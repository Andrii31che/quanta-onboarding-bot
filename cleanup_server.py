"""
Уборка старых каналов по discord-channels-cleanup-2026-07-21.ru.md (часть 1).

Режимы (env CLEANUP_MODE):
  inventory — только чтение: список ВСЕХ каналов (имя/категория/тип) +
              для целей уборки — дата последнего сообщения и снапшот прав
              (точка отката). Ничего не меняет.
  apply     — исполнение шагов 2-6, 10 (появится после подтверждения списков).

ЖЕЛЕЗНОЕ ПРАВИЛО (приказ AC 2026-07-22): бот работает ТОЛЬКО по белому
списку TARGETS. Каналы компаний (lotos-signal, uniko, yesglobal, dubadu,
vimgrace, onetrade, rwa, pulse, street-energy и любые не из списка) — не
переименовываются, не переносятся, права не меняются, история НЕ читается.
В инвентаризации они присутствуют именем и категорией — этого достаточно.
"""

import json
import logging

import discord

import config

log = logging.getLogger("quanta-onboarding.cleanup")

# Белый список: единственные каналы, которые уборке разрешено ЧИТАТЬ и МЕНЯТЬ.
# Всё остальное — только имя в списке, никаких операций.
TARGETS = {
    # старые живые — на переименование (история сохраняется)
    "general-chat", "updates", "questions-feedback",
    # старые мёртвые/командные — кандидаты на удаление (по подтверждению AC)
    "materials", "intensive", "incubator", "brand-mind", "welcome",
    # в архив
    "random",
    # пустые двойники, созданные setup 14.07 — на снос
    "общее", "анонсы", "вопросы",
}


def _perm_snapshot(ch) -> dict:
    """Компактный снимок overwrites: имя цели → (allow, deny) битовые значения."""
    snap = {}
    for target, ow in ch.overwrites.items():
        allow, deny = ow.pair()
        snap[getattr(target, "name", str(target))] = [allow.value, deny.value]
    return snap


async def _last_message_iso(ch):
    try:
        async for msg in ch.history(limit=1):
            return msg.created_at.isoformat()[:16]
        return "пусто"
    except discord.HTTPException as e:
        return f"нет доступа ({e.status})"


async def inventory(client, guild: discord.Guild) -> None:
    log.info("=== INVENTORY: %r (id=%s), каналов всего: %d ===",
             guild.name, guild.id, len(guild.channels))
    report = {"targets": [], "untouched": [], "categories": []}
    for ch in guild.channels:
        if isinstance(ch, discord.CategoryChannel):
            report["categories"].append(
                {"name": ch.name, "id": ch.id, "children": len(ch.channels)})
            continue
        cat = ch.category.name if ch.category else "(без категории)"
        base = {"name": ch.name, "id": ch.id, "cat": cat,
                "type": str(ch.type)}
        if ch.name in TARGETS and isinstance(ch, discord.TextChannel):
            base["last_msg"] = await _last_message_iso(ch)
            base["perms"] = _perm_snapshot(ch)
            report["targets"].append(base)
        else:
            # вне белого списка (в т.ч. ВСЕ каналы компаний): имя и категория,
            # историю не читаем, права не снимаем
            report["untouched"].append(base)

    log.info("--- ЦЕЛИ УБОРКИ (%d) ---", len(report["targets"]))
    for t in report["targets"]:
        log.info("TARGET %s | кат=%s | посл.сообщение=%s",
                 t["name"], t["cat"], t["last_msg"])
        log.info("PERMS %s %s", t["name"], json.dumps(t["perms"], ensure_ascii=False))
    log.info("--- НЕ ТРОГАЕМ (%d) ---", len(report["untouched"]))
    for u in report["untouched"]:
        log.info("UNTOUCHED %s | кат=%s | тип=%s", u["name"], u["cat"], u["type"])
    log.info("--- КАТЕГОРИИ (%d) ---", len(report["categories"]))
    for c in report["categories"]:
        log.info("CATEGORY %s | каналов внутри: %d", c["name"], c["children"])
    log.info("=== INVENTORY DONE — сверь списки и подтверди перед apply ===")


# ── APPLY-1: обратимые шаги (переименования, права, дубли) ────────────────────
# Правки AC 22.07: категорию Text Channels НЕ трогаем, каналы НЕ переносим —
# только rename на месте; materials НЕ удаляется → это материалы-quanta.
RENAMES = [
    # (старое имя, новое имя, тир из setup_server, пустой-двойник на снос)
    ("general-chat", "общее", "write", "общее"),
    ("updates", "анонсы", "broadcast", "анонсы"),
    ("questions-feedback", "вопросы", "write", "вопросы"),
    ("materials", "материалы-quanta", "broadcast", None),
]

QUESTIONS_PIN = (
    "**Куда с чем идти:**\n"
    "Вопросы по продукту и серверу — сюда, отвечаем публично, ответ видят все.\n"
    "Нашёл баг — смотри инструкцию в #поддержка.\n"
    "Личное по аккаунту/платежу — тоже через #поддержка, не в общий чат."
)


async def _find_empty_double(guild, name: str):
    """Пустой двойник: канал с этим именем БЕЗ категории (создан setup 14.07)."""
    for ch in guild.text_channels:
        if ch.name == name and ch.category is None:
            async for _ in ch.history(limit=1):
                return None  # не пустой — не трогаем
            return ch
    return None


async def apply_renames(client, guild: discord.Guild) -> None:
    """Прогон 1 — обратимое. Fail-fast: первая ошибка останавливает всё."""
    import setup_server
    log.info("=== CLEANUP APPLY-1: переименования/права/дубли (fail-fast) ===")
    roles = {name: discord.utils.get(guild.roles, name=name)
             for name in (config.MEMBER_ROLE, config.AFFILIATE_ROLE)}
    team_roles = setup_server.resolve_team_roles(guild)

    for old, new, tier, double_name in RENAMES:
        ch = discord.utils.get(guild.text_channels, name=old)
        if ch is None:
            already = discord.utils.get(guild.text_channels, name=new)
            if already is not None and already.category is not None:
                log.info("Шаг %r→%r: уже сделан, пропускаю", old, new)
                continue
            log.error("СТОП: канал %r не найден (и %r в категории нет)", old, new)
            return
        # 1) двойник удаляем ДО переименования (чтобы не жить с дублем имени)
        if double_name:
            double = await _find_empty_double(guild, double_name)
            if double is not None:
                await double.delete(reason="Quanta cleanup: пустой двойник (часть 1)")
                log.info("Удалён пустой двойник #%s (id=%s)", double_name, double.id)
        # 2) права по тиру (merge — чужие overwrites не трогаем)
        plan = setup_server._overwrites(tier, guild, roles, team_roles)
        merged = dict(ch.overwrites)
        merged.update(plan)
        await ch.edit(name=new, overwrites=merged,
                      reason="Quanta cleanup: переименование с историей (часть 1)")
        log.info("Переименован #%s → #%s (тир %s), история цела", old, new, tier)

    # #анонсы → announcement-тип
    ann = discord.utils.get(guild.text_channels, name="анонсы")
    if ann is not None and "COMMUNITY" in guild.features:
        try:
            if ann.type is not discord.ChannelType.news:
                await ann.edit(type=discord.ChannelType.news)
                log.info("#анонсы переключён в announcement-тип")
        except (discord.HTTPException, TypeError) as e:
            log.warning("Не смог сделать #анонсы announcement: %s", e)

    # закреп-маршрутизатор в #вопросы (идемпотентно — ищем свой закреп)
    q = discord.utils.get(guild.text_channels, name="вопросы")
    if q is not None:
        try:
            pins = await q.pins()
            if not any(p.author.id == client.user.id and
                       p.content.startswith("**Куда с чем идти:**") for p in pins):
                msg = await q.send(QUESTIONS_PIN)
                await msg.pin(reason="Quanta cleanup: маршрутизатор (§4)")
                log.info("Закреп-маршрутизатор запощен в #вопросы")
            else:
                log.info("Закреп в #вопросы уже есть — пропускаю")
        except discord.HTTPException as e:
            log.error("Закреп в #вопросы не получился: %s", e)

    # random — скрыть на месте (не переносим: категорию не трогаем)
    rnd = discord.utils.get(guild.text_channels, name="random")
    if rnd is not None:
        merged = dict(rnd.overwrites)
        merged[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        member = roles.get(config.MEMBER_ROLE)
        if member is not None:
            merged[member] = discord.PermissionOverwrite(view_channel=False)
        await rnd.edit(overwrites=merged,
                       reason="Quanta cleanup: random в архив (скрыт на месте)")
        log.info("#random скрыт на месте (история цела; вернуть = открыть права)")
    log.info("=== APPLY-1 DONE — сверь сервер; удаления (intensive/welcome) "
             "идут отдельным прогоном apply2 после подтверждения AC ===")


# ── APPLY-2: необратимое (бэкап + удаления) — только после «ок» AC ────────────
DELETE_AFTER_BACKUP = ["intensive", "welcome"]


async def apply_deletions(client, guild: discord.Guild) -> None:
    log.info("=== CLEANUP APPLY-2: бэкап + удаления %s ===", DELETE_AFTER_BACKUP)
    for name in DELETE_AFTER_BACKUP:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch is None:
            log.info("#%s уже нет — пропускаю", name)
            continue
        try:
            count = 0
            async for msg in ch.history(limit=None, oldest_first=True):
                if msg.content or msg.attachments:
                    att = " ".join(a.url for a in msg.attachments)
                    log.info("BACKUP #%s | %s | %s | %s %s", name,
                             msg.created_at.isoformat()[:16], msg.author,
                             msg.content[:300], att)
                    count += 1
            log.info("Бэкап #%s: %d сообщений выгружено в лог", name, count)
            await ch.delete(reason="Quanta cleanup: удаление по плану части 1 (V)")
            log.info("Удалён #%s", name)
        except discord.HTTPException as e:
            log.error("СТОП на #%s: %s", name, e)
            return
    log.info("=== APPLY-2 DONE ===")


# ── HIDE_EARN: #заработок полностью скрыт (часть 2, чек-лист п.1) ────────────
async def apply_hide_earn(client, guild: discord.Guild) -> None:
    import setup_server
    ch = discord.utils.get(guild.text_channels, name=config.EARN_CHANNEL)
    if ch is None:
        log.error("HIDE_EARN: #%s не найден", config.EARN_CHANNEL)
        return
    roles = {name: discord.utils.get(guild.roles, name=name)
             for name in (config.MEMBER_ROLE, config.AFFILIATE_ROLE)}
    plan = setup_server._overwrites("earn", guild, roles,
                                    setup_server.resolve_team_roles(guild))
    merged = dict(ch.overwrites)
    merged.update(plan)
    await ch.edit(overwrites=merged,
                  reason="Quanta: #заработок скрыт полностью (часть 2, V 21.07)")
    log.info("HIDE_EARN DONE: #%s видят только @%s и команда",
             config.EARN_CHANNEL, config.AFFILIATE_ROLE)


# ── CUTOVER: снос реакций-якорей, пост-указатель + кнопка-починка ────────────
# Запускать ТОЛЬКО после зелёного теста нативной «Адаптации» (часть 3, п.3).
async def apply_cutover(client, guild: discord.Guild) -> None:
    import bot as botmod
    ch = discord.utils.get(guild.text_channels, name=config.START_CHANNEL)
    if ch is None:
        log.error("CUTOVER: #%s не найден", config.START_CHANNEL)
        return
    # 1) удалить якоря «язык» и «цели» (правила остаются закрепом)
    for var, mid in (("LANG_MESSAGE_ID", config.LANG_MESSAGE_ID),
                     ("GOALS_MESSAGE_ID", config.GOALS_MESSAGE_ID)):
        if not mid:
            continue
        try:
            msg = await ch.fetch_message(mid)
            await msg.delete()
            log.info("CUTOVER: якорь %s удалён", var)
        except discord.NotFound:
            log.info("CUTOVER: якорь %s уже удалён", var)
        except discord.HTTPException as e:
            log.error("CUTOVER: не удалить якорь %s: %s", var, e)
    # 2) пост-указатель с кнопкой-починкой (идемпотентно)
    try:
        pins = await ch.pins()
        if not any(p.author.id == client.user.id and
                   p.content.startswith("**Карта сервера") for p in pins):
            msg = await ch.send(
                botmod.fmt(botmod.content.START_POINTER,
                           botmod.content.DEFAULT_LANG, guild),
                view=botmod.FixView())
            await msg.pin(reason="Quanta: пост-указатель (часть 3)")
            log.info("CUTOVER: пост-указатель с кнопкой запощен и закреплён")
        else:
            log.info("CUTOVER: пост-указатель уже стоит")
    except discord.HTTPException as e:
        log.error("CUTOVER: указатель не встал: %s", e)
    log.info("CUTOVER DONE. Дальше: NATIVE_ONBOARDING=1 в Railway (если ещё "
             "не включён) и убери CLEANUP_MODE.")


async def run(client, guild: discord.Guild) -> None:
    mode = config.CLEANUP_MODE
    if mode == "inventory":
        await inventory(client, guild)
    elif mode == "apply1":
        await apply_renames(client, guild)
    elif mode == "apply2":
        await apply_deletions(client, guild)
    elif mode == "hide_earn":
        await apply_hide_earn(client, guild)
    elif mode == "cutover":
        await apply_cutover(client, guild)
    elif mode in ("", "0", "off"):
        pass  # выключено явно — не ошибка
    else:
        log.error("Неизвестный CLEANUP_MODE=%r", mode)
