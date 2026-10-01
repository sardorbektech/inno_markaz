"""API Endpoint Tests."""

import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "llm_provider" in data


@pytest.mark.asyncio
async def test_config_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] in ("ollama", "openrouter")


@pytest.mark.asyncio
async def test_schema_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "departments" in data
        assert "employees" in data


@pytest.mark.asyncio
async def test_chat_endpoint_valid_query(db_connection):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={"message": "Xodimlar soni nechta?", "user_role": "analyst"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_destructive_query():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={"message": "DROP TABLE employees;", "user_role": "analyst"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "taqiqlangan" in data["answer"].lower() or "bekor qilindi" in data["answer"].lower()
