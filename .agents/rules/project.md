# Inno Markaz — Loyiha Qoidalari (`.agents/rules/project.md`)

Ushbu qoidalar Inno Markaz loyihasi uchun xos me'yorlar va cheklovlarni belgilaydi.

---

## 1. Stek va Muhit
- **Til:** Python 3.12.x (masalan: 3.12.7, 3.12.10).
- **Backend:** FastAPI, Uvicorn, Pydantic v2, pydantic-settings.
- **Ma'lumotlar bazasi:** PostgreSQL, asyncpg drayveri (faqat read-only tranzaksiyalar, statement_timeout bilan).
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
- **Lint tekshiruvi:** `.venv\Scripts\python.exe -m ruff check app tests`.

---

## 3. Arxitektura va Xavfsizlik Qoidalari
1. **LLM cheklovi:** LLM hech qachon to'g'ridan-to'g'ri PostgreSQL bazasiga ulanmaydi va so'rov yubormaydi. LLM faqat savol semantikasini tushunib, structured JSON reja (Query Plan) tuzadi yoki tozalangan natijalar asosida javob yozadi.
2. **MCP quvuri majburiyligi:** Har bir savol quyidagi bosqichlardan ketma-ket o'tadi:
   - `INPUT_VALIDATION` -> `QUERY_PLAN` -> `SCHEMA_RESOLUTION` -> `AUTHORIZATION` -> `SQL_GENERATION` -> `SQL_AST_VALIDATION` -> `SENSITIVITY_POLICY` -> `COMPLEXITY_CHECK` -> `PARAMETERIZATION` -> `POSTGRESQL` -> `RESULT_SANITIZER` -> `LLM_ANSWER`.
3. **Faqat Read-Only SQL:** Barcha so'rovlar faqat `SELECT` operatoridan iborat bo'lishi shart. Har qanday DDL/DML (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`) qat'iyan taqiqlanadi.
4. **SELECT * taqiqi:** `SELECT *` ishlatish taqiqlangan (`COUNT(*)` bundan mustasno). Faqat ruxsat etilgan jadvallar va ustunlar ko'rsatilishi shart.
5. **Nozik Ma'lumotlar Siyosati (Sensitivity Policy):**
   - Individual xodim maoshi (`salary`) ko'rsatilmaydi. Faqat agregat statistika (`AVG`, `MIN`, `MAX`, `COUNT`) ruxsat etiladi.
   - Shaxsiy aloqa ma'lumotlari (`employee_contacts.contact_value`, `phone`, `personal_email`, `telegram`) ommaviy javobda ko'rsatilmaydi.
6. **Sana parametrlari:** PostgreSQL `date` ustunlari bilan ishlashda (`hire_date`), parametrlarga Python `datetime.date` obyektlari berilishi shart (asyncpg matn formatidagi sanani qabul qilmaydi).

---

## 4. Skills va Plaginlar
- `antigravity-guide`: Antigravity vositalari va ko'rsatmalari uchun.
- `chrome-devtools`: Frontend va a11y tekshiruvlari uchun.
