# Inno Markaz — Loyiha Qoidalari (`.agents/rules/project.md`)

Ushbu qoidalar Inno Markaz loyihasi uchun xos me'yorlar va cheklovlarni belgilaydi.

---

## 1. Stek va Muhit
- **Til:** Python 3.12.x (masalan: 3.12.7, 3.12.10).
- **Backend:** FastAPI, Uvicorn, Pydantic v2, pydantic-settings.
- **Ma'lumotlar bazasi:** PostgreSQL, asyncpg drayveri (faqat `inno_readonly` foydalanuvchisi, read-only tranzaksiyalar, statement_timeout bilan).
- **SQL AST tahlili:** sqlglot (PostgreSQL dialekti).
- **LLM integratsiyasi:** Ollama va OpenRouter umumiy `LLMProvider` abstraksiyasi ortida.
- **Frontend:** Statik HTML, CSS, JavaScript (FastAPI `StaticFiles` orqali `/static` va `/`).
- **Test:** pytest, pytest-asyncio (`asyncio_mode = "auto"`).

---

## 2. Ishga Tushirish va Test Buyruqlari
- **Virtual muhit:** `.venv\Scripts\Activate.ps1` (Windows) / `source .venv/bin/activate` (Linux).
- **Bog'liqliklarni o'rnatish:** `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
- **Serverni ishga tushirish:** `.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
- **Testlarni ishga tushirish:** `.venv\Scripts\python.exe -m pytest -q`.
- **Xavfsizlik va POC testlarini ishga tushirish:** `.venv\Scripts\python.exe -m pytest tests/test_security.py tests/test_memory.py -q`.

---

## 3. Arxitektura, Xavfsizlik va Funksional Qoidalar
1. **Yagona Rol ("viewer"):**
   - Tizimda faqat bitta rol amal qiladi: `viewer`.
   - `viewer` barcha biznes ma'lumotlarini (shu jumladan individual maoshlar, telefon, elektron pochta, kontaktlar va ta'lim ma'lumotlarini) to'liq o'qish (SELECT) huquqiga ega.
2. **Qat'iy Read-Only Invarianti:**
   - Foydalanuvchi ma'lumotlar bazasiga yangi ma'lumot kirita olmaydi, o'chira olmaydi va o'zgartira olmaydi.
   - Har qanday `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE` so'rovlari:
     - Input Validator darajasida rad etiladi;
     - SQL AST Validator darajasida rad etiladi;
     - PostgreSQL darajasida `inno_readonly` foydalanuvchisi va `readonly=True` tranzaksiyasi orqali jismonan bloklanadi.
3. **LLM Xotirasi (Memory - Oxirgi 10 ta xabar):**
   - Har bir mijoz sessiyasi (`session_id`) bo'yicha oxirgi 10 ta xabar (foydalanuvchi savoli va assistent javobi) xotirada saqlanadi.
   - LLM suhbat kontekstini inobatga olgan holda navbatdagi so'rovlarni tahlil qiladi va javob qaytaradi.
4. **Chiroyli Markdown Chiqishi:**
   - LLM javoblari aniq, chiroyli Markdown formatida chiqishi shart (qalin matnlar `**`, jadvallar `| Ustun | Ustun |`, sarlavhalar `### `).
   - Frontend javoblarni to'g'ri HTML ko'rinishida chiroyli render qiladi.
5. **Prompt Injection va Tag Injection Himoyasi:**
   - Promptlarda `<USER>`, `<USER_QUESTION>`, `<SCHEMA>`, `<SYSTEM>` kabi soxta XML teglari QAT'IYAN ISHLATILMAYDI.
   - Buning o'rniga xavfsiz Markdown sarlavhalari (`### Input Question:`, `### Read-Only Schema:`) va LLM tizimli chat rollari (`system`, `user`) qo'llaniladi.
   - Input Validator har qanday prompt injection, jailbreak (`DAN mode`), ko'rsatmalarni e'tiborsiz qoldirish (`Ignore previous instructions`) va stacked SQL urinishlarini aniqlab, so'rovni to'xtatadi.
6. **Jarayon Tafsilotlarida Vaqt Ko'rsatkichlari:**
   - MCP quvuridagi har bir bosqichning sarflangan vaqti soniyalarda (`0.25 s`, `1.20 s`) o'lchanadi va UI inspectorida nishon sifatida ko'rsatiladi.

---

## 4. Skills va Plaginlar
- `antigravity-guide`: Antigravity vositalari va ko'rsatmalari uchun.
- `chrome-devtools`: Frontend va a11y tekshiruvlari uchun.
