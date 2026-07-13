"""
Разовая сборка сервера Quanta по discord-build-spec-2026-07-13.ru.md (§3-§6).

Запускается из bot.py при SETUP_MODE=1 (после инвайта бота с правами
Manage Roles + Manage Channels). Всё ИДЕМПОТЕНТНО:
  - роли: find-or-create по имени;
  - каналы: RU-имя есть → используем; легаси EN-имя есть → переименовываем
    (история и закрепы сохраняются); нет — создаём. Тиры записи (§4)
    применяются МЕРЖЕМ overwrites: свои ключи (@everyone, @member,
    @affiliate, командные роли, бот) перезаписываются по плану, чужие
    (роли компаний, ручные правки) не трогаются;
  - грандфазер (§6) идёт ДО применения тиров — ни секунды блэкаута
    для текущих участников;
  - каналы ВНЕ спеки, видимые @everyone, прячутся от @newcomer
    (§5: новичок видит только #старт) — точечным set_permissions;
  - якоря в #старт: если уже запощены ботом — переиспользуются, иначе
    постятся заново; ID печатаются в лог для Railway Variables.

Ничего НЕ удаляется: лишние старые каналы (напр. #faq, #events) и каналы
компаний остаются — решение по ним за AC.
"""

import logging

import discord

import config
import content

log = logging.getLogger("quanta-onboarding.setup")

# Роли Phase 1 (спека §3). @student — позже, со стартом школы.
ROLE_NAMES = [
    config.NEWCOMER_ROLE,
    config.MEMBER_ROLE,
    config.AFFILIATE_ROLE,
    config.HELPER_ROLE,
    config.AMBASSADOR_ROLE,
]

# Каналы §4: (имя из config, легаси-имена для переименования, топик, тир).
# Тиры записи: start — видят все, пишет бот; broadcast — читает @member,
# пишет команда; write — пишут @member; learn — читает @member, посты команда,
# обсуждение в тредах; earn — пишут @affiliate (+команда); apps — служебный,
# видят команда и бот.
CHANNEL_SPECS = [
    (config.START_CHANNEL, ["start-here"],
     "Правила, выбор языка и цели. Два шага — и все каналы открыты.", "start"),
    ("анонсы", ["announcements"],
     "Релизы продукта и анонсы эфиров. Пишет команда.", "broadcast"),
    ("поддержка", ["support"],
     "Как сообщить о баге (report-bug на сайте) и куда писать, если не решилось.",
     "broadcast"),
    (config.GENERAL_CHANNEL, ["general"],
     "Свободный разговор.", "write"),
    (config.WINS_CHANNEL, ["wins", "results"],
     "Работы участников: что сделали в Quanta. Покажи своё!", "write"),
    (config.QUESTIONS_CHANNEL, ["questions"],
     "Вопросы и ответы — видны всем. Личное по аккаунту — через поддержку.",
     "write"),
    (config.EARN_CHANNEL, ["affiliate", "earn"],
     "Партнёрка: как приводить людей, лидерборд. Пишут партнёры с активной ссылкой.",
     "earn"),
    (config.LEARN_CHANNEL, ["quanta-school", "q-lab"],
     "Q-Lab: бесплатные AI-уроки и материалы. Обсуждение — в тредах.", "learn"),
    (config.APPLICATIONS_CHANNEL, ["applications"],
     "Служебный: заявки на #заработок от бота (Quanta ID). Видит только команда.",
     "apps"),
]

def _team_overwrite() -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        view_channel=True, send_messages=True, send_messages_in_threads=True,
        create_public_threads=True, add_reactions=True,
        read_message_history=True)


def _overwrites(tier: str, guild: discord.Guild, roles: dict,
                team_roles: list) -> dict:
    """Собрать ПЛАН overwrites канала по тиру записи (§4) — только наши ключи."""
    everyone = guild.default_role
    member = roles.get(config.MEMBER_ROLE)
    affiliate = roles.get(config.AFFILIATE_ROLE)
    me = guild.me
    deny_view = discord.PermissionOverwrite(view_channel=False)
    bot_full = discord.PermissionOverwrite(
        view_channel=True, send_messages=True, manage_messages=True,
        add_reactions=True, read_message_history=True)

    if tier == "start":
        # видят ВСЕ (включая @newcomer до гейта), пишет только бот
        ow = {
            everyone: discord.PermissionOverwrite(
                view_channel=True, send_messages=False,
                send_messages_in_threads=False, create_public_threads=False,
                create_private_threads=False, add_reactions=True,
                read_message_history=True),
            me: bot_full,
        }
    elif tier == "broadcast":
        ow = {
            everyone: deny_view,
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=False,
                send_messages_in_threads=False, create_public_threads=False,
                create_private_threads=False, add_reactions=True,
                read_message_history=True),
            me: bot_full,
        }
        for t in team_roles:
            ow[t] = _team_overwrite()
    elif tier == "write":
        ow = {
            everyone: deny_view,
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True),
            me: bot_full,
        }
    elif tier == "learn":
        # читают участники, посты — команда; обсуждение в тредах открыто
        ow = {
            everyone: deny_view,
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=False,
                send_messages_in_threads=True, create_public_threads=False,
                create_private_threads=False, add_reactions=True,
                read_message_history=True),
            me: bot_full,
        }
        for t in team_roles:
            ow[t] = _team_overwrite()
    elif tier == "earn":
        # читают участники, пишут @affiliate (+команда — лидерборд и т.п.)
        ow = {
            everyone: deny_view,
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=False, add_reactions=True,
                read_message_history=True),
            affiliate: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True),
            me: bot_full,
        }
        for t in team_roles:
            ow[t] = _team_overwrite()
    elif tier == "apps":
        # служебный: @everyone не видит; команда и бот — видят
        ow = {everyone: deny_view, me: bot_full}
        for t in team_roles:
            ow[t] = _team_overwrite()
    else:
        raise ValueError(f"неизвестный тир: {tier}")
    # роль могла не создаться (None-ключ ломает API) — вычищаем
    return {k: v for k, v in ow.items() if k is not None}


async def ensure_roles(guild: discord.Guild) -> dict:
    roles = {}
    for name in ROLE_NAMES:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            try:
                role = await guild.create_role(name=name, reason="Quanta setup")
                log.info("Роль создана: @%s", name)
            except discord.HTTPException as e:
                log.error("Не удалось создать роль @%s: %s", name, e)
                continue
        else:
            log.info("Роль уже есть: @%s", name)
        roles[name] = role
    return roles


def resolve_team_roles(guild: discord.Guild) -> list:
    """Существующие командные роли (§3 «как есть») по именам из TEAM_ROLES."""
    found = []
    for name in config.TEAM_ROLES:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            log.warning("TEAM_ROLES: роль %r на сервере не найдена — пропускаю", name)
        else:
            found.append(role)
    if not found:
        log.warning(
            "TEAM_ROLES пуст/не найдены: #анонсы, #поддержка, #обучение и #заявки "
            "будут доступны команде только через право Administrator. Задай "
            "TEAM_ROLES в Railway и перезапусти setup, чтобы вплести роли команды.")
    return found


async def ensure_channel(guild: discord.Guild, name: str, legacy: list,
                         topic: str, tier: str, roles: dict, team_roles: list):
    """RU-имя есть → используем; легаси → rename; нет → create. Затем тир.

    Overwrites МЕРЖАТСЯ: план перекрывает только свои ключи, чужие
    (роли компаний, ручные правки) сохраняются."""
    ch = discord.utils.get(guild.text_channels, name=name)
    if ch is None:
        for old in legacy:
            ch = discord.utils.get(guild.text_channels, name=old)
            if ch is not None:
                try:
                    await ch.edit(name=name, reason="Quanta setup: RU-имена (§4)")
                    log.info("Канал переименован: #%s → #%s", old, name)
                except discord.HTTPException as e:
                    log.error("Не удалось переименовать #%s → #%s: %s", old, name, e)
                break
    plan = _overwrites(tier, guild, roles, team_roles)
    if ch is None:
        try:
            ch = await guild.create_text_channel(
                name, overwrites=plan, topic=topic, reason="Quanta setup")
            log.info("Канал создан: #%s (тир %s)", name, tier)
        except discord.HTTPException as e:
            log.error("Не удалось создать #%s: %s", name, e)
            return None
    else:
        merged = dict(ch.overwrites)
        merged.update(plan)
        try:
            await ch.edit(overwrites=merged, topic=topic,
                          reason="Quanta setup: тиры записи (§4)")
            log.info("Канал обновлён: #%s (тир %s)", name, tier)
        except discord.HTTPException as e:
            log.error("Не удалось применить тир к #%s: %s", name, e)
    return ch


async def grandfather_members(guild: discord.Guild, roles: dict) -> None:
    """§6: всем текущим не-ботам разом выдать @member — никого не запирать.

    Вызывается ДО применения тиров к каналам, иначе на время прогона весь
    сервер ослеп бы (deny @everyone ложится раньше, чем у людей есть роль)."""
    member_role = roles.get(config.MEMBER_ROLE)
    if member_role is None:
        log.error("Грандфазер пропущен: роли @%s нет", config.MEMBER_ROLE)
        return
    todo = [m for m in guild.members
            if not m.bot and member_role not in m.roles]
    log.info("Грандфазер: выдаю @%s %d участникам…", config.MEMBER_ROLE, len(todo))
    done = 0
    for m in todo:
        try:
            await m.add_roles(member_role, reason="Quanta setup: грандфазер §6")
            done += 1
            if done % 25 == 0:
                log.info("Грандфазер: %d/%d", done, len(todo))
        except discord.HTTPException as e:
            log.error("Грандфазер: не выдал @member %s: %s", m, e)
    log.info("Грандфазер готов: %d/%d", done, len(todo))


async def hide_extras_from_newcomers(guild: discord.Guild, roles: dict,
                                     keep_ids: set) -> None:
    """§5: новичок видит только #старт. Спековые каналы закрыты через
    @everyone deny; каналы ВНЕ спеки (легаси #faq, #events, будущие ручные)
    иначе остались бы видимы новичку — прячем их от @newcomer точечно.
    set_permissions заменяет overwrite только ДЛЯ @newcomer на этом канале,
    overwrites других ролей не трогает. Скип — по ID резолвнутых спековых
    каналов (не по имени: дубль имени или войс «старт» не должны проскочить)."""
    newcomer = roles.get(config.NEWCOMER_ROLE)
    if newcomer is None:
        return
    hidden = []
    for ch in guild.channels:
        if ch.id in keep_ids:
            continue
        ow = ch.overwrites_for(guild.default_role)
        if ow.view_channel is False:
            continue  # уже приватный (каналы компаний и т.п.)
        cur = ch.overwrites_for(newcomer)
        if cur.view_channel is False:
            continue  # уже спрятан прошлым прогоном
        try:
            await ch.set_permissions(
                newcomer, view_channel=False,
                reason="Quanta setup: @newcomer видит только #старт (§5)")
            hidden.append("#" + ch.name)
        except discord.HTTPException as e:
            log.error("Не смог спрятать #%s от @newcomer: %s", ch.name, e)
    if hidden:
        log.info("Спрятаны от @newcomer вне-спековые каналы: %s", ", ".join(hidden))


async def _find_existing_anchor(ch, client, text: str):
    """Найти уже запощенный ботом якорь с точно таким текстом (идемпотентность).
    Внимание: правка текста якоря в content.py между прогонами = «не найден»
    → будет запощен дубль. Менял текст — удали старый якорь руками."""
    try:
        async for msg in ch.history(limit=50):
            if msg.author.id == client.user.id and msg.content == text:
                return msg
    except discord.HTTPException as e:
        log.warning("Не смог просмотреть историю #%s: %s", ch.name, e)
    return None


async def post_anchors(client, ch) -> None:
    """3 якоря в #старт: правила / язык / цели. Печатает ID для Railway."""
    if config.RULES_MESSAGE_ID and config.LANG_MESSAGE_ID and config.GOALS_MESSAGE_ID:
        log.info("Якоря уже сконфигурированы (ID заданы) — пропускаю постинг")
        return
    plan = [
        ("RULES_MESSAGE_ID", content.ANCHOR_RULES, [config.RULES_EMOJI]),
        ("LANG_MESSAGE_ID", content.ANCHOR_LANG, list(config.LANG_EMOJI)),
        ("GOALS_MESSAGE_ID", content.ANCHOR_GOALS, list(config.GOAL_EMOJI)),
    ]
    results = []
    for var, text, emojis in plan:
        msg = await _find_existing_anchor(ch, client, text)
        if msg is None:
            msg = await ch.send(text)
            log.info("Якорь запощен: %s", var)
        else:
            log.info("Якорь уже был: %s (переиспользую)", var)
        for e in emojis:
            try:
                await msg.add_reaction(e)
            except discord.HTTPException:
                pass
        try:
            if not msg.pinned:
                await msg.pin(reason="Quanta setup: якорь онбординга")
        except discord.HTTPException:
            log.warning("Не смог закрепить якорь %s (нужен Manage Messages)", var)
        results.append((var, msg.id))
    log.info("=== ЯКОРЯ ГОТОВЫ — впиши в Railway Variables и передеплой: ===")
    for var, mid in results:
        log.info("%s=%s", var, mid)


async def run(client, guild: discord.Guild) -> None:
    log.info("=== SETUP_MODE: собираю сервер %r (id=%s) по спеке §3-§6 ===",
             guild.name, guild.id)
    my_perms = guild.me.guild_permissions
    if not (my_perms.manage_roles and my_perms.manage_channels):
        log.error("SETUP: не хватает прав (нужны Manage Roles + Manage Channels) — стоп")
        return
    try:
        roles = await ensure_roles(guild)
        team_roles = resolve_team_roles(guild)
        # грандфазер ДО тиров: deny-@everyone не должен ослепить текущих (§6)
        await grandfather_members(guild, roles)
        channels = {}
        for name, legacy, topic, tier in CHANNEL_SPECS:
            ch = await ensure_channel(guild, name, legacy, topic, tier,
                                      roles, team_roles)
            if ch is not None:
                channels[name] = ch
        # #анонсы → announcement-канал, если включён Community-режим
        ann = channels.get("анонсы")
        if ann is not None and "COMMUNITY" in guild.features:
            try:
                if ann.type is not discord.ChannelType.news:
                    await ann.edit(type=discord.ChannelType.news)
                    log.info("#анонсы переключён в announcement-тип")
            except (discord.HTTPException, TypeError) as e:
                log.warning("Не смог сделать #анонсы announcement-каналом: %s", e)
        # скрываем от новичка всё, что НЕ входит в спековые каналы (по ID)
        keep_ids = {ch.id for ch in channels.values()}
        await hide_extras_from_newcomers(guild, roles, keep_ids)
        start = channels.get(config.START_CHANNEL)
        if start is not None:
            await post_anchors(client, start)
        else:
            log.error("#%s не найден/не создан — якоря не запощены",
                      config.START_CHANNEL)
        log.info("=== SETUP DONE. Дальше: впиши ID якорей в Railway, SETUP_MODE=0, "
                 "передеплой. Порядок каналов расставь в UI перетаскиванием. ===")
    except Exception:
        log.exception("SETUP: неожиданная ошибка — прогон остановлен")
