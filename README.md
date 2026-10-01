# Inno Markaz — PostgreSQL Database AI Agent

Tabiiy tildagi so'rovlarni PostgreSQL ma'lumotlar bazasiga xavfsiz yo'naltiruvchi va tahliliy javoblar qaytaruvchi sun'iy intellekt agenti. Tizim deterministik **MCP (Model Context Protocol)** arxitekturasi orqali LLM'ning bazaga to'g'ridan-to'g'ri kirishini cheklaydi, SQL inyeksiyalari va nozik shaxsiy ma'lumotlar sizib chiqishining oldini oladi.

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

Coverage (qamrov) hisoboti bilan ishga tushirish:
```powershell
python -m pytest --cov=app --cov-report=term-missing
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
│   ├── llm/                   # Ollama va OpenRouter provayderlari va factory
│   ├── mcp/                   # Deterministik xavfsizlik va ijro quvuri
│   │   ├── executor.py        # Pipeline boshqaruvchisi
│   │   ├── input_validator.py # So'rovni tekshirish
│   │   ├── schema_resolver.py # Tabiiy til atamalarini sxemaga moslash
│   │   ├── authorization.py   # Foydalanuvchi roli ruxsatlari
│   │   ├── sql_generator.py   # Parametrlangan SQL yaratish
│   │   ├── sql_ast_validator.py # sqlglot orqali SQL AST tekshiruvi
│   │   ├── sensitivity_policy.py# Maosh va shaxsiy ma'lumotlar siyosati
│   │   ├── complexity_checker.py# So'rov murakkabligini nazorat qilish
│   │   ├── parameterizer.py   # Parametrlarni xavfsiz bog'lash
│   │   └── result_sanitizer.py# Natijalarni tozalash
│   ├── db/                    # asyncpg ulanish havzasi va PostgreSQL sxemasi
│   └── prompts/               # Query planning, SQL va javob sintezi promptlari
├── static/                    # HTML, CSS va JS dan iborat frontend interfeysi
└── tests/                     # Unit va integratsion testlar to'plami
```
