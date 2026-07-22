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


async def run(client, guild: discord.Guild) -> None:
    mode = config.CLEANUP_MODE
    if mode == "inventory":
        await inventory(client, guild)
    elif mode == "apply":
        log.error("CLEANUP apply ещё не включён — сначала подтверждение списков AC")
    else:
        log.error("Неизвестный CLEANUP_MODE=%r", mode)
