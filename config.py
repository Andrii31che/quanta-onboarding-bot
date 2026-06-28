"""
Конфигурация онбординг-бота Quanta (Discord).

Всё, что зависит от конкретного сервера (имена ролей/каналов, ID
rules/segment-сообщений, ссылки), задаётся через переменные окружения —
чтобы тот, у кого есть admin-доступ к серверу, заполнил значения без правки кода.

Бот ищет роли и каналы ПО ИМЕНИ внутри гильдии, поэтому ID-каналов знать
не обязательно — достаточно, чтобы роли/каналы с этими именами существовали
(их создаёт owner по community-discord-redesign §3-4 = задача GROWTH-4).

Спека: quanta-docs/03-execution/growth/discord-onboarding-bot-spec-2026-06-16.md
"""

import os


def _get_int(name: str):
    """Прочитать int-переменную окружения; вернуть None, если не задана/пустая."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Переменная {name} должна быть числом (ID), получено: {raw!r}")


def _get_ids(name: str):
    """Список int-ID из переменной вида '123,456' → [123, 456]."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.append(int(part))
    return out


# ── Обязательное ─────────────────────────────────────────────────────────────
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

# ── Гильдия ──────────────────────────────────────────────────────────────────
# Если задан — бот работает только с этой гильдией (рекомендуется на проде).
GUILD_ID = _get_int("GUILD_ID")

# ── Роли (по имени на сервере; регистр важен) ────────────────────────────────
NEWCOMER_ROLE = os.environ.get("NEWCOMER_ROLE", "newcomer")
MEMBER_ROLE = os.environ.get("MEMBER_ROLE", "member")
AFFILIATE_ROLE = os.environ.get("AFFILIATE_ROLE", "affiliate")
HELPER_ROLE = os.environ.get("HELPER_ROLE", "helper")

# ── Каналы (по имени; без префикса #) ────────────────────────────────────────
START_HERE_CHANNEL = os.environ.get("START_HERE_CHANNEL", "start-here")

# ── Сообщения-якоря в #start-here ────────────────────────────────────────────
# ID сообщения с правилами (реакция ✅ = rules-ack) и ID сообщения выбора
# сегмента (reaction-role 🎨💼🚀📱👀). Owner создаёт сообщения и вставляет ID.
RULES_MESSAGE_ID = _get_int("RULES_MESSAGE_ID")
SEGMENT_MESSAGE_ID = _get_int("SEGMENT_MESSAGE_ID")

# Эмодзи подтверждения правил.
RULES_EMOJI = os.environ.get("RULES_EMOJI", "✅")

# ── Сегменты: эмодзи → внутренний ключ (порядок и ярлыки по спеке §1) ─────────
SEGMENT_EMOJI = {
    "🎨": "creator",        # Контент-создатель
    "💼": "expert",         # Эксперт / консультант
    "🚀": "entrepreneur",   # Предприниматель
    "📱": "blogger",        # Блогер
    "👀": "watcher",        # Просто смотрю
}

# Опционально: ключ сегмента → имя роли-тега (для сегментной аналитики/рассылок).
# Если роль с таким именем есть на сервере — бот её выдаст; если нет — просто
# запишет сегмент в state и пойдёт дальше (роль не обязательна).
SEGMENT_ROLE = {
    "creator": os.environ.get("ROLE_CREATOR", "seg-creator"),
    "expert": os.environ.get("ROLE_EXPERT", "seg-expert"),
    "entrepreneur": os.environ.get("ROLE_ENTREPRENEUR", "seg-entrepreneur"),
    "blogger": os.environ.get("ROLE_BLOGGER", "seg-blogger"),
    "watcher": os.environ.get("ROLE_WATCHER", "seg-watcher"),
}

# ── Ссылки-плейсхолдеры для value-DM (заполняются по мере готовности) ─────────
# Статус на 2026-06-16 (спека): demo пока нет (после GROWTH-6/14), Q-Lab —
# ссылка Андрея. Пока не заданы — подставляется нейтральная заглушка.
DEMO_URL = os.environ.get("DEMO_URL", "").strip()
QLAB_URL = os.environ.get("QLAB_URL", "").strip()

# ── Напоминание ──────────────────────────────────────────────────────────────
# Через сколько часов после join слать 1 напоминание, если онбординг не пройден.
REMINDER_HOURS = float(os.environ.get("REMINDER_HOURS", "24"))

# ── Админы (резолв по user-id, через запятую) ────────────────────────────────
# Могут пользоваться !affiliate / !stats даже без роли @helper.
ADMIN_IDS = _get_ids("ADMIN_IDS")

# ── Хранилище состояния ──────────────────────────────────────────────────────
STATE_PATH = os.environ.get("STATE_PATH", "data/state.json")
