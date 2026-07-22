"""
Quanta Discord — онбординг-гейт бот (Phase 1).

Реализует discord-build-spec-2026-07-13.ru.md (§2, §5, §8):
  join → @newcomer + авто-DM → ✅ правила (rules-ack) → выбор ЦЕЛЕЙ
  💰🏢🚀🧠👀 (можно несколько; value-DM по каждой) → @member → доступ к
  каналам участника. Цель 💰: бот просит Quanta ID в ЛС и постит заявку
  в служебный #заявки (ручная выдача @affiliate, Phase 1).
  + 24ч напоминание (1 раз), команды !faq, !affiliate (Phase 1), !stats.
  + SETUP_MODE=1: разовая сборка сервера (роли, каналы §4, грандфазер
  @member, якоря в #старт) — см. setup_server.py.

Стек: discord.py + Python 3.12. Деплой: Railway worker (см. Procfile).
State: data/state.json (переживает рестарт процесса; на Railway файловая
система эфемерна — состояние теряется при редеплое, known limit Phase 1).

Privileged intents (включить в Discord Developer Portal → Bot → Privileged
Gateway Intents): SERVER MEMBERS INTENT и MESSAGE CONTENT INTENT.
Права бота на сервере: Manage Roles + Manage Channels (для SETUP_MODE),
роль бота — ВЫШЕ управляемых ролей в иерархии.
"""

import asyncio
import json
import logging
import os
import re

import discord

import config
import content

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("quanta-onboarding")


# ── Состояние ────────────────────────────────────────────────────────────────
# { "<user_id>": {joined_at, lang, rules_ack, goals[], pending_qid, qid,
#                 member_granted, reminded} }
state: dict = {}
_state_lock = asyncio.Lock()
# user_id'ы, для которых выдача @member сейчас в процессе — защита от
# двойного гранта при повторной доставке реакции (TOCTOU между await).
_granting: set = set()
# SETUP_MODE: on_ready срабатывает и при reconnect — сетап гоняем один раз.
_setup_started = False
# CLEANUP_MODE: та же защита от повторного запуска при reconnect.
_cleanup_started = False


def load_state() -> None:
    global state
    try:
        with open(config.STATE_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            raise ValueError(f"ожидался объект, получено {type(loaded).__name__}")
        state = loaded
        log.info("Состояние загружено: %d записей", len(state))
    except FileNotFoundError:
        state = {}
        log.info("Файл состояния не найден — старт с пустого состояния")
    except (json.JSONDecodeError, ValueError, OSError) as e:
        state = {}
        log.warning("Не удалось прочитать состояние (%s) — старт с пустого", e)


async def save_state() -> None:
    """Атомарная запись через временный файл, под локом (защищает сам файл)."""
    async with _state_lock:
        try:
            os.makedirs(os.path.dirname(config.STATE_PATH) or ".", exist_ok=True)
            tmp = config.STATE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp, config.STATE_PATH)
        except OSError as e:
            log.error("Не удалось сохранить состояние: %s", e)


def user_record(user_id: int) -> dict:
    key = str(user_id)
    if key not in state:
        state[key] = {
            "joined_at": None,
            "lang": None,
            "rules_ack": False,
            "goals": [],
            "pending_qid": False,
            "qid": None,
            "member_granted": False,
            "reminded": False,
        }
    # legacy-записи (до перехода сегменты → цели) могли не иметь новых полей
    rec = state[key]
    rec.setdefault("goals", [])
    rec.setdefault("pending_qid", False)
    rec.setdefault("pending_company", False)
    rec.setdefault("card_sent", False)
    rec.setdefault("announced", False)
    rec.setdefault("reminded48", False)
    return rec


# ── Discord client ───────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True          # privileged — on_member_join, управление ролями
intents.message_content = True  # privileged — команды !faq/!affiliate/!stats
# реакции входят в Intents.default()

client = discord.Client(intents=intents)


# ── Хелперы по ролям/каналам (поиск по имени внутри гильдии) ──────────────────
def find_role(guild: discord.Guild, name: str):
    return discord.utils.get(guild.roles, name=name)


async def add_role_by_name(member: discord.Member, role_name: str) -> bool:
    role = find_role(member.guild, role_name)
    if role is None:
        log.warning("Роль %r не найдена на сервере %s", role_name, member.guild.name)
        return False
    try:
        await member.add_roles(role, reason="Quanta onboarding")
        return True
    except discord.Forbidden:
        log.error("Нет прав выдать роль %r (проверь Manage Roles + иерархию)", role_name)
    except discord.HTTPException as e:
        log.error("Ошибка выдачи роли %r: %s", role_name, e)
    return False


async def remove_role_by_name(member: discord.Member, role_name: str) -> bool:
    role = find_role(member.guild, role_name)
    if role is None:
        return False
    if role not in member.roles:
        return True
    try:
        await member.remove_roles(role, reason="Quanta onboarding")
        return True
    except discord.Forbidden:
        log.error("Нет прав снять роль %r", role_name)
    except discord.HTTPException as e:
        log.error("Ошибка снятия роли %r: %s", role_name, e)
    return False


async def dm(member: discord.abc.User, text: str) -> bool:
    """Отправить ЛС. DM могут быть закрыты — это не ошибка, просто False."""
    try:
        await member.send(text)
        return True
    except discord.Forbidden:
        log.info("ЛС закрыты у %s — пропускаю", member)
    except discord.HTTPException as e:
        log.warning("Не удалось отправить ЛС %s: %s", member, e)
    return False


def is_staff(member: discord.Member) -> bool:
    """Хелпер/админ — может пользоваться !affiliate, !stats."""
    if member.id in config.ADMIN_IDS:
        return True
    if member.guild_permissions.administrator:
        return True
    return find_role(member.guild, config.HELPER_ROLE) in member.roles


def main_guild():
    """Рабочая гильдия: по GUILD_ID, иначе первая (бот живёт на одном сервере)."""
    if config.GUILD_ID:
        return client.get_guild(config.GUILD_ID)
    return client.guilds[0] if client.guilds else None


def channel_mentions(guild: discord.Guild) -> dict:
    """Плейсхолдер value-DM → упоминание канала <#id>; канала нет — "#имя"."""
    mapping = {
        "ch_earn": config.EARN_CHANNEL,
        "ch_general": config.GENERAL_CHANNEL,
        "ch_learn": config.LEARN_CHANNEL,
        "ch_wins": config.WINS_CHANNEL,
        "ch_questions": config.QUESTIONS_CHANNEL,
        "ch_materials": config.MATERIALS_CHANNEL,
        "ch_ann": config.ANNOUNCEMENTS_CHANNEL,
        "ch_support": config.SUPPORT_CHANNEL,
    }
    out = {}
    for key, name in mapping.items():
        ch = discord.utils.get(guild.text_channels, name=name)
        out[key] = ch.mention if ch else "#" + name
    return out


# Эмодзи цели по ключу (для поста «Встречайте» и шага 2 тура)
EMOJI_BY_GOAL = {goal: emoji for emoji, goal in config.GOAL_EMOJI.items()}


def lang_of(member) -> str:
    """Язык участника: роль языка (нативный опрос) → state → дефолт."""
    for role in getattr(member, "roles", []):
        code = config.LANG_ROLES.get(role.name)
        if code:
            return code
    rec = state.get(str(getattr(member, "id", 0)))
    return (rec or {}).get("lang") or content.DEFAULT_LANG


def fmt(text_or_dict, lang: str, guild=None, **extra) -> str:
    """Подставить упоминания каналов и доп-поля в текст (или словарь языков)."""
    if isinstance(text_or_dict, dict):
        text = text_or_dict.get(lang) or text_or_dict[content.DEFAULT_LANG]
    else:
        text = text_or_dict
    fields = dict(content._CH_DEFAULTS)
    if guild is not None:
        fields.update(channel_mentions(guild))
    fields.update(extra)
    return text.format(**fields)


def goals_of(member) -> list:
    """Цели участника: из state + из ролей (роль — источник правды опроса)."""
    rec = state.get(str(member.id)) or {}
    goals = list(rec.get("goals") or [])
    for role in getattr(member, "roles", []):
        g = config.GOAL_BY_ROLE.get(role.name)
        if g and g not in goals:
            goals.append(g)
    return goals


# ── Кнопки: тур в личке, починка в #старт, поддержка ─────────────────────────
# Все view — persistent (timeout=None, фиксированные custom_id): переживают
# рестарт бота, состояние шага не хранится — каждый шаг вычисляется на клике.

def _member_of(user):
    g = main_guild()
    return g.get_member(user.id) if g else None


def _tour_step2_text(member, lang: str) -> str:
    goals = goals_of(member) or ["learn", "watch"]
    lines = [content.TOUR_STEP2_HEADER[lang]]
    for g in ("learn", "earn", "company", "business", "watch"):
        if g in goals:
            lines.append(content.TOUR_GOAL_LINES[lang][g])
    return "\n".join(lines)


class TourEntryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Начать знакомство",
                       style=discord.ButtonStyle.primary, custom_id="q_tour_start")
    async def start(self, interaction: discord.Interaction, _):
        m = _member_of(interaction.user)
        lang = lang_of(m) if m else content.DEFAULT_LANG
        await interaction.response.send_message(
            fmt(content.TOUR_STEP1, lang, main_guild()), view=TourStep1View())

    @discord.ui.button(label="Пропустить",
                       style=discord.ButtonStyle.secondary, custom_id="q_tour_skip")
    async def skip(self, interaction: discord.Interaction, _):
        m = _member_of(interaction.user)
        lang = lang_of(m) if m else content.DEFAULT_LANG
        await interaction.response.send_message(
            fmt(content.TOUR_SKIP, lang, main_guild()))


class TourStep1View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Дальше →",
                       style=discord.ButtonStyle.primary, custom_id="q_tour_s2")
    async def next(self, interaction: discord.Interaction, _):
        m = _member_of(interaction.user)
        lang = lang_of(m) if m else content.DEFAULT_LANG
        text = fmt(_tour_step2_text(m, lang) if m else
                   content.TOUR_STEP2_HEADER[lang], lang, main_guild())
        await interaction.response.send_message(text, view=TourStep2View())


class TourStep2View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Дальше →",
                       style=discord.ButtonStyle.primary, custom_id="q_tour_s3")
    async def next(self, interaction: discord.Interaction, _):
        m = _member_of(interaction.user)
        lang = lang_of(m) if m else content.DEFAULT_LANG
        await interaction.response.send_message(
            fmt(content.TOUR_STEP3, lang, main_guild()))


class FixView(discord.ui.View):
    """Кнопка-починка в #старт: одна кнопка чинит роли/письма (решение §4)."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label=content.FIX_BUTTON_LABEL,
                       style=discord.ButtonStyle.primary, custom_id="q_fix")
    async def fix(self, interaction: discord.Interaction, _):
        # починка шлёт несколько ЛС — дольше 3с лимита Discord на ответ,
        # поэтому сначала defer, финальный текст уходит followup'ом
        await interaction.response.defer(ephemeral=True)
        m = _member_of(interaction.user)
        if m is None:
            await interaction.followup.send("🤷", ephemeral=True)
            return
        lang = lang_of(m)
        repaired = []
        rec = user_record(m.id)
        # 1) роли: цель есть, @member нет → догнать (каналы откроются)
        if goals_of(m) and not rec.get("member_granted"):
            for g in goals_of(m):
                if g not in rec["goals"]:
                    rec["goals"].append(g)
            if config.NATIVE_ONBOARDING:
                rec["rules_ack"] = True
            await save_state()
            await maybe_grant_member(m)
            if rec.get("member_granted"):
                repaired.append("доступ к каналам")
        # 2) письма: карта + value-DM по целям заново
        delivered = await dm(m, fmt(content.WELCOME_CARD, lang, m.guild))
        if delivered:
            rec["card_sent"] = True
            mentions = channel_mentions(m.guild)
            for g in goals_of(m):
                await dm(m, content.value_dm(g, lang, config.PRODUCT_URL, mentions))
                if g == "earn" and not rec.get("qid"):
                    rec["pending_qid"] = True
            await save_state()
            repaired.append("письма отправлены")
        text = (fmt(content.FIX_REPAIRED, lang, what=", ".join(repaired))
                if repaired else fmt(content.FIX_ALL_OK, lang))
        await interaction.followup.send(text, ephemeral=True)


class SupportView(discord.ui.View):
    """#поддержка: [🎫 Открыть тикет](ссылка) + [📖 Частые вопросы] (эфемерно)."""

    def __init__(self, invite_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🎫 Открыть тикет",
                                        style=discord.ButtonStyle.link,
                                        url=invite_url))

    @discord.ui.button(label="📖 Частые вопросы",
                       style=discord.ButtonStyle.secondary, custom_id="q_support_faq")
    async def faq(self, interaction: discord.Interaction, _):
        m = _member_of(interaction.user)
        lang = lang_of(m) if m else content.DEFAULT_LANG
        topics = ", ".join(t["title"] for t in content.FAQ_TOPICS[lang].values())
        await interaction.response.send_message(
            content.FAQ_LIST_PROMPT[lang].format(topics=topics), ephemeral=True)


async def dm_view(member, text: str, view) -> bool:
    """ЛС с кнопками; закрытая личка — не ошибка, просто False."""
    try:
        await member.send(text, view=view)
        return True
    except discord.Forbidden:
        log.info("ЛС закрыты у %s — пропускаю (view)", member)
    except discord.HTTPException as e:
        log.warning("Не удалось отправить ЛС (view) %s: %s", member, e)
    return False


# ── Центральная обработка выбора цели (реакция / роль из опроса / вкладка) ────
async def process_goal_pick(member: discord.Member, goal: str,
                            notify: bool = True) -> None:
    """Единый вход для всех источников цели (условие V №2: источник не важен)."""
    rec = user_record(member.id)
    if config.NATIVE_ONBOARDING:
        rec["rules_ack"] = True  # экран правил пройден на входе (Discord)
    lang = lang_of(member)
    mentions = channel_mentions(member.guild)
    if goal in rec["goals"]:
        if notify:
            # «уже выбрано»: без дублей заявок, повтор главного (канон части 2)
            await dm(member, content.ALREADY_PICKED_DM.get(lang) or
                     content.ALREADY_PICKED_DM[content.DEFAULT_LANG])
            delivered = await dm(member, content.value_dm(
                goal, lang, config.PRODUCT_URL, mentions))
            if goal == "earn" and delivered and not rec.get("qid"):
                rec["pending_qid"] = True
                await save_state()
        await maybe_grant_member(member)
        return
    rec["goals"].append(goal)
    await save_state()
    if notify:
        if not rec.get("card_sent"):
            if await dm_view(member, fmt(content.WELCOME_CARD, lang, member.guild),
                             TourEntryView()):
                rec["card_sent"] = True
                await save_state()
        delivered = await dm(member, content.value_dm(
            goal, lang, config.PRODUCT_URL, mentions))
        if goal == "earn":
            if delivered:
                rec["pending_qid"] = True
                await save_state()
                schedule_qid_reminder(member)
            else:
                log.warning("💰: ЛС закрыты у %s — письмо не ушло", member)
                await ping_closed_dm(member)
        elif goal == "company" and delivered:
            rec["pending_company"] = True
            await save_state()
        log.info("Цель=%s (lang=%s, notify) → %s", goal, lang, member)
    await maybe_grant_member(member)


async def ping_closed_dm(member) -> None:
    """Страховка §4: письмо не ушло → пинг в #старт, самоудаление через час."""
    ch = discord.utils.get(member.guild.text_channels, name=config.START_CHANNEL)
    if ch is None:
        return
    try:
        await ch.send(content.PING_CLOSED_DM.format(
            mention=member.mention, btn=content.FIX_BUTTON_LABEL),
            delete_after=3600)
    except discord.HTTPException as e:
        log.warning("Пинг в #%s не ушёл: %s", config.START_CHANNEL, e)


# ── Выдача @member, когда оба шага пройдены ───────────────────────────────────
async def maybe_grant_member(member: discord.Member) -> None:
    rec = user_record(member.id)
    if rec.get("member_granted") or member.id in _granting:
        return
    # в нативном режиме правила приняты на экране входа (Rules Screening)
    rules_ok = rec.get("rules_ack") or config.NATIVE_ONBOARDING
    if not (rules_ok and rec.get("goals")):
        return
    _granting.add(member.id)
    try:
        # @member уже был (старый участник добирает цель / state сброшен
        # редеплоем) → это восстановление, а не вход: без поста «Встречайте»
        member_role = find_role(member.guild, config.MEMBER_ROLE)
        had_member = member_role is not None and member_role in member.roles
        granted = await add_role_by_name(member, config.MEMBER_ROLE)
        if granted:
            await remove_role_by_name(member, config.NEWCOMER_ROLE)
            rec["member_granted"] = True
            if had_member:
                rec["announced"] = True
                log.info("@member уже был: %s — «Встречайте» пропущен", member)
            else:
                log.info("@member выдан: %s (цели=%s)", member, rec.get("goals"))
            await save_state()
            await announce_welcome(member)
    finally:
        _granting.discard(member.id)


async def announce_welcome(member: discord.Member) -> None:
    """Пост «Встречайте» в #общее (часть 1 шаг 8; текст — правка V, без рода)."""
    rec = user_record(member.id)
    if rec.get("announced"):
        return
    ch = discord.utils.get(member.guild.text_channels,
                           name=config.GENERAL_CHANNEL)
    if ch is None:
        return
    goals = " ".join(EMOJI_BY_GOAL[g] for g in rec.get("goals", [])
                     if g in EMOJI_BY_GOAL) or "👀"
    try:
        await ch.send(content.ANNOUNCE_WELCOME.format(
            mention=member.mention, goals=goals))
        rec["announced"] = True
        await save_state()
    except discord.HTTPException as e:
        log.warning("Пост «Встречайте» не ушёл: %s", e)


# ── 48ч-напоминание: цель 💰 отмечена, Quanta ID не прислан (одно) ────────────
_qid48_scheduled: set = set()


def schedule_qid_reminder(member: discord.Member) -> None:
    if member.id in _qid48_scheduled:
        return
    _qid48_scheduled.add(member.id)
    client.loop.create_task(_qid48_task(member))


async def _qid48_task(member: discord.Member) -> None:
    try:
        await asyncio.sleep(48 * 3600)
        rec = state.get(str(member.id))
        if (rec and rec.get("pending_qid") and not rec.get("qid")
                and not rec.get("reminded48")):
            lang = lang_of(member)
            await dm(member, fmt(content.REMINDER_48H, lang, member.guild))
            rec["reminded48"] = True
            await save_state()
            log.info("48ч-напоминание 💰 → %s", member)
    finally:
        _qid48_scheduled.discard(member.id)


# ── SLA-пинг: заявка в #заявки без ответа сутки → пинг админам (часть 2) ─────
async def _sla_task(user_id: int, qid: str) -> None:
    await asyncio.sleep(24 * 3600)
    guild = main_guild()
    if guild is None:
        return
    m = guild.get_member(user_id)
    if m is None:
        return
    aff = find_role(guild, config.AFFILIATE_ROLE)
    if aff is not None and aff in m.roles:
        return  # роль выдана — SLA соблюдён
    ch = discord.utils.get(guild.text_channels, name=config.APPLICATIONS_CHANNEL)
    if ch is None:
        return
    admins = " ".join(f"<@{i}>" for i in config.ADMIN_IDS)
    try:
        await ch.send(content.SLA_PING.format(
            admins=admins, mention=m.mention, qid=qid))
    except discord.HTTPException as e:
        log.warning("SLA-пинг не ушёл: %s", e)


# ── Напоминание через REMINDER_HOURS ──────────────────────────────────────────
# Кому уже запланировано (защита от дублей: reconnect повторно зовёт on_ready →
# resume_reminders; без этого юзер получил бы напоминание дважды).
_reminder_scheduled: set = set()


async def reminder_task(member: discord.Member, delay_seconds: float) -> None:
    try:
        try:
            await asyncio.sleep(delay_seconds)
        except asyncio.CancelledError:
            return
        await _reminder_fire(member)
    finally:
        _reminder_scheduled.discard(member.id)


async def _reminder_fire(member: discord.Member) -> None:
    rec = state.get(str(member.id))
    if not rec:
        return
    # done: прошёл НОВЫЙ онбординг (цели) ИЛИ старый (segment из legacy-state),
    # ИЛИ @member уже выдан — иначе стартовый resume раздал бы «напоминания»
    # всей старой базе (state может пережить деплой при volume/локальном запуске)
    done = rec.get("member_granted") or (
        rec.get("rules_ack") and (rec.get("goals") or rec.get("segment")))
    if rec.get("reminded") or done:
        return
    # юзер мог уйти за время ожидания — не слать напоминание вдогонку
    if member.guild.get_member(member.id) is None:
        rec["reminded"] = True
        await save_state()
        return
    lang = rec.get("lang") or content.DEFAULT_LANG
    sent = await dm(member, content.REMINDER_DM[lang])
    rec["reminded"] = True
    await save_state()
    if sent:
        log.info("Напоминание отправлено: %s", member)


def schedule_reminder(member: discord.Member, delay_seconds: float) -> None:
    if member.id in _reminder_scheduled:
        return  # уже запланировано (resume после reconnect и т.п.) — не дублируем
    _reminder_scheduled.add(member.id)
    if delay_seconds < 0:
        delay_seconds = 0
    client.loop.create_task(reminder_task(member, delay_seconds))


async def resume_reminders() -> None:
    """
    На старте восстановить напоминания: для тех, кто не прошёл онбординг и
    ещё не получал напоминания. Если 24ч уже прошли — напомнить сразу,
    иначе — досидеть остаток.
    """
    import datetime

    delay = config.REMINDER_HOURS * 3600
    now = datetime.datetime.now(datetime.timezone.utc)
    resumed = 0
    for key, rec in list(state.items()):
        # та же done-логика, что в _reminder_fire (legacy-segment учитывается)
        done = rec.get("member_granted") or (
            rec.get("rules_ack") and (rec.get("goals") or rec.get("segment")))
        if rec.get("reminded") or done or not rec.get("joined_at"):
            continue
        try:
            joined = datetime.datetime.fromisoformat(rec["joined_at"])
            if joined.tzinfo is None:
                joined = joined.replace(tzinfo=datetime.timezone.utc)
            member = None
            for guild in client.guilds:
                if config.GUILD_ID and guild.id != config.GUILD_ID:
                    continue
                member = guild.get_member(int(key))
                if member:
                    break
            if member is None:
                continue
            elapsed = (now - joined).total_seconds()
            schedule_reminder(member, delay - elapsed)
            resumed += 1
        except (ValueError, TypeError) as e:
            log.warning("Пропускаю запись %s в resume_reminders: %s", key, e)
            continue
    if resumed:
        log.info("Восстановлено напоминаний: %d", resumed)


# ── События ──────────────────────────────────────────────────────────────────
async def ensure_aux_roles(guild: discord.Guild) -> None:
    """Роли под нативный опрос: 5 целей + 3 языка (идемпотентно)."""
    wanted = list(config.GOAL_ROLES.values()) + list(config.LANG_ROLES)
    for name in wanted:
        if discord.utils.get(guild.roles, name=name) is None:
            try:
                await guild.create_role(name=name, reason="Quanta: роли опроса")
                log.info("Роль создана: @%s", name)
            except discord.HTTPException as e:
                log.error("Не создать роль @%s: %s", name, e)


async def reconcile_roles(guild: discord.Guild) -> None:
    """Стартовая сверка: роль цели есть, @member нет → догнать (без DM).

    Закрывает окно «опрос выдал роль, пока бот лежал» + чинит state после
    редеплоя (диск эфемерный). Письма здесь НЕ шлём — не спамить старых."""
    fixed = 0
    for m in guild.members:
        if m.bot:
            continue
        role_goals = [config.GOAL_BY_ROLE[r.name] for r in m.roles
                      if r.name in config.GOAL_BY_ROLE]
        if not role_goals:
            continue
        rec = user_record(m.id)
        for r in m.roles:
            code = config.LANG_ROLES.get(r.name)
            if code:
                rec["lang"] = code
        new = [g for g in role_goals if g not in rec["goals"]]
        if new:
            rec["goals"].extend(new)
            rec["announced"] = True  # бэкфилл: без поста «Встречайте»
            await save_state()
        if not rec.get("member_granted"):
            await maybe_grant_member(m)
            if rec.get("member_granted"):
                fixed += 1
    if fixed:
        log.info("Сверка ролей: доступ догнан у %d участников", fixed)


async def ensure_support_pin(guild: discord.Guild) -> None:
    """Закреп-маршрутизатор в #поддержка с кнопками (когда есть ссылка тикетов)."""
    if not config.SUPPORT_INVITE_URL:
        return
    ch = discord.utils.get(guild.text_channels, name=config.SUPPORT_CHANNEL)
    if ch is None:
        return
    try:
        pins = await ch.pins()
        if any(p.author.id == client.user.id and
               p.content.startswith("**Куда с чем идти") for p in pins):
            return
        msg = await ch.send(fmt(content.SUPPORT_PIN, content.DEFAULT_LANG, guild),
                            view=SupportView(config.SUPPORT_INVITE_URL))
        await msg.pin(reason="Quanta: маршрутизатор поддержки")
        log.info("Закреп поддержки с кнопками запощен")
    except discord.HTTPException as e:
        log.warning("Закреп поддержки не встал: %s", e)


_views_registered = False


@client.event
async def on_ready():
    global _setup_started, _views_registered
    log.info("Бот запущен: %s", client.user)
    log.info("Гильдии: %s", [(g.name, g.id) for g in client.guilds])
    if not _views_registered:
        _views_registered = True
        client.add_view(TourEntryView())
        client.add_view(TourStep1View())
        client.add_view(TourStep2View())
        client.add_view(FixView())
        if config.SUPPORT_INVITE_URL:
            client.add_view(SupportView(config.SUPPORT_INVITE_URL))
    guild_now = main_guild()
    if guild_now is not None:
        await ensure_aux_roles(guild_now)
        await reconcile_roles(guild_now)
        await ensure_support_pin(guild_now)
    if config.GUILD_ID and not any(g.id == config.GUILD_ID for g in client.guilds):
        log.warning("GUILD_ID=%s — бот не состоит в этой гильдии!", config.GUILD_ID)
    if not config.RULES_MESSAGE_ID:
        log.warning("RULES_MESSAGE_ID не задан — реакция на правила НЕ обрабатывается (гейт мёртв)")
    if not config.GOALS_MESSAGE_ID:
        log.warning("GOALS_MESSAGE_ID не задан — выбор цели НЕ обрабатывается (гейт мёртв)")
    if config.SETUP_MODE and not _setup_started:
        _setup_started = True
        guild = main_guild()
        if guild is None:
            log.error("SETUP_MODE=1, но гильдия не найдена — бот приглашён на сервер?")
        else:
            import setup_server
            client.loop.create_task(setup_server.run(client, guild))
    global _cleanup_started
    if config.CLEANUP_MODE and not _cleanup_started:
        _cleanup_started = True
        guild = main_guild()
        if guild is None:
            log.error("CLEANUP_MODE=%s, но гильдия не найдена", config.CLEANUP_MODE)
        else:
            import cleanup_server
            client.loop.create_task(cleanup_server.run(client, guild))
    await resume_reminders()


@client.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    if config.GUILD_ID and member.guild.id != config.GUILD_ID:
        return
    import datetime

    rec = user_record(member.id)
    rec["joined_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec["reminded"] = False
    # rejoin: при выходе Discord снял роли — сбрасываем флаг «выдано»,
    # иначе maybe_grant_member навсегда выходит на первой проверке (lockout)
    rec["member_granted"] = False
    await save_state()

    if config.NATIVE_ONBOARDING:
        # часть 3: гейт держит Discord (правила + опрос). Не прошёл опрос —
        # физически не участник. @newcomer и 24ч-напоминание упразднены;
        # письма поедут по событиям ролей (on_member_update).
        log.info("Join (native): %s (id=%s) — жду ролей опроса", member, member.id)
        return

    await add_role_by_name(member, config.NEWCOMER_ROLE)
    # прошёл онбординг раньше (state пережил его выход) — восстановить сразу
    await maybe_grant_member(member)
    if rec.get("member_granted"):
        log.info("Rejoin: %s — @member восстановлен без повторного онбординга", member)
    else:
        await dm(member, content.AUTO_DM)
        schedule_reminder(member, config.REMINDER_HOURS * 3600)
    log.info("Join: %s (id=%s)", member, member.id)


@client.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """События ролей — главный вход после перехода на нативный опрос.

    Условие V №2: бот реагирует на роль цели из ЛЮБОГО источника одинаково
    (опрос при входе, вкладка «Каналы и роли», ручная выдача)."""
    if after.bot:
        return
    if config.GUILD_ID and after.guild.id != config.GUILD_ID:
        return
    added = [r for r in after.roles if r not in before.roles]
    if not added:
        return
    rec = user_record(after.id)
    lang_changed = False
    for role in added:
        code = config.LANG_ROLES.get(role.name)
        if code and rec.get("lang") != code:
            rec["lang"] = code
            lang_changed = True
    if lang_changed:
        await save_state()
        log.info("Язык (роль)=%s: %s", rec["lang"], after)
    for role in added:
        goal = config.GOAL_BY_ROLE.get(role.name)
        if goal:
            await process_goal_pick(after, goal, notify=True)
        elif role.name == config.AFFILIATE_ROLE:
            # AC выдаёт @affiliate после проверки U-50 → закрываем петлю DM
            rec["pending_qid"] = False
            await save_state()
            lang = lang_of(after)
            await dm(after, fmt(content.ACCESS_OPENED_DM, lang, after.guild))
            log.info("@affiliate выдан → доступ-DM %s", after)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Нас интересуют только реакции на якорные сообщения в гильдии.
    if payload.guild_id is None:
        return
    if config.GUILD_ID and payload.guild_id != config.GUILD_ID:
        return
    if payload.user_id == client.user.id:
        return

    guild = client.get_guild(payload.guild_id)
    if guild is None:
        return
    member = payload.member or guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    emoji = str(payload.emoji)

    # выбор языка (флаг) — запоминаем, на нём шлём дальнейшие DM
    if config.LANG_MESSAGE_ID and payload.message_id == config.LANG_MESSAGE_ID:
        lang = config.LANG_EMOJI.get(emoji)
        if lang:
            rec = user_record(member.id)
            if rec.get("lang") != lang:
                rec["lang"] = lang
                await save_state()
                log.info("Язык=%s: %s", lang, member)
        return

    # rules-ack
    if config.RULES_MESSAGE_ID and payload.message_id == config.RULES_MESSAGE_ID:
        if emoji == config.RULES_EMOJI:
            rec = user_record(member.id)
            if not rec.get("rules_ack"):
                rec["rules_ack"] = True
                await save_state()
                log.info("rules-ack: %s", member)
            await maybe_grant_member(member)
        return

    # выбор цели (💰🏢🚀🧠👀) — переходный путь через реакции; после включения
    # нативного опроса якорь удаляется (cutover), а логика едет через роли
    if config.GOALS_MESSAGE_ID and payload.message_id == config.GOALS_MESSAGE_ID:
        goal = config.GOAL_EMOJI.get(emoji)
        if goal is None:
            return
        await process_goal_pick(member, goal, notify=True)
        return


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.content.startswith("!"):
        # ЛС без команды: Quanta ID (💰) → компания (🏢) → фолбэк (не молчим)
        if message.guild is None:
            rec = state.get(str(message.author.id))
            if rec and rec.get("pending_qid"):
                await maybe_capture_qid(message)
            elif rec and rec.get("pending_company"):
                await capture_company(message)
            else:
                m = _member_of(message.author)
                lang = lang_of(m) if m else content.DEFAULT_LANG
                await dm(message.author,
                         fmt(content.DM_FALLBACK, lang, main_guild()))
        return
    # отсекаем чужие гильдии сразу; ЛС (message.guild is None) оставляем для !faq
    if message.guild is not None and config.GUILD_ID and message.guild.id != config.GUILD_ID:
        return

    content_lower = message.content.strip().lower()

    # !faq [тема] — для всех, в т.ч. в ЛС с ботом
    if content_lower == "!faq" or content_lower.startswith("!faq "):
        await handle_faq(message)
        return

    # дальше — только в гильдии и для staff
    if message.guild is None:
        return

    if content_lower.startswith("!affiliate"):
        await handle_affiliate(message)
        return
    if content_lower == "!stats":
        await handle_stats(message)
        return


# ── 💰-заявка: Quanta ID из ЛС → пост в #заявки (спека §8, Phase 1) ───────────
async def maybe_capture_qid(message: discord.Message) -> None:
    rec = state.get(str(message.author.id))
    if not rec or not rec.get("pending_qid"):
        return
    qid = message.content.strip()
    lang = rec.get("lang") or content.DEFAULT_LANG
    # валидный Quanta ID = одна строка без пробелов (логин или почта);
    # на невалидное отвечаем, а не молчим — иначе юзер уверен, что подал заявку
    if not qid or len(qid) > 100 or any(c.isspace() for c in qid):
        await dm(message.author, content.QID_INVALID_DM[lang])
        return
    guild = main_guild()
    if guild is None:
        log.error("Заявка 💰 от %s: гильдия не найдена (проверь GUILD_ID)", message.author)
        return
    ch = discord.utils.get(guild.text_channels, name=config.APPLICATIONS_CHANNEL)
    if ch is None:
        log.error("Канал #%s не найден — заявка от %s (qid=%s) НЕ доставлена",
                  config.APPLICATIONS_CHANNEL, message.author, qid)
        return  # юзеру не подтверждаем, чтобы не врать про отправку
    mentions = channel_mentions(guild)
    member = guild.get_member(message.author.id)
    # флаг снимаем ДО поста: два быстрых ЛС подряд не должны дать две заявки
    rec["pending_qid"] = False
    rec["qid"] = qid
    await save_state()
    try:
        await ch.send(content.APPLICATION_POST.format(
            ch_earn=mentions["ch_earn"],
            mention=member.mention if member else str(message.author),
            name=str(message.author),
            user_id=message.author.id,
            qid=qid,
        ))
    except discord.HTTPException as e:
        log.error("Не удалось запостить заявку в #%s: %s", config.APPLICATIONS_CHANNEL, e)
        # вернуть флаг, чтобы юзер мог прислать ID повторно
        rec["pending_qid"] = True
        rec["qid"] = None
        await save_state()
        return
    await dm(message.author, content.QID_RECEIVED_DM[lang].format(ch_earn=mentions["ch_earn"]))
    # SLA части 2: ответ на заявку — сутки; просрочка → пинг админам в #заявки
    client.loop.create_task(_sla_task(message.author.id, qid))
    log.info("Заявка 💰: %s → #%s (qid=%s)", message.author, config.APPLICATIONS_CHANNEL, qid)


async def capture_company(message: discord.Message) -> None:
    """🏢: ответ «что за компания» → заявка в #заявки (тур, шаг 2)."""
    rec = state.get(str(message.author.id))
    if not rec or not rec.get("pending_company"):
        return
    text = message.content.strip()[:300]
    if not text:
        return
    guild = main_guild()
    if guild is None:
        return
    ch = discord.utils.get(guild.text_channels, name=config.APPLICATIONS_CHANNEL)
    if ch is None:
        log.error("#%s не найден — заявка компании от %s потеряна",
                  config.APPLICATIONS_CHANNEL, message.author)
        return
    member = guild.get_member(message.author.id)
    try:
        await ch.send(content.COMPANY_POST.format(
            mention=member.mention if member else str(message.author),
            name=str(message.author), user_id=message.author.id, text=text))
    except discord.HTTPException as e:
        log.error("Заявка компании не запостилась: %s", e)
        return
    rec["pending_company"] = False
    await save_state()
    lang = lang_of(member) if member else content.DEFAULT_LANG
    await dm(message.author, content.COMPANY_RECEIVED_DM[lang])
    log.info("Заявка 🏢: %s → #%s (%s)", message.author,
             config.APPLICATIONS_CHANNEL, text[:60])


# ── Команды ──────────────────────────────────────────────────────────────────
def _faq_lang(message: discord.Message, arg: str) -> str:
    """Язык FAQ: сохранённый выбор юзера, иначе эвристика по тексту запроса."""
    rec = state.get(str(message.author.id))
    if rec and rec.get("lang"):
        return rec["lang"]
    has_cyr = any("Ѐ" <= c <= "ӿ" for c in arg)
    has_lat = any("a" <= c <= "z" for c in arg)
    if has_lat and not has_cyr:
        return "en"
    return content.DEFAULT_LANG  # кириллица без явного выбора → ru


async def handle_faq(message: discord.Message):
    arg = message.content[len("!faq"):].strip().lower()
    lang = _faq_lang(message, arg)
    topics_dict = content.FAQ_TOPICS[lang]
    if not arg:
        topics = ", ".join(t["title"] for t in topics_dict.values())
        await message.reply(content.FAQ_LIST_PROMPT[lang].format(topics=topics))
        return
    matches = [t for t in topics_dict.values()
               if any(alias in arg for alias in t["aliases"])]
    if not matches:
        topic_names = ", ".join(t["title"] for t in topics_dict.values())
        await message.reply(content.FAQ_FALLBACK[lang].format(topics=topic_names))
        return
    # до 3 совпадений, чтобы не заспамить
    reply = "\n\n".join(f"**{t['title']}**\n{t['answer']}" for t in matches[:3])
    await message.reply(reply)


async def handle_affiliate(message: discord.Message):
    """Фаза 1 (интерим): ручная выдача @affiliate хелпером/админом."""
    if not is_staff(message.author):
        return
    # упоминания берём из ТЕКСТА команды: message.mentions при reply-пинге
    # включает автора цитируемого сообщения — роль улетела бы не тому
    targets = []
    for uid in re.findall(r"<@!?(\d+)>", message.content):
        m = message.guild.get_member(int(uid))
        if m is not None and m not in targets:
            targets.append(m)
    if not targets:
        await message.reply("Использование: `!affiliate @пользователь`")
        return
    granted_to = []
    for target in targets:
        if await add_role_by_name(target, config.AFFILIATE_ROLE):
            granted_to.append(target.mention)
    if granted_to:
        await message.reply("Выдал @" + config.AFFILIATE_ROLE + ": " + ", ".join(granted_to))
    else:
        await message.reply("Не удалось выдать роль — проверь права бота и иерархию ролей.")


async def handle_stats(message: discord.Message):
    """Срез онбординга для хелперов (спека §6)."""
    if not is_staff(message.author):
        return
    # реальные join'ы — те, чей вход бот зафиксировал (joined_at задан);
    # реакции pre-existing участников (joined_at=None) метрику не инфлейтят
    joined = [r for r in state.values() if r.get("joined_at")]
    total = len(joined)
    passed = sum(1 for r in joined if r.get("rules_ack") and r.get("goals"))
    members = sum(1 for r in joined if r.get("member_granted"))
    by_goal = {}
    for r in state.values():
        for g in r.get("goals") or []:
            by_goal[g] = by_goal.get(g, 0) + 1
    pending = sum(1 for r in state.values() if r.get("pending_qid"))
    pct = (passed / total * 100) if total else 0
    goal_lines = "\n".join(
        f"  • {content.GOAL_LABEL.get(k, k)}: {v}" for k, v in by_goal.items()
    ) or "  (пока нет)"
    await message.reply(
        f"**Онбординг (с момента последнего сброса state)**\n"
        f"Всего join: {total}\n"
        f"Прошли гейт (правила + цель): {passed} ({pct:.0f}%)\n"
        f"Получили @{config.MEMBER_ROLE}: {members}\n"
        f"Ждём Quanta ID для 💰-заявки: {pending}\n"
        f"Срез по целям (сумма может быть > числа людей — цели множественные):\n"
        f"{goal_lines}"
    )


def main():
    load_state()
    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
