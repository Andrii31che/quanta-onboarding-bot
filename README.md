# Quanta — онбординг-бот Discord (Phase 1)

Онбординг-гейт для сервера Quanta: новичок видит только `#start-here`, пока не
примет правила (✅) и не выберет сегмент. После этого получает `@member` и
доступ к чатам. Бот шлёт сегментный value-DM, напоминает раз через 24 ч,
отвечает на `!faq` и даёт хелперам вручную выдавать `@affiliate`.

**Спека:** `quanta-docs/03-execution/growth/discord-onboarding-bot-spec-2026-06-16.md`
**Задачи:** Plane GROWTH-5 (бот) + GROWTH-10 (`!faq`).
**Стек:** discord.py 2.3.2, Python 3.12. Деплой: Railway worker.

---

## ⚠️ Что нужно, чтобы бот ожил (по ролям)

Код готов. Чтобы он заработал на сервере, нужны три вещи, которые делаются
**вне кода** — без них бот запустится, но управлять будет нечем:

### 1. Andre — создать бота и токен (≈2 мин, admin-права на сервере НЕ нужны)
1. https://discord.com/developers/applications → **New Application** → назови (напр. `Quanta Onboarding`).
2. Вкладка **Bot** → **Reset Token** → скопируй → это `DISCORD_TOKEN`.
3. Вкладка **Bot** → **Privileged Gateway Intents** → включи:
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**
4. Вкладка **OAuth2 → URL Generator**: scopes `bot`; Bot Permissions:
   `Manage Roles`, `Read Messages/View Channels`, `Send Messages`,
   `Read Message History`, `Add Reactions`. Скопируй сгенерированную ссылку —
   она нужна owner'у для шага 3.

### 2. Owner сервера — серверная структура (это и есть задача GROWTH-4)
Бот ищет роли и каналы **по имени**, поэтому достаточно их создать:
- Роли: `newcomer`, `member`, `affiliate`, `helper`
  (+ опц. `seg-creator/expert/entrepreneur/blogger/watcher` для аналитики).
- Канал `start-here` (read-only для `@newcomer`); tier-2 каналы
  (`general`, `wins`, `questions`, `affiliate`) — на запись только для `@member`+.
- Write-tiers по `community-discord-redesign §3-4`.

### 3. Owner — пустить бота на сервер (нужны права Manage Server)
- Открыть OAuth2-ссылку из шага 1.4 → выбрать сервер Quanta → авторизовать.
- **Перетащить роль бота ВЫШЕ** ролей `newcomer/member/affiliate` в
  Server Settings → Roles (иначе бот не сможет их выдавать — это самая частая
  причина «бот молчит»).
- В `#start-here` запостить сообщение с правилами и сообщение выбора сегмента,
  скопировать их Message ID (Developer Mode → ПКМ → Copy Message ID) →
  вписать в `RULES_MESSAGE_ID` и `SEGMENT_MESSAGE_ID`.
  Под сегмент-сообщение добавить реакции 🎨💼🚀📱👀.

---

## Локальный запуск

```bash
cd ~/Projects/quanta-onboarding-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env          # заполни DISCORD_TOKEN и остальное
python bot.py
```

## Деплой на Railway

1. Залить репо на GitHub (`Andrii31che/quanta-onboarding-bot`).
2. Railway → New Project → Deploy from GitHub repo → выбрать репо.
3. Service → **Variables** → внести значения из `env.example`
   (как минимум `DISCORD_TOKEN`, `GUILD_ID`, `RULES_MESSAGE_ID`,
   `SEGMENT_MESSAGE_ID`).
4. Деплой стартует сам (worker по `Procfile` / `railway.json`).

---

## Конфигурация

Всё — через переменные окружения, см. `env.example`. Бот сопоставляет роли и
каналы по имени внутри гильдии, ID-каналов знать не нужно. Имена ролей/каналов
переопределяются переменными (`NEWCOMER_ROLE` и т.д.).

## Команды

| Команда | Кто | Что |
|---|---|---|
| `!faq` | все | список тем FAQ |
| `!faq <тема>` | все | выверенный ответ (напр. `!faq оплата`, `!faq вывод`) |
| `!affiliate @user` | helper/admin | вручную выдать `@affiliate` (Фаза 1, интерим) |
| `!stats` | helper/admin | срез онбординга: join / прошли гейт / сегменты |

## Состояние

`data/state.json` — кто на каком шаге (rules-ack, сегмент, выдан ли `@member`,
было ли напоминание). Гитигнорится. Переживает рестарт; таймеры напоминаний
восстанавливаются при старте.

## Известные ограничения Phase 1

- **Авто-`@affiliate`** (Фаза 2 спеки §3.2) не реализован — нужен эндпоинт
  id-server (сверка Quanta ID). Пока — ручная выдача через `!affiliate`.
- `data/state.json` хранится на диске инстанса. На Railway без volume он
  сбрасывается при редеплое — счётчики `!stats` обнулятся (онбординг-логика
  при этом не ломается). Для постоянной статистики — подключить volume.
- Ссылки `DEMO_URL` / `QLAB_URL` пока пустые → в value-DM подставляется
  нейтральная заглушка (URL не выдумываем). Заполнить, когда будут готовы.
