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
    }
    out = {}
    for key, name in mapping.items():
        ch = discord.utils.get(guild.text_channels, name=name)
        out[key] = ch.mention if ch else "#" + name
    return out


# ── Выдача @member, когда оба шага пройдены ───────────────────────────────────
async def maybe_grant_member(member: discord.Member) -> None:
    rec = user_record(member.id)
    if rec.get("member_granted") or member.id in _granting:
        return
    if not (rec.get("rules_ack") and rec.get("goals")):
        return
    _granting.add(member.id)
    try:
        granted = await add_role_by_name(member, config.MEMBER_ROLE)
        if granted:
            await remove_role_by_name(member, config.NEWCOMER_ROLE)
            rec["member_granted"] = True
            await save_state()
            log.info("@member выдан: %s (цели=%s)", member, rec.get("goals"))
    finally:
        _granting.discard(member.id)


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
@client.event
async def on_ready():
    global _setup_started
    log.info("Бот запущен: %s", client.user)
    log.info("Гильдии: %s", [(g.name, g.id) for g in client.guilds])
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

    # выбор цели (💰🏢🚀🧠👀) — можно несколько; value-DM по каждой новой
    if config.GOALS_MESSAGE_ID and payload.message_id == config.GOALS_MESSAGE_ID:
        goal = config.GOAL_EMOJI.get(emoji)
        if goal is None:
            return
        rec = user_record(member.id)
        goals = rec["goals"]
        if goal not in goals:
            goals.append(goal)
            await save_state()
            lang = rec.get("lang") or content.DEFAULT_LANG
            mentions = channel_mentions(guild)
            await dm(member, content.value_dm(goal, lang, config.PRODUCT_URL, mentions))
            if goal == "earn":
                # 💰: просим Quanta ID (спека §8). Флаг заявки — только если
                # вопрос реально доставлен, иначе любое будущее ЛС боту
                # превратилось бы в «Quanta ID» без контекста.
                asked = await dm(member, content.QID_REQUEST_DM[lang].format(
                    ch_earn=mentions["ch_earn"]))
                if asked:
                    rec["pending_qid"] = True
                    await save_state()
                else:
                    log.warning("💰: не смог спросить Quanta ID у %s (ЛС закрыты)", member)
            log.info("Цель=%s (lang=%s), value-DM → %s", goal, lang, member)
        elif (goal == "earn" and not rec.get("pending_qid") and not rec.get("qid")):
            # rescue: 💰 уже выбрана, но Quanta ID так и не спросили (ЛС были
            # закрыты) — повторный клик реакции = повторная попытка спросить
            lang = rec.get("lang") or content.DEFAULT_LANG
            mentions = channel_mentions(guild)
            asked = await dm(member, content.QID_REQUEST_DM[lang].format(
                ch_earn=mentions["ch_earn"]))
            if asked:
                rec["pending_qid"] = True
                await save_state()
                log.info("💰 rescue: повторно спросил Quanta ID у %s", member)
        await maybe_grant_member(member)
        return


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.content.startswith("!"):
        # ЛС без команды: возможно, это ответ с Quanta ID на заявку 💰
        if message.guild is None:
            await maybe_capture_qid(message)
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
    log.info("Заявка 💰: %s → #%s (qid=%s)", message.author, config.APPLICATIONS_CHANNEL, qid)


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
