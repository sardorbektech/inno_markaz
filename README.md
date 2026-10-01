# Inno Markaz — PostgreSQL Database AI Agent

Tabiiy tildagi so'rovlarni PostgreSQL ma'lumotlar bazasiga xavfsiz yo'naltiruvchi va tahliliy javoblar qaytaruvchi sun'iy intellekt agenti. Tizim deterministik **MCP (Model Context Protocol)** arxitekturasi orqali LLM'ning bazaga to'g'ridan-to'g'ri kirishini cheklaydi, SQL inyeksiyalari va nojo'ya o'zgarishlarning oldini oladi.

---

## Asosiy Imkoniyatlar va Xususiyatlar

1. **Suhbat Xotirasi (Memory):** Har bir sessiya uchun oxirgi 10 ta xabar (savol-javob) saqlanadi, bu esa zanjirli so'rovlar ("Uning maoshi qancha?", "Bo'lim boshlig'i kim?") bilan ishlash imkonini beradi.
2. **Chiroyli Markdown Chiqishi:** Natijalar aniq, chiroyli Markdown jadvallari (`| Bo'lim | Xodimlar |`), sarlavhalar va qalin matnlar bilan taqdim etiladi.
3. **To'liq O'qish Erkinligi (Full Read-Only Access):** Foydalanuvchi (`viewer`) bazadagi istalgan biznes ma'lumotlarini — individual maoshlar, telefon raqamlari, elektron pochta, kontaktlar va ta'lim ma'lumotlarini to'siqsiz ko'ra oladi.
4. **Qat'iy O'zgarmaslik (Zero-Write Guarantee):** Bazaga yangi ma'lumot kiritish, o'chirish yoki o'zgartirish qat'iyan taqiqlanadi (Input validation, SQL AST tekshiruvi va PostgreSQL `inno_readonly` foydalanuvchisi / read-only tranzaksiya darajasida jismonan bloklanadi).
5. **Jarayon Tafsilotlari va Vaqt:** Har bir xavfsizlik va ijro bosqichining sarflagan vaqti soniyalarda (`0.25 s`, `1.20 s`) ko'rsatiladi.
6. **Prompt Injection Himoyasi:** Promptlarda `<USER>` kabi soxta XML teglari ishlatilmaydi. Tizim ko'rsatmalarini buzishga urinishlar (`Ignore instructions`, `DAN mode`, `Jailbreak`, stacked SQL) dastlabki bosqichdayoq bloklanadi.

---

## Talablar

- **Python:** `3.12.x` (masalan, `3.12.7` yoki `3.12.10`)
- **PostgreSQL:** 14+ (jadvallar va namunaviy ma'lumotlar bilan)
- **LLM Provayderi:** OpenRouter API kaliti yoki lokal Ollama xizmati

---

## Muhitni Sozlash

1. **Repozitoriyni oching va virtual muhit yarating:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(Linux/macOS uchun: `source .venv/bin/activate`)*

2. **Bog'liqliklarni o'rnating:**
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. **Muhit o'zgaruvchilarini sozlang:**
   `.env.example` faylidan nusxa olib `.env` faylini yarating va PostgreSQL hamda LLM kalitlarini kiriting:
   ```powershell
   Copy-Item .env.example .env
   ```
   `.env` faylida:
   - `DATABASE_URL`: PostgreSQL ulanish manzili (masalan: `postgresql://inno_readonly:password@localhost:5432/inno_markaz`)
   - `LLM_PROVIDER`: `openrouter` yoki `ollama`
   - `OPENROUTER_API_KEY`: OpenRouter kaliti (agar OpenRouter tanlansa)
   - `OLLAMA_BASE_URL`: Ollama manzili (masalan: `http://localhost:11434`)

---

## Ishga Tushirish

FastAPI serverini ishga tushirish:
```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Brauzerda oching:
- **Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Hujjatlari:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Testlash

Barcha testlarni ishga tushirish:
```powershell
python -m pytest -q
```

Xavfsizlik, Prompt Injection POC va Xotira testlarini ishga tushirish:
```powershell
python -m pytest tests/test_security.py tests/test_memory.py -v
```

---

## Loyiha Tuzilmasi

```text
Inno Markaz/
├── AGENTS.md                  # Loyihaning to'liq texnik spetsifikatsiyasi
├── ABOUT.md                   # AI va dasturchilar uchun Master Prompt spetsifikatsiyasi
├── README.md                  # Foydalanish va o'rnatish qo'llanmasi
├── .env.example               # Muhit o'zgaruvchilari namunasi
├── pyproject.toml             # Loyiha konfiguratsiyasi va bog'liqliklar
├── requirements.txt           # Python paketlari ro'yxati
├── .agents/
│   └── rules/
│       └── project.md         # Loyihaga xos agent qoidalari
├── app/
│   ├── main.py                # FastAPI ilovasi kirish nuqtasi va static routing
│   ├── logging_config.py      # Terminal bosqichlarini rangli loglash
│   ├── config/                # Sozlamalar (settings, db, llm, security)
│   ├── api/                   # REST API marshrutlari va Pydantic sxemalari
│   ├── llm/                   # Ollama va OpenRouter provayderlari, memory va service
│   │   ├── memory.py          # Oxirgi 10 ta xabar saqlanuvchi suhbat xotirasi
│   ├── mcp/                   # Deterministik xavfsizlik va ijro quvuri
│   │   ├── executor.py        # Pipeline boshqaruvchisi va bosqichlar vaqti
│   │   ├── input_validator.py # Prompt injection va DDL/DML larni bloklash
│   │   ├── schema_resolver.py # Tabiiy til atamalarini sxemaga moslash
│   │   ├── authorization.py   # Viewer roli ruxsatlari
│   │   ├── sql_generator.py   # Parametrlangan SQL yaratish
│   │   ├── sql_ast_validator.py # sqlglot orqali SQL AST tekshiruvi
│   │   ├── sensitivity_policy.py# Ruxsat etilgan biznes o'qish tekshiruvi
│   │   ├── complexity_checker.py# So'rov murakkabligini nazorat qilish
│   │   ├── parameterizer.py   # Parametrlarni xavfsiz bog'lash
│   │   └── result_sanitizer.py# Natijalarni tozalash va formatlash
│   ├── db/                    # asyncpg ulanish havzasi va PostgreSQL sxemasi
│   └── prompts/               # Query planning, SQL va chiroyli javob sintezi promptlari
├── static/                    # HTML, CSS va JS dan iborat frontend interfeysi
└── tests/                     # Unit, integratsion, POC prompt injection va memory testlari
```
