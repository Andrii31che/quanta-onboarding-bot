"""
Тексты онбординг-бота Quanta. Customer-facing. Языки: RU / UK / EN.

Источник RU (НЕ переписывать формулировки — прошли forbidden-scan #606):
- 5 value-DM (цели): discord-valuedm-goals-2026-07-13.ru.md
- FAQ:               sales-lead-valuedm-faq-2026-06-16.md §B (выверено по Module 12)
- авто-DM / REMINDER / якоря / QID: bot-authored по спеке
  discord-build-spec-2026-07-13.ru.md §5, проверены на #606 вручную.

UK/EN — переводы RU-оригинала. Сохранены факты (минимум вывода $10, кредиты
12 мес, USDC/BEP20, помесячная лицензия, возврата нет) и запреты #606 на
каждом языке: без «пирамида/пассивный доход/реферал/гарантированно/успей»
(и их UK/EN эквивалентов), без имён AI-провайдеров, «лицензия/license»
не «подписка/subscription». Названия каналов — русские во всех языках
(бот оформляет их Discord-упоминаниями, спека value-DM).

Язык юзера хранится в state (rec["lang"]); выбирается реакцией-флагом
🇷🇺/🇺🇦/🇬🇧 в #старт. Пока не выбран — DEFAULT_LANG.
"""

LANGS = ("ru", "uk", "en")
DEFAULT_LANG = "ru"

# ── Шаг [2]: авто-DM при join — триязычный (язык ещё не выбран) ───────────────
AUTO_DM = (
    "🇷🇺 Привет 👋 Рад, что заглянул(а) в Quanta. Чтобы открыть доступ к чатам, "
    "зайди в **#старт** и сделай пару шагов: выбери язык (флаг), поставь ✅ "
    "под правилами и отметь свою цель — можно несколько. После этого добро "
    "пожаловать внутрь.\n\n"
    "🇺🇦 Привіт 👋 Радий, що завітав(ла) у Quanta. Щоб відкрити доступ до чатів, "
    "зайди в **#старт** і зроби кілька кроків: обери мову (прапор), постав ✅ "
    "під правилами та познач свою ціль — можна кілька. Після цього ласкаво "
    "просимо досередини.\n\n"
    "🇬🇧 Hi 👋 Glad you stopped by Quanta. To unlock the chats, head to "
    "**#старт** and take a couple of steps: pick your language (flag), tick ✅ "
    "under the rules, and mark your goal — you can pick several. Then welcome "
    "inside."
)

# ── Напоминание через 24ч (1 раз), по языку ──────────────────────────────────
REMINDER_DM = {
    "ru": (
        "Напоминаю про вход в Quanta 🙂 Остались два коротких шага в **#старт**: "
        "✅ под правилами и выбор цели. После них откроются чаты. "
        "Если что-то непонятно — набери здесь `!faq`, подскажу."
    ),
    "uk": (
        "Нагадую про вхід у Quanta 🙂 Лишилися два короткі кроки в **#старт**: "
        "✅ під правилами та вибір цілі. Після них відкриються чати. "
        "Якщо щось незрозуміло — набери тут `!faq`, підкажу."
    ),
    "en": (
        "A quick nudge about joining Quanta 🙂 Two short steps left in **#старт**: "
        "tick ✅ under the rules and pick your goal. The chats open right after. "
        "If anything's unclear, type `!faq` here and I'll help."
    ),
}

# ── Заглушка для незаполненной ссылки продукта (не выдумываем URL) ────────────
PRODUCT_FALLBACK = {
    "ru": "ссылку пришлю отдельно",
    "uk": "посилання надішлю окремо",
    "en": "I'll send the link separately",
}


# ── 5 value-DM под цели × 3 языка ────────────────────────────────────────────
# Тексты — discord-valuedm-goals-2026-07-13.ru.md (forbidden-scan PASS,
# НЕ переписывать формулировки). Плейсхолдеры {ch_*} бот резолвит в
# Discord-упоминания каналов (<#id>), поэтому имена каналов одинаковые
# (русские) во всех языках.
_VALUE_DM = {
    "ru": {
        "earn": (
            "Привет! Рад, что ты здесь 👋 У тебя есть личная ссылка Quanta — "
            "по ней люди заходят в экосистему, а тебе идёт комиссия с их оплат. "
            "Два шага: 1) забери свою ссылку в кабинете; "
            "2) загляни в {ch_earn} — покажу, как привести первых."
        ),
        "company": (
            "Привет! Если у тебя своя команда или сеть — Quanta заводится под "
            "твой бренд: посты, видео и материалы под твою компанию. "
            "Два шага: 1) напиши, что за компания; "
            "2) подключим её и дадим тебе закрытый канал для твоих людей."
        ),
        "business": (
            "Привет! Вместо десятка отдельных сервисов — одна система: контент, "
            "видео и тексты под твой бизнес в одном месте. "
            "Два шага: 1) глянь, что она умеет → {product}; "
            "2) вопросы — в {ch_general}, подскажу с чего начать."
        ),
        "learn": (
            "Привет! Здесь можно бесплатно освоить AI — на реальных "
            "инструментах, а не в теории. "
            "Два шага: 1) зайди в {ch_learn} (Q-Lab); "
            "2) сделай первое задание — дальше подскажу, куда двигаться."
        ),
        "watch": (
            "Привет! Осмотрись без обязательств. Хочешь — бесплатно попробуй "
            "AI в {ch_learn}, глянь в {ch_wins}, что делают другие. "
            "Если что-то зацепит — спроси в {ch_questions}, подскажу."
        ),
    },
    "uk": {
        "earn": (
            "Привіт! Радий, що ти тут 👋 У тебе є особисте посилання Quanta — "
            "за ним люди заходять в екосистему, а тобі йде комісія з їхніх "
            "оплат. Два кроки: 1) забери своє посилання в кабінеті; "
            "2) зазирни в {ch_earn} — покажу, як привести перших."
        ),
        "company": (
            "Привіт! Якщо в тебе своя команда чи мережа — Quanta налаштовується "
            "під твій бренд: пости, відео та матеріали під твою компанію. "
            "Два кроки: 1) напиши, що за компанія; "
            "2) підключимо її та дамо тобі закритий канал для твоїх людей."
        ),
        "business": (
            "Привіт! Замість десятка окремих сервісів — одна система: контент, "
            "відео й тексти під твій бізнес в одному місці. "
            "Два кроки: 1) поглянь, що вона вміє → {product}; "
            "2) питання — в {ch_general}, підкажу з чого почати."
        ),
        "learn": (
            "Привіт! Тут можна безкоштовно опанувати AI — на реальних "
            "інструментах, а не в теорії. "
            "Два кроки: 1) зайди в {ch_learn} (Q-Lab); "
            "2) зроби перше завдання — далі підкажу, куди рухатися."
        ),
        "watch": (
            "Привіт! Роздивись без зобов'язань. Хочеш — безкоштовно спробуй "
            "AI в {ch_learn}, поглянь у {ch_wins}, що роблять інші. "
            "Якщо щось зачепить — запитай у {ch_questions}, підкажу."
        ),
    },
    "en": {
        "earn": (
            "Hey! Glad you're here 👋 You have a personal Quanta link — people "
            "join the ecosystem through it, and you earn a commission on their "
            "payments. Two steps: 1) grab your link in your dashboard; "
            "2) drop into {ch_earn} — I'll show you how to bring your first ones."
        ),
        "company": (
            "Hey! If you have your own team or network — Quanta sets up under "
            "your brand: posts, videos, and materials for your company. "
            "Two steps: 1) tell me what company it is; "
            "2) we'll connect it and give you a private channel for your people."
        ),
        "business": (
            "Hey! Instead of a dozen separate services — one system: content, "
            "video, and copy for your business in one place. "
            "Two steps: 1) see what it can do → {product}; "
            "2) questions — in {ch_general}, I'll help you start."
        ),
        "learn": (
            "Hey! Here you can learn AI for free — on real tools, not in "
            "theory. Two steps: 1) head to {ch_learn} (Q-Lab); "
            "2) do the first task — I'll guide you from there."
        ),
        "watch": (
            "Hey! Look around, no strings attached. If you like — try AI for "
            "free in {ch_learn}, check {ch_wins} to see what others make. "
            "If something clicks — ask in {ch_questions}, I'll help."
        ),
    },
}

# Дефолтные плейсхолдеры каналов (если гильдия/канал не найдены — просто текст).
_CH_DEFAULTS = {
    "ch_earn": "#заработок",
    "ch_general": "#общее",
    "ch_learn": "#обучение",
    "ch_wins": "#результаты",
    "ch_questions": "#вопросы",
}


def value_dm(goal: str, lang: str = DEFAULT_LANG,
             product_url: str = "", channels: dict | None = None) -> str:
    """channels: плейсхолдер → упоминание канала ("<#id>"); без него — "#имя"."""
    lang = lang if lang in LANGS else DEFAULT_LANG
    template = _VALUE_DM[lang][goal]
    fields = dict(_CH_DEFAULTS)
    fields.update(channels or {})
    fields["product"] = product_url if product_url else PRODUCT_FALLBACK[lang]
    return template.format(**fields)


# Ярлыки целей (для логов/статистики) — на дефолтном языке.
GOAL_LABEL = {
    "earn": "Заработать на рекомендациях 💰",
    "company": "Развернуть на компанию/сеть 🏢",
    "business": "Автоматизировать бизнес 🚀",
    "learn": "Научиться AI 🧠",
    "watch": "Осмотреться 👀",
}


# ── 💰: запрос Quanta ID → заявка в #заявки (спека §8, Phase 1) ───────────────
QID_REQUEST_DM = {
    "ru": (
        "Чтобы открыть тебе {ch_earn}, пришли ответом на это сообщение свой "
        "Quanta ID — логин или почту из кабинета. Я передам заявку команде, "
        "она проверит, что партнёрка активна."
    ),
    "uk": (
        "Щоб відкрити тобі {ch_earn}, надішли у відповідь на це повідомлення "
        "свій Quanta ID — логін або пошту з кабінету. Я передам заявку команді, "
        "вона перевірить, що партнерка активна."
    ),
    "en": (
        "To open {ch_earn} for you, reply to this message with your Quanta ID — "
        "the login or email from your dashboard. I'll pass the request to the "
        "team; they'll check that your partner link is active."
    ),
}

QID_INVALID_DM = {
    "ru": (
        "Хм, это не похоже на Quanta ID 🙂 Пришли одной строкой логин или почту "
        "из кабинета — без пробелов. Если пока не актуально — просто "
        "проигнорируй это сообщение."
    ),
    "uk": (
        "Хм, це не схоже на Quanta ID 🙂 Надішли одним рядком логін або пошту "
        "з кабінету — без пробілів. Якщо поки не актуально — просто "
        "проігноруй це повідомлення."
    ),
    "en": (
        "Hmm, that doesn't look like a Quanta ID 🙂 Send the login or email "
        "from your dashboard in one line, no spaces. If it's not relevant "
        "right now — just ignore this message."
    ),
}

QID_RECEIVED_DM = {
    "ru": (
        "Принял, заявка ушла команде ✅ Как только проверят — тебе выдадут роль, "
        "и {ch_earn} откроется. Обычно это не дольше рабочего дня."
    ),
    "uk": (
        "Прийняв, заявка пішла команді ✅ Щойно перевірять — тобі видадуть роль, "
        "і {ch_earn} відкриється. Зазвичай це не довше робочого дня."
    ),
    "en": (
        "Got it, the request went to the team ✅ Once they check it, you'll get "
        "the role and {ch_earn} opens up. Usually takes less than a working day."
    ),
}

# Пост в служебный #заявки (team-facing, RU).
APPLICATION_POST = (
    "📥 Заявка на {ch_earn}: {mention} (`{name}`, id {user_id}) · "
    "Quanta ID: `{qid}`\n"
    "Проверь в админке, что партнёрка активна → выдай роль @affiliate "
    "(ПКМ по нику → Roles)."
)


# ── Якорные сообщения для #старт (постятся ботом в SETUP_MODE) ────────────────
ANCHOR_RULES = (
    "**Добро пожаловать в Quanta 👋**\n"
    "Здесь делают контент, осваивают AI на практике и растут вместе с "
    "продуктом.\n\n"
    "**Правила простые:**\n"
    "1. Уважение к людям — без оскорблений и токсичности.\n"
    "2. Без спама и рекламы сторонних проектов.\n"
    "3. Без обещаний дохода и финансовых гарантий.\n"
    "4. Вопросы по продукту — в #вопросы; личное по аккаунту/платежу — через "
    "поддержку (#поддержка).\n\n"
    "Согласен(на) — поставь ✅ под этим сообщением. Это первый из двух шагов."
)

ANCHOR_LANG = (
    "**Выбери язык / Обери мову / Pick your language**\n"
    "На нём я буду писать тебе в личку.\n\n"
    "🇷🇺 — русский · 🇺🇦 — українська · 🇬🇧 — English"
)

ANCHOR_GOALS = (
    "**Шаг второй: с чем ты пришёл? Выбери цель — можно несколько.**\n\n"
    "💰 — заработать на рекомендациях\n"
    "🏢 — развернуть Quanta на свою компанию/сеть\n"
    "🚀 — автоматизировать свой бизнес\n"
    "🧠 — научиться AI на практике\n"
    "👀 — осмотреться\n\n"
    "Жми реакцию под этим сообщением — я открою тебе каналы и напишу в личку, "
    "с чего начать."
)


# ── FAQ × 3 языка (§B, выверено по Module 12) ─────────────────────────────────
# Структура: FAQ_TOPICS[lang] = { key: {aliases, title, answer} }.
# aliases — на соответствующем языке (матч по подстроке запроса).
FAQ_TOPICS = {
    "ru": {
        "buy_license": {
            "aliases": ["купить", "лицензи", "как купить", "покупк", "оформит", "оплат"],
            "title": "Как купить лицензию",
            "answer": (
                "Регистрируешься → выбираешь лицензию в кабинете → оплачиваешь счёт "
                "в крипте. Лицензия активируется после подтверждения платежа в сети. "
                "Если пришёл по чьей-то ссылке — просто зарегистрируйся по ней, "
                "остальное в кабинете."
            ),
        },
        "license_period": {
            "aliases": ["срок", "на месяц", "больше чем", "период", "30", "90", "360"],
            "title": "Срок лицензии",
            "answer": "Да — есть лицензии на 30, 90 и 360 дней. Срок выбираешь при создании счёта.",
        },
        "currency_network": {
            "aliases": ["валют", "сет", "usdc", "bsc", "bep20", "чем платить"],
            "title": "Валюта и сеть оплаты",
            "answer": (
                "Цена в долларах, валюту выбираешь на чекауте из списка — USDC в сети "
                "BEP20 (BSC) один из вариантов. Выбирай ровно ту сеть, которую чекаут "
                "показывает для выбранной валюты — платёж по другой сети не дойдёт."
            ),
        },
        "payment_failed": {
            "aliases": ["не работает оплат", "комисси", "не дала оплат", "ошибка оплат"],
            "title": "Не проходит оплата",
            "answer": (
                "Давай пройдём оплату вместе по шагам, это 5-7 минут. Скину "
                "видео-инструкцию под твой телефон. Если уже частично оплатил — не плати "
                "второй раз, пришли хеш транзакции, сопоставим."
            ),
        },
        "paid_inactive": {
            "aliases": ["оплатил", "неактивн", "не активир", "заплатил а"],
            "title": "Оплатил, а лицензия неактивна",
            "answer": (
                "Не плати второй раз. Напиши в канал поддержки и приложи хеш "
                "транзакции — платёж сопоставят с твоим аккаунтом."
            ),
        },
        "pay_from_balance": {
            "aliases": ["с баланса", "балансом", "оплатить балан", "баланс"],
            "title": "Оплата с баланса",
            "answer": (
                "Да. Если комиссий на балансе хватает — оплачиваешь лицензию прямо "
                "с баланса, без внешнего платежа. Понадобится двухфакторная "
                "аутентификация."
            ),
        },
        "link_needs_license": {
            "aliases": ["нужна лицензи", "делиться ссылк", "ссылка без лицензи"],
            "title": "Нужна ли лицензия, чтобы делиться ссылкой",
            "answer": (
                "Нет. Ссылка работает без лицензии — люди регистрируются по ней "
                "в любой момент. Лицензия нужна, чтобы получать выплаты, а не для самой "
                "ссылки."
            ),
        },
        "withdraw_inactive": {
            "aliases": ["вывести при неактив", "вывод неактивн", "выплат неактивн"],
            "title": "Вывод при неактивной лицензии",
            "answer": (
                "Нет, для выплат нужна активная лицензия. Ссылка продолжает работать; "
                "активируешь лицензию — получаешь выплаты."
            ),
        },
        "withdraw_limits": {
            "aliases": ["минималк", "минимум", "частота вывод", "вывод", "выплат"],
            "title": "Минималка и частота вывода",
            "answer": (
                "Минимум вывода — $10. Заявку можно подать в любой момент, ограничений "
                "по частоте нет. Скорость зачисления зависит от платёжного провайдера. "
                "Выплаты приходят в USDC по BEP20."
            ),
        },
        "two_links": {
            "aliases": ["двум ссылк", "две ссылк", "чья продаж", "по двум"],
            "title": "Зашёл по двум разным ссылкам — чья продажа",
            "answer": (
                "Первого. Привязка фиксируется за первой ссылкой, по которой человек "
                "зарегистрировался; поздние её не меняют."
            ),
        },
        "credits_expire": {
            "aliases": ["сгораю", "кредит", "истека", "12 месяц"],
            "title": "Когда сгорают кредиты",
            "answer": (
                "Кредиты действуют 12 месяцев с момента зачисления — и обычные "
                "пополнения, и кредиты с лицензией."
            ),
        },
        "refund": {
            "aliases": ["вернуть деньг", "возврат", "рефанд"],
            "title": "Возврат денег",
            "answer": (
                "Нет. Оплата распределяется по экосистеме с первого дня, поэтому "
                "завершённый платёж не отменяется. Поэтому лицензия и сделана помесячной "
                "предоплатой — на кону всегда только текущий период, решаешь каждый "
                "месяц заново."
            ),
        },
        "stop_paying": {
            "aliases": ["перестану плат", "останется ли", "если не плат", "удал"],
            "title": "Останется ли моё, если перестану платить",
            "answer": (
                "Да. Аккаунт не удаляется, всё созданное остаётся. Активируешь снова — "
                "продолжаешь с того места."
            ),
        },
        "vioxen_issues": {
            "aliases": ["vioxen", "виоксен", "долго генер", "зависа", "генерац"],
            "title": "Vioxen долго генерит / ошибки",
            "answer": (
                "Знаю, по видео бывали сбои и долгая генерация — команда чинит. Если "
                "у тебя ошибка — пришли скрин в канал поддержки, разберём конкретно, "
                "кредиты за сбой вернём."
            ),
        },
        "where_to_write": {
            "aliases": ["куда писать", "куда обратит", "где спросит", "куда задать"],
            "title": "Куда писать",
            "answer": (
                "Вопрос по продукту/оплате — пиши в #вопросы, там отвечаем и ответ "
                "виден всем. Личные вещи по аккаунту/платежу — в канал поддержки "
                "с хешем транзакции. Так быстрее и не теряется."
            ),
        },
    },
    "uk": {
        "buy_license": {
            "aliases": ["купити", "ліцензі", "як купити", "покупк", "оформ", "оплат"],
            "title": "Як купити ліцензію",
            "answer": (
                "Реєструєшся → обираєш ліцензію в кабінеті → оплачуєш рахунок у крипті. "
                "Ліцензія активується після підтвердження платежу в мережі. Якщо прийшов "
                "за чиїмось посиланням — просто зареєструйся за ним, решта в кабінеті."
            ),
        },
        "license_period": {
            "aliases": ["термін", "на місяць", "більше ніж", "період", "30", "90", "360"],
            "title": "Термін ліцензії",
            "answer": "Так — є ліцензії на 30, 90 і 360 днів. Термін обираєш при створенні рахунку.",
        },
        "currency_network": {
            "aliases": ["валют", "мереж", "usdc", "bsc", "bep20", "чим платити"],
            "title": "Валюта і мережа оплати",
            "answer": (
                "Ціна в доларах, валюту обираєш на чекауті зі списку — USDC у мережі "
                "BEP20 (BSC) один із варіантів. Обирай саме ту мережу, яку чекаут "
                "показує для обраної валюти — платіж іншою мережею не дійде."
            ),
        },
        "payment_failed": {
            "aliases": ["не працює оплат", "комісі", "не дала оплат", "помилка оплат"],
            "title": "Не проходить оплата",
            "answer": (
                "Давай пройдемо оплату разом по кроках, це 5-7 хвилин. Скину "
                "відео-інструкцію під твій телефон. Якщо вже частково оплатив — не плати "
                "вдруге, надішли хеш транзакції, зіставимо."
            ),
        },
        "paid_inactive": {
            "aliases": ["оплатив", "неактивн", "не актив", "заплатив а"],
            "title": "Оплатив, а ліцензія неактивна",
            "answer": (
                "Не плати вдруге. Напиши в канал підтримки та додай хеш транзакції — "
                "платіж зіставлять з твоїм акаунтом."
            ),
        },
        "pay_from_balance": {
            "aliases": ["з балансу", "балансом", "оплатити балан", "баланс"],
            "title": "Оплата з балансу",
            "answer": (
                "Так. Якщо комісій на балансі вистачає — оплачуєш ліцензію прямо "
                "з балансу, без зовнішнього платежу. Знадобиться двофакторна "
                "автентифікація."
            ),
        },
        "link_needs_license": {
            "aliases": ["потрібна ліцензі", "ділитися посилан", "посилання без ліцензі"],
            "title": "Чи потрібна ліцензія, щоб ділитися посиланням",
            "answer": (
                "Ні. Посилання працює без ліцензії — люди реєструються за ним "
                "будь-коли. Ліцензія потрібна, щоб отримувати виплати, а не для самого "
                "посилання."
            ),
        },
        "withdraw_inactive": {
            "aliases": ["вивести при неактив", "вивід неактивн", "виплат неактивн"],
            "title": "Вивід при неактивній ліцензії",
            "answer": (
                "Ні, для виплат потрібна активна ліцензія. Посилання продовжує "
                "працювати; активуєш ліцензію — отримуєш виплати."
            ),
        },
        "withdraw_limits": {
            "aliases": ["мінімалк", "мінімум", "частота вивод", "вивід", "виплат"],
            "title": "Мінімалка і частота виводу",
            "answer": (
                "Мінімум виводу — $10. Заявку можна подати будь-коли, обмежень "
                "за частотою немає. Швидкість зарахування залежить від платіжного "
                "провайдера. Виплати приходять у USDC по BEP20."
            ),
        },
        "two_links": {
            "aliases": ["двома посилан", "два посилан", "чий продаж", "за двома"],
            "title": "Зайшов за двома різними посиланнями — чий продаж",
            "answer": (
                "Першого. Прив'язка фіксується за першим посиланням, за яким людина "
                "зареєструвалася; пізніші її не змінюють."
            ),
        },
        "credits_expire": {
            "aliases": ["згораю", "кредит", "спливаю", "12 місяц"],
            "title": "Коли згорають кредити",
            "answer": (
                "Кредити діють 12 місяців з моменту зарахування — і звичайні "
                "поповнення, і кредити з ліцензією."
            ),
        },
        "refund": {
            "aliases": ["повернути гро", "повернення", "рефанд"],
            "title": "Повернення грошей",
            "answer": (
                "Ні. Оплата розподіляється по екосистемі з першого дня, тому "
                "завершений платіж не скасовується. Тому ліцензія й зроблена помісячною "
                "передоплатою — на кону завжди лише поточний період, вирішуєш щомісяця "
                "наново."
            ),
        },
        "stop_paying": {
            "aliases": ["перестану плат", "чи залишиться", "якщо не плат", "видал"],
            "title": "Чи залишиться моє, якщо перестану платити",
            "answer": (
                "Так. Акаунт не видаляється, все створене лишається. Активуєш знову — "
                "продовжуєш з того місця."
            ),
        },
        "vioxen_issues": {
            "aliases": ["vioxen", "віоксен", "довго генер", "зависа", "генерац"],
            "title": "Vioxen довго генерує / помилки",
            "answer": (
                "Знаю, по відео бували збої та довга генерація — команда лагодить. Якщо "
                "в тебе помилка — надішли скрін у канал підтримки, розберемо конкретно, "
                "кредити за збій повернемо."
            ),
        },
        "where_to_write": {
            "aliases": ["куди писати", "куди звернут", "де запитати", "куди поставити"],
            "title": "Куди писати",
            "answer": (
                "Питання щодо продукту/оплати — пиши в #вопросы, там відповідаємо "
                "і відповідь бачать усі. Особисте щодо акаунта/платежу — в канал "
                "підтримки з хешем транзакції. Так швидше і не губиться."
            ),
        },
    },
    "en": {
        "buy_license": {
            "aliases": ["buy", "license", "how to buy", "purchase", "get a license", "pay", "payment"],
            "title": "How to buy a license",
            "answer": (
                "Register → pick a license in your dashboard → pay the invoice in "
                "crypto. The license activates once the payment is confirmed on-chain. "
                "If you came through someone's link — just register through it, the rest "
                "is in the dashboard."
            ),
        },
        "license_period": {
            "aliases": ["period", "for a month", "longer than", "term", "30", "90", "360"],
            "title": "License period",
            "answer": "Yes — there are 30-, 90-, and 360-day licenses. You pick the term when creating the invoice.",
        },
        "currency_network": {
            "aliases": ["currency", "network", "usdc", "bsc", "bep20", "what to pay"],
            "title": "Currency and payment network",
            "answer": (
                "Price is in dollars; you pick the currency at checkout from a list — "
                "USDC on BEP20 (BSC) is one option. Use exactly the network checkout "
                "shows for the chosen currency — a payment on another network won't arrive."
            ),
        },
        "payment_failed": {
            "aliases": ["payment doesn't work", "fee", "couldn't pay", "payment error"],
            "title": "Payment won't go through",
            "answer": (
                "Let's do the payment together step by step, it's 5-7 minutes. I'll send "
                "a video guide for your phone. If you've already partially paid — don't "
                "pay again, send the transaction hash and we'll reconcile it."
            ),
        },
        "paid_inactive": {
            "aliases": ["paid", "inactive", "not activated", "paid but"],
            "title": "Paid, but the license is inactive",
            "answer": (
                "Don't pay again. Write to the support channel and attach the "
                "transaction hash — the payment will be matched to your account."
            ),
        },
        "pay_from_balance": {
            "aliases": ["from balance", "with balance", "pay from balance", "balance"],
            "title": "Paying from balance",
            "answer": (
                "Yes. If your balance has enough — you pay for the license straight "
                "from the balance, no external payment. Two-factor authentication is "
                "required."
            ),
        },
        "link_needs_license": {
            "aliases": ["need a license", "share the link", "link without a license"],
            "title": "Do you need a license to share the link",
            "answer": (
                "No. The link works without a license — people can register through it "
                "any time. A license is needed to receive payouts, not for the link itself."
            ),
        },
        "withdraw_inactive": {
            "aliases": ["withdraw with inactive", "payout inactive", "withdraw inactive"],
            "title": "Withdrawing with an inactive license",
            "answer": (
                "No, payouts need an active license. The link keeps working; activate "
                "the license and you get payouts."
            ),
        },
        "withdraw_limits": {
            "aliases": ["minimum", "withdrawal frequency", "withdraw", "payout", "cash out"],
            "title": "Minimum and withdrawal frequency",
            "answer": (
                "Minimum withdrawal is $10. You can request any time, no frequency "
                "limits. Crediting speed depends on the payment provider. Payouts arrive "
                "in USDC on BEP20."
            ),
        },
        "two_links": {
            "aliases": ["two links", "two different links", "whose sale", "by two"],
            "title": "Came through two different links — whose sale",
            "answer": (
                "The first one's. The attribution is locked to the first link the person "
                "registered through; later ones don't change it."
            ),
        },
        "credits_expire": {
            "aliases": ["expire", "credit", "burn", "12 months"],
            "title": "When credits expire",
            "answer": (
                "Credits are valid for 12 months from the moment they're credited — both "
                "regular top-ups and credits that come with a license."
            ),
        },
        "refund": {
            "aliases": ["refund", "money back", "get money back"],
            "title": "Refunds",
            "answer": (
                "No. Payment is distributed across the ecosystem from day one, so a "
                "completed payment isn't reversed. That's why the license is monthly "
                "prepaid — only the current period is ever at stake, and you decide again "
                "each month."
            ),
        },
        "stop_paying": {
            "aliases": ["stop paying", "will it stay", "if i don't pay", "delete"],
            "title": "Will my stuff stay if I stop paying",
            "answer": (
                "Yes. The account isn't deleted, everything you've made stays. Activate "
                "again and you continue from where you left off."
            ),
        },
        "vioxen_issues": {
            "aliases": ["vioxen", "slow generation", "freezes", "generation"],
            "title": "Vioxen is slow / errors",
            "answer": (
                "I know, video had outages and slow generation — the team is fixing it. "
                "If you hit an error — send a screenshot to the support channel, we'll "
                "look into it, and credits spent on a failure get refunded."
            ),
        },
        "where_to_write": {
            "aliases": ["where to write", "where to ask", "where do i ask", "where to post"],
            "title": "Where to write",
            "answer": (
                "Product/payment questions — post in #вопросы, we answer there and the "
                "answer is visible to everyone. Personal account/payment matters — the "
                "support channel with the transaction hash. Faster and nothing gets lost."
            ),
        },
    },
}

FAQ_FALLBACK = {
    "ru": ("Не нашёл точную тему. Доступные: {topics}.\n"
           "Например: `!faq оплата`. Если вопрос личный (аккаунт/платёж) — лучше "
           "в #вопросы или в канал поддержки."),
    "uk": ("Не знайшов точну тему. Доступні: {topics}.\n"
           "Наприклад: `!faq оплата`. Якщо питання особисте (акаунт/платіж) — краще "
           "в #вопросы або в канал підтримки."),
    "en": ("Couldn't find an exact topic. Available: {topics}.\n"
           "For example: `!faq payment`. If it's personal (account/payment) — better "
           "in #вопросы or the support channel."),
}

FAQ_LIST_PROMPT = {
    "ru": "Темы FAQ: {topics}\nНапример: `!faq оплата`",
    "uk": "Теми FAQ: {topics}\nНаприклад: `!faq оплата`",
    "en": "FAQ topics: {topics}\nFor example: `!faq payment`",
}
