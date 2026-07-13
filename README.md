# Quanta — онбординг-бот Discord (Phase 1)

Онбординг-гейт для сервера Quanta: новичок видит только `#старт`, пока не
примет правила (✅) и не выберет ≥1 цель 💰🏢🚀🧠👀 (можно несколько). После
этого получает `@member` и доступ к чатам. Бот шлёт value-DM по каждой цели,
для 💰 собирает Quanta ID и постит заявку в служебный `#заявки`, напоминает
раз через 24 ч, отвечает на `!faq` и даёт хелперам вручную выдавать
`@affiliate`. `SETUP_MODE=1` — разовая сборка сервера (роли, каналы §4,
грандфазер `@member`, якоря) — см. `setup_server.py`.

**Языки:** RU / UK / EN. Юзер выбирает язык реакцией-флагом 🇷🇺/🇺🇦/🇬🇧 в
`#старт` — value-DM, напоминания и `!faq` приходят на нём. Авто-DM при
входе — триязычный (язык ещё не выбран). Без выбора — RU (для `!faq` на латинице — EN).

**Спека:** `quanta-docs/03-execution/growth/discord-build-spec-2026-07-13.ru.md`
(+ тексты: `discord-valuedm-goals-2026-07-13.ru.md`).
**Задачи:** Plane GROWTH-4/5/10.
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

### 2. Admin — пустить бота на сервер
- OAuth2-ссылка из шага 1.4 (permissions: Manage Roles, Manage Channels,
  View Channels, Send Messages, Manage Messages, Read Message History,
  Add Reactions) → выбрать сервер Quanta → авторизовать.
- **Перетащить роль бота ВЫШЕ** ролей `newcomer/member/affiliate` в
  Server Settings → Roles (иначе бот не сможет их выдавать — это самая частая
  причина «бот молчит»).

### 3. SETUP_MODE — серверную структуру собирает сам бот
`SETUP_MODE=1` в Railway Variables → редеплой. Бот на старте разово:
- создаёт роли `newcomer/member/affiliate/helper/ambassador`;
- создаёт/переименовывает каналы на RU-имена и применяет тиры записи (§4);
- выдаёт `@member` всем текущим участникам (грандфазер §6);
- постит 3 якоря в `#старт` (правила ✅ / язык 🇷🇺🇺🇦🇬🇧 / цели 💰🏢🚀🧠👀)
  и печатает их ID в лог → вписать в `RULES_MESSAGE_ID` / `LANG_MESSAGE_ID` /
  `GOALS_MESSAGE_ID`, вернуть `SETUP_MODE=0`, передеплоить.
Идемпотентно: повторный прогон ничего не дублирует и ничего не удаляет.

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

**Статус (2026-06-28):** задеплоен и онлайн как `Quanta#0953`. Проект Railway
`quanta-onboarding-bot` (id `b7ca9edc-9d4d-4391-b0cd-cea611092ce6`), задеплоен
через `railway up` из локальной папки (без GitHub). `DISCORD_TOKEN` задан в
Railway Variables. Бот подключён к Gateway, но `Guilds=[]` — ещё не на сервере
(ждёт инвайта owner'ом, см. блок выше). `.railwayignore` исключает `.env`,
`.git`, `data/state.json` и кэш из загрузки.

Передеплой / обновление:

```bash
railway up        # из папки репо (нужен railway login)
```

Альтернатива — деплой из GitHub:

1. Залить репо на GitHub (`Andrii31che/quanta-onboarding-bot`).
2. Railway → проект → Deploy from GitHub repo → выбрать репо.
3. Service → **Variables** → внести значения из `env.example`
   (как минимум `DISCORD_TOKEN`, `GUILD_ID`, `RULES_MESSAGE_ID`,
   `LANG_MESSAGE_ID`, `GOALS_MESSAGE_ID`).
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
| `!stats` | helper/admin | срез онбординга: join / прошли гейт / цели / 💰-заявки |

## Состояние

`data/state.json` — кто на каком шаге (rules-ack, цели, язык, pending-заявка
💰, выдан ли `@member`, было ли напоминание). Гитигнорится. Переживает рестарт;
таймеры напоминаний восстанавливаются при старте.

## Известные ограничения Phase 1

- **Авто-`@affiliate`** (Фаза 2 спеки §3.2) не реализован — нужен эндпоинт
  id-server (сверка Quanta ID). Пока — ручная выдача через `!affiliate`.
- `data/state.json` хранится на диске инстанса. На Railway без volume он
  сбрасывается при редеплое — счётчики `!stats` обнулятся (онбординг-логика
  при этом не ломается). Для постоянной статистики — подключить volume.
- Ссылка `PRODUCT_URL` (цель 🚀) пока пустая → в value-DM подставляется
  нейтральная заглушка (URL не выдумываем). Заполнить перед запуском.
- **value-DM по каждой цели шлётся один раз** — при первом её выборе. Снятие
  реакции цель не убирает (add-only); повторный клик DM не дублирует.
  Это намеренное решение Phase 1 (анти-спам).
- Заявка 💰 (Quanta ID) постится в `#заявки`; если канал не найден — бот
  пишет ошибку в лог и юзеру НЕ подтверждает отправку.
- `TEAM_ROLES` не задан → «пишет команда» (#анонсы, #поддержка, #обучение)
  и видимость `#заявки` держатся на праве Administrator. Задай имена
  командных ролей и перегони setup, чтобы вплести их явно.
- Идемпотентность якорей — по точному тексту: поменял текст якоря в
  `content.py` → setup запостит НОВОЕ сообщение (старое удали руками,
  ID в Railway обнови).
- **Авторизация staff — по имени роли** (`helper`), не по ID. На сервере не
  должно быть второй роли с таким именем, и `@helper` должна быть доверенной,
  не самоназначаемой ролью — иначе её носители получат `!affiliate`/`!stats`.
