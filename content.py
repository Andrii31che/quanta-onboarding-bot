"""
Тексты онбординг-бота Quanta. Customer-facing. Языки: RU / UK / EN.

Источник RU (НЕ переписывать формулировки — прошли forbidden-scan #606):
- авто-DM:       discord-onboarding-bot-spec-2026-06-16.md §3.3
- 5 value-DM:    sales-lead-valuedm-faq-2026-06-16.md §A
- FAQ:           sales-lead-valuedm-faq-2026-06-16.md §B (выверено по Module 12)
- REMINDER_DM:   bot-authored (нет в источниках); проверен на #606 вручную.

UK/EN — переводы RU-оригинала (GROWTH-5/10 AC: RU+UK+EN). Сохранены факты
(минимум вывода $10, кредиты 12 мес, USDC/BEP20, помесячная лицензия, возврата
нет) и запреты #606 на каждом языке: без «пирамида/пассивный доход/реферал/
заработок/гарантированно/успей» (и их UK/EN эквивалентов), без имён
AI-провайдеров, «лицензия/license» не «подписка/subscription».

Язык юзера хранится в state (rec["lang"]); выбирается реакцией-флагом
🇷🇺/🇺🇦/🇬🇧 в #start-here. Пока не выбран — DEFAULT_LANG.
"""

LANGS = ("ru", "uk", "en")
DEFAULT_LANG = "ru"

# ── Шаг [2]: авто-DM при join — триязычный (язык ещё не выбран) ───────────────
AUTO_DM = (
    "🇷🇺 Привет 👋 Рад, что заглянул(а) в Quanta. Чтобы открыть доступ к чатам, "
    "зайди в **#start-here** и сделай пару шагов: выбери язык (флаг), поставь ✅ "
    "под правилами и отметь, чем занимаешься. После этого добро пожаловать внутрь.\n\n"
    "🇺🇦 Привіт 👋 Радий, що завітав(ла) у Quanta. Щоб відкрити доступ до чатів, "
    "зайди в **#start-here** і зроби кілька кроків: обери мову (прапор), постав ✅ "
    "під правилами та познач, чим займаєшся. Після цього ласкаво просимо досередини.\n\n"
    "🇬🇧 Hi 👋 Glad you stopped by Quanta. To unlock the chats, head to "
    "**#start-here** and take a couple of steps: pick your language (flag), tick ✅ "
    "under the rules, and mark what you do. Then welcome inside."
)

# ── Напоминание через 24ч (1 раз), по языку ──────────────────────────────────
REMINDER_DM = {
    "ru": (
        "Напоминаю про вход в Quanta 🙂 Остались два коротких шага в **#start-here**: "
        "✅ под правилами и выбор, чем ты занимаешься. После них откроются чаты. "
        "Если что-то непонятно — просто ответь на это сообщение."
    ),
    "uk": (
        "Нагадую про вхід у Quanta 🙂 Лишилися два короткі кроки в **#start-here**: "
        "✅ під правилами та вибір, чим ти займаєшся. Після них відкриються чати. "
        "Якщо щось незрозуміло — просто дай відповідь на це повідомлення."
    ),
    "en": (
        "A quick nudge about joining Quanta 🙂 Two short steps left in **#start-here**: "
        "tick ✅ under the rules and pick what you do. The chats open right after. "
        "If anything's unclear, just reply to this message."
    ),
}

# ── Заглушки для незаполненных ссылок (не выдумываем URL) ─────────────────────
DEMO_FALLBACK = {
    "ru": "ссылку на демо скину отдельно — пока загляни в канал, подскажу",
    "uk": "посилання на демо скину окремо — поки що зазирни в канал, підкажу",
    "en": "I'll send the demo link separately — for now hop into the channel, I'll guide you",
}
QLAB_FALLBACK = {
    "ru": "ссылку на Q-Lab скину отдельно — спроси в #questions",
    "uk": "посилання на Q-Lab скину окремо — запитай у #questions",
    "en": "I'll send the Q-Lab link separately — ask in #questions",
}


def _demo(lang: str, demo_url: str) -> str:
    return demo_url if demo_url else DEMO_FALLBACK[lang]


def _qlab(lang: str, qlab_url: str) -> str:
    return qlab_url if qlab_url else QLAB_FALLBACK[lang]


# ── 5 сегментных value-DM × 3 языка ──────────────────────────────────────────
_VALUE_DM = {
    "ru": {
        "creator": (
            "Привет! Рад, что ты с нами 👋 Здесь ты говоришь «сделай пост про X» — "
            "и получаешь готовый материал под каждую соцсеть, в твоём стиле, "
            "а не черновик.\n"
            "Два шага: 1) глянь 2-мин демо → {demo}; "
            "2) загляни в #wins, покажу, с чего начать."
        ),
        "expert": (
            "Привет! Тебе больше не нужно быть себе копирайтером и маркетологом — "
            "инструмент готовит контент и тексты под продажу, а ты возвращаешься "
            "к своему делу.\n"
            "Два шага: 1) демо под твою задачу → {demo}; "
            "2) бесплатное обучение в Q-Lab → {qlab}."
        ),
        "entrepreneur": (
            "Привет! Вместо десятка отдельных подписок — одна система: контент, "
            "видео, тексты в одном месте, по одной лицензии. Включаешь сегодня.\n"
            "Два шага: 1) посмотри, что она убирает из твоего «зоопарка» → {demo}; "
            "2) вопросы — в #general, отвечу."
        ),
        "blogger": (
            "Привет! Здесь ты наконец монетизируешь аудиторию: контент под все "
            "площадки за минуты + выплаты в крипте, без блокировок по региону.\n"
            "Два шага: 1) глянь, как это выглядит → {demo}; "
            "2) забери свою ссылку и загляни в #affiliate."
        ),
        "watcher": (
            "Привет! Здесь можно осмотреться без обязательств. Хочешь — бесплатно "
            "поучись работать с AI в Q-Lab, на реальных инструментах.\n"
            "Два шага: 1) Q-Lab → {qlab}; "
            "2) если что-то зацепит — спроси в #questions, подскажу."
        ),
    },
    "uk": {
        "creator": (
            "Привіт! Радий, що ти з нами 👋 Тут ти кажеш «зроби пост про X» — "
            "і отримуєш готовий матеріал під кожну соцмережу, у твоєму стилі, "
            "а не чернетку.\n"
            "Два кроки: 1) глянь 2-хв демо → {demo}; "
            "2) зазирни в #wins, покажу, з чого почати."
        ),
        "expert": (
            "Привіт! Тобі більше не треба бути сам собі копірайтером і маркетологом — "
            "інструмент готує контент і тексти під продаж, а ти повертаєшся "
            "до своєї справи.\n"
            "Два кроки: 1) демо під твоє завдання → {demo}; "
            "2) безкоштовне навчання в Q-Lab → {qlab}."
        ),
        "entrepreneur": (
            "Привіт! Замість десятка окремих підписок — одна система: контент, "
            "відео, тексти в одному місці, за однією ліцензією. Вмикаєш сьогодні.\n"
            "Два кроки: 1) подивись, що вона прибирає з твого «зоопарку» → {demo}; "
            "2) питання — у #general, відповім."
        ),
        "blogger": (
            "Привіт! Тут ти нарешті монетизуєш аудиторію: контент під усі "
            "майданчики за хвилини + виплати в крипті, без блокувань за регіоном.\n"
            "Два кроки: 1) глянь, як це виглядає → {demo}; "
            "2) забери своє посилання і зазирни в #affiliate."
        ),
        "watcher": (
            "Привіт! Тут можна роззирнутися без зобов'язань. Хочеш — безкоштовно "
            "повчись працювати з AI у Q-Lab, на реальних інструментах.\n"
            "Два кроки: 1) Q-Lab → {qlab}; "
            "2) якщо щось зачепить — запитай у #questions, підкажу."
        ),
    },
    "en": {
        "creator": (
            "Hi! Glad you're with us 👋 Here you say \"make a post about X\" — "
            "and get ready-to-publish material for each social network, in your "
            "voice, not a rough draft.\n"
            "Two steps: 1) watch the 2-min demo → {demo}; "
            "2) drop into #wins and I'll show you where to start."
        ),
        "expert": (
            "Hi! You no longer have to be your own copywriter and marketer — "
            "the tool prepares content and sales copy, and you get back "
            "to your actual work.\n"
            "Two steps: 1) a demo for your case → {demo}; "
            "2) free training in Q-Lab → {qlab}."
        ),
        "entrepreneur": (
            "Hi! Instead of a dozen separate subscriptions — one system: content, "
            "video, copy in one place, under a single license. Switch it on today.\n"
            "Two steps: 1) see what it removes from your tool zoo → {demo}; "
            "2) questions go to #general, I'll answer."
        ),
        "blogger": (
            "Hi! Here you finally monetize your audience: content for every "
            "platform in minutes + payouts in crypto, no regional blocks.\n"
            "Two steps: 1) see how it looks → {demo}; "
            "2) grab your link and drop into #affiliate."
        ),
        "watcher": (
            "Hi! You can look around with no commitment. If you like — learn to "
            "work with AI for free in Q-Lab, on real tools.\n"
            "Two steps: 1) Q-Lab → {qlab}; "
            "2) if something clicks — ask in #questions, I'll help."
        ),
    },
}


def value_dm(segment: str, lang: str = DEFAULT_LANG,
             demo_url: str = "", qlab_url: str = "") -> str:
    lang = lang if lang in LANGS else DEFAULT_LANG
    template = _VALUE_DM[lang][segment]
    return template.format(demo=_demo(lang, demo_url), qlab=_qlab(lang, qlab_url))


# Ярлыки сегментов (для логов/статистики) — на дефолтном языке.
SEGMENT_LABEL = {
    "creator": "Контент-создатель 🎨",
    "expert": "Эксперт / консультант 💼",
    "entrepreneur": "Предприниматель 🚀",
    "blogger": "Блогер 📱",
    "watcher": "Просто смотрю 👀",
}


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
                "Вопрос по продукту/оплате — пиши в #questions, там отвечаем и ответ "
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
                "Питання щодо продукту/оплати — пиши в #questions, там відповідаємо "
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
                "Product/payment questions — post in #questions, we answer there and the "
                "answer is visible to everyone. Personal account/payment matters — the "
                "support channel with the transaction hash. Faster and nothing gets lost."
            ),
        },
    },
}

FAQ_FALLBACK = {
    "ru": ("Не нашёл точную тему. Доступные: {topics}.\n"
           "Например: `!faq оплата`. Если вопрос личный (аккаунт/платёж) — лучше "
           "в #questions или в канал поддержки."),
    "uk": ("Не знайшов точну тему. Доступні: {topics}.\n"
           "Наприклад: `!faq оплата`. Якщо питання особисте (акаунт/платіж) — краще "
           "в #questions або в канал підтримки."),
    "en": ("Couldn't find an exact topic. Available: {topics}.\n"
           "For example: `!faq payment`. If it's personal (account/payment) — better "
           "in #questions or the support channel."),
}

FAQ_LIST_PROMPT = {
    "ru": "Темы FAQ: {topics}\nНапример: `!faq оплата`",
    "uk": "Теми FAQ: {topics}\nНаприклад: `!faq оплата`",
    "en": "FAQ topics: {topics}\nFor example: `!faq payment`",
}
