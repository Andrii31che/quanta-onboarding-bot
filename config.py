"""
Конфигурация онбординг-бота Quanta (Discord).

Всё, что зависит от конкретного сервера (имена ролей/каналов, ID якорных
сообщений, ссылки), задаётся через переменные окружения — чтобы тот, у кого
есть admin-доступ к серверу, заполнил значения без правки кода.

Бот ищет роли и каналы ПО ИМЕНИ внутри гильдии, поэтому ID-каналов знать
не обязательно — достаточно, чтобы роли/каналы с этими именами существовали.
В SETUP_MODE бот сам создаёт/переименовывает их (см. setup_server.py).

Спека: quanta-docs/03-execution/growth/discord-build-spec-2026-07-13.ru.md
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
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            raise ValueError(f"{name} должен быть списком числовых ID через запятую, "
                             f"некорректное значение: {part!r}")
    return out


def _get_float(name: str, default: str):
    """Прочитать float-переменную с понятной ошибкой вместо сырого traceback."""
    raw = os.environ.get(name, default).strip()
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Переменная {name} должна быть числом, получено: {raw!r}")


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
AMBASSADOR_ROLE = os.environ.get("AMBASSADOR_ROLE", "ambassador")

# Существующие КОМАНДНЫЕ роли (через запятую, «как есть» — спека §3): setup
# вплетает их в тиры «пишет команда» (#анонсы, #поддержка, #обучение) и в
# служебный #заявки. Пусто → эти каналы доступны команде только через
# permission Administrator (setup напишет предупреждение в лог).
TEAM_ROLES = [s.strip() for s in os.environ.get("TEAM_ROLES", "").split(",") if s.strip()]

# ── Каналы (по имени; без префикса #; спека §4 — имена на русском) ────────────
START_CHANNEL = os.environ.get("START_CHANNEL", "старт")
APPLICATIONS_CHANNEL = os.environ.get("APPLICATIONS_CHANNEL", "заявки")
EARN_CHANNEL = os.environ.get("EARN_CHANNEL", "заработок")
GENERAL_CHANNEL = os.environ.get("GENERAL_CHANNEL", "общее")
LEARN_CHANNEL = os.environ.get("LEARN_CHANNEL", "обучение")
WINS_CHANNEL = os.environ.get("WINS_CHANNEL", "результаты")
QUESTIONS_CHANNEL = os.environ.get("QUESTIONS_CHANNEL", "вопросы")

# ── Сообщения-якоря в #старт ─────────────────────────────────────────────────
# ID сообщения с правилами (реакция ✅ = rules-ack), выбора языка (флаги) и
# выбора целей (💰🏢🚀🧠👀). В SETUP_MODE бот сам постит якоря и печатает ID
# в лог — затем их вносят в переменные и передеплоивают.
RULES_MESSAGE_ID = _get_int("RULES_MESSAGE_ID")
LANG_MESSAGE_ID = _get_int("LANG_MESSAGE_ID")
GOALS_MESSAGE_ID = _get_int("GOALS_MESSAGE_ID")

# Эмодзи подтверждения правил.
RULES_EMOJI = os.environ.get("RULES_EMOJI", "✅")

# ── Выбор языка (reaction-role флагами) ──────────────────────────────────────
LANG_EMOJI = {"🇷🇺": "ru", "🇺🇦": "uk", "🇬🇧": "en"}

# ── Цели на входе (спека §2): эмодзи → внутренний ключ. Можно несколько. ──────
GOAL_EMOJI = {
    "💰": "earn",      # заработать на рекомендациях → #заработок (по партнёрке)
    "🏢": "company",   # развернуть Quanta на свою компанию/сеть → приватный канал
    "🚀": "business",  # автоматизировать свой бизнес → #общее + материалы
    "🧠": "learn",     # научиться AI на практике → #обучение
    "👀": "watch",     # осмотреться → всё открытое
}

# ── Ссылка для value-DM цели 🚀 («глянь, что она умеет») ─────────────────────
# Пока не задана — бот подставляет нейтральную заглушку (не выдумываем URL).
PRODUCT_URL = os.environ.get("PRODUCT_URL", "").strip()

# ── Напоминание ──────────────────────────────────────────────────────────────
# Через сколько часов после join слать 1 напоминание, если онбординг не пройден.
REMINDER_HOURS = _get_float("REMINDER_HOURS", "24")

# ── Админы (резолв по user-id, через запятую) ────────────────────────────────
# Могут пользоваться !affiliate / !stats даже без роли @helper.
ADMIN_IDS = _get_ids("ADMIN_IDS")

# ── CLEANUP_MODE ─────────────────────────────────────────────────────────────
# "inventory" — читающая инвентаризация каналов (часть 1 уборки, ничего не
# меняет); "apply" — исполнение уборки (включается отдельно после
# подтверждения списков). Пусто — выключено.
CLEANUP_MODE = os.environ.get("CLEANUP_MODE", "").strip().lower()

# ── SETUP_MODE ───────────────────────────────────────────────────────────────
# "1" → при старте бот один раз прогоняет setup_server.run(): роли, каналы
# с тирами записи (§4), грандфазер @member (§6), якоря в #старт (лог ID).
# Идемпотентно: существующее не трогается повторно. После успешного прогона
# переменную вернуть в "0"/убрать.
SETUP_MODE = os.environ.get("SETUP_MODE", "").strip() == "1"

# ── Хранилище состояния ──────────────────────────────────────────────────────
STATE_PATH = os.environ.get("STATE_PATH", "data/state.json")
