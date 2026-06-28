"""
Quanta Discord — онбординг-гейт бот (Phase 1).

Реализует discord-onboarding-bot-spec-2026-06-16.md:
  join → @newcomer + авто-DM → ✅ правила (rules-ack) → выбор сегмента
  (reaction-role) → сегментный value-DM → @member → доступ к tier-2 каналам.
  + 24ч напоминание (1 раз), команды !faq, !affiliate (Фаза 1), !stats.

Стек: discord.py + Python 3.12. Деплой: Railway worker (см. Procfile).
State: data/state.json (переживает рестарт; таймеры напоминаний
восстанавливаются на старте — см. resume_reminders).

Privileged intents (включить в Discord Developer Portal → Bot → Privileged
Gateway Intents): SERVER MEMBERS INTENT и MESSAGE CONTENT INTENT.
Права бота на сервере: Manage Roles (роль бота — ВЫШЕ управляемых ролей
в иерархии), плюс возможность видеть #start-here.
"""

import asyncio
import json
import logging
import os

import discord

import config
import content

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("quanta-onboarding")


# ── Состояние ────────────────────────────────────────────────────────────────
# { "<user_id>": {joined_at, rules_ack, segment, member_granted, reminded} }
state: dict = {}
_state_lock = asyncio.Lock()


def load_state() -> None:
    global state
    try:
        with open(config.STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        log.info("Состояние загружено: %d записей", len(state))
    except FileNotFoundError:
        state = {}
        log.info("Файл состояния не найден — старт с пустого состояния")
    except (json.JSONDecodeError, OSError) as e:
        state = {}
        log.warning("Не удалось прочитать состояние (%s) — старт с пустого", e)


async def save_state() -> None:
    """Атомарная запись через временный файл, под локом (без гонок)."""
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
            "rules_ack": False,
            "segment": None,
            "member_granted": False,
            "reminded": False,
        }
    return state[key]


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


# ── Выдача @member, когда оба шага пройдены ───────────────────────────────────
async def maybe_grant_member(member: discord.Member) -> None:
    rec = user_record(member.id)
    if rec.get("member_granted"):
        return
    if not (rec.get("rules_ack") and rec.get("segment")):
        return
    granted = await add_role_by_name(member, config.MEMBER_ROLE)
    if granted:
        await remove_role_by_name(member, config.NEWCOMER_ROLE)
        rec["member_granted"] = True
        await save_state()
        log.info("@member выдан: %s (сегмент=%s)", member, rec.get("segment"))


# ── Напоминание через REMINDER_HOURS ──────────────────────────────────────────
async def reminder_task(member: discord.Member, delay_seconds: float) -> None:
    try:
        await asyncio.sleep(delay_seconds)
    except asyncio.CancelledError:
        return
    rec = state.get(str(member.id))
    if not rec:
        return
    done = rec.get("rules_ack") and rec.get("segment")
    if rec.get("reminded") or done:
        return
    sent = await dm(member, content.REMINDER_DM)
    rec["reminded"] = True
    await save_state()
    if sent:
        log.info("Напоминание отправлено: %s", member)


def schedule_reminder(member: discord.Member, delay_seconds: float) -> None:
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
        done = rec.get("rules_ack") and rec.get("segment")
        if rec.get("reminded") or done or not rec.get("joined_at"):
            continue
        try:
            joined = datetime.datetime.fromisoformat(rec["joined_at"])
        except (ValueError, TypeError):
            continue
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
    if resumed:
        log.info("Восстановлено напоминаний: %d", resumed)


# ── События ──────────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    log.info("Бот запущен: %s", client.user)
    log.info("Гильдии: %s", [g.name for g in client.guilds])
    if config.GUILD_ID and not any(g.id == config.GUILD_ID for g in client.guilds):
        log.warning("GUILD_ID=%s — бот не состоит в этой гильдии!", config.GUILD_ID)
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
    await save_state()

    await add_role_by_name(member, config.NEWCOMER_ROLE)
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

    # выбор сегмента (reaction-role)
    if config.SEGMENT_MESSAGE_ID and payload.message_id == config.SEGMENT_MESSAGE_ID:
        segment = config.SEGMENT_EMOJI.get(emoji)
        if segment is None:
            return
        rec = user_record(member.id)
        first_choice = rec.get("segment") is None
        rec["segment"] = segment
        await save_state()
        # роль-тег сегмента (если есть на сервере)
        seg_role = config.SEGMENT_ROLE.get(segment)
        if seg_role:
            await add_role_by_name(member, seg_role)
        # value-DM шлём только при первом выборе (без спама при переключении)
        if first_choice:
            await dm(member, content.value_dm(segment, config.DEMO_URL, config.QLAB_URL))
            log.info("Сегмент=%s, value-DM → %s", segment, member)
        await maybe_grant_member(member)
        return


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.content.startswith("!"):
        return

    content_lower = message.content.strip()

    # !faq [тема]
    if content_lower == "!faq" or content_lower.startswith("!faq "):
        await handle_faq(message)
        return

    # дальше — только для гильдии и для staff
    if message.guild is None:
        return
    if config.GUILD_ID and message.guild.id != config.GUILD_ID:
        return

    if content_lower.startswith("!affiliate"):
        await handle_affiliate(message)
        return
    if content_lower == "!stats":
        await handle_stats(message)
        return


# ── Команды ──────────────────────────────────────────────────────────────────
async def handle_faq(message: discord.Message):
    arg = message.content[len("!faq"):].strip().lower()
    if not arg:
        topics = ", ".join(t["title"] for t in content.FAQ_TOPICS.values())
        await message.reply(
            "Темы FAQ: " + topics + "\nНапример: `!faq оплата`"
        )
        return
    matches = []
    for topic in content.FAQ_TOPICS.values():
        if any(alias in arg for alias in topic["aliases"]):
            matches.append(topic)
    if not matches:
        topic_names = ", ".join(t["title"] for t in content.FAQ_TOPICS.values())
        await message.reply(content.FAQ_FALLBACK.format(topics=topic_names))
        return
    # до 3 совпадений, чтобы не заспамить
    reply = "\n\n".join(f"**{t['title']}**\n{t['answer']}" for t in matches[:3])
    await message.reply(reply)


async def handle_affiliate(message: discord.Message):
    """Фаза 1 (интерим): ручная выдача @affiliate хелпером/админом."""
    if not is_staff(message.author):
        return
    if not message.mentions:
        await message.reply("Использование: `!affiliate @пользователь`")
        return
    granted_to = []
    for target in message.mentions:
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
    total = len(state)
    passed = sum(1 for r in state.values() if r.get("rules_ack") and r.get("segment"))
    members = sum(1 for r in state.values() if r.get("member_granted"))
    by_segment = {}
    for r in state.values():
        seg = r.get("segment")
        if seg:
            by_segment[seg] = by_segment.get(seg, 0) + 1
    pct = (passed / total * 100) if total else 0
    seg_lines = "\n".join(
        f"  • {content.SEGMENT_LABEL.get(k, k)}: {v}" for k, v in by_segment.items()
    ) or "  (пока нет)"
    await message.reply(
        f"**Онбординг (с момента последнего сброса state)**\n"
        f"Всего join: {total}\n"
        f"Прошли гейт (правила + сегмент): {passed} ({pct:.0f}%)\n"
        f"Получили @{config.MEMBER_ROLE}: {members}\n"
        f"Сегментный срез:\n{seg_lines}"
    )


def main():
    load_state()
    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
