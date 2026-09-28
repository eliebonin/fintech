import asyncio
import logging
from uuid import UUID, uuid4

from fastapi import FastAPI, Query
from httpx import ASGITransport, AsyncClient

from apps.reference_api.problem_details import configure_problem_details


async def _request(app: FastAPI, path: str, headers: dict[str, str] | None = None):
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        return await client.get(path, headers=headers)


def test_validation_problem_omits_rejected_input():
    app = FastAPI()
    configure_problem_details(app)

    @app.get("/validate")
    def validate(value: int = Query()):
        return {"value": value}

    response = asyncio.run(_request(app, "/validate?value=super-secret-input"))

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "request.validation_failed"
    assert "super-secret-input" not in response.text


def test_unhandled_exception_does_not_disclose_message(caplog):
    app = FastAPI()
    configure_problem_details(app)

    @app.get("/explode")
    def explode():
        raise RuntimeError("sentinel-secret")

    with caplog.at_level(logging.INFO, logger="apps.reference_api"):
        response = asyncio.run(_request(app, "/explode"))

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "internal.error"
    assert "sentinel-secret" not in response.text
    assert "sentinel-secret" not in caplog.text


def test_invalid_request_id_is_replaced():
    app = FastAPI()
    configure_problem_details(app)

    response = asyncio.run(_request(app, "/missing", headers={"X-Request-ID": "not-a-uuid"}))

    assert response.status_code == 404
    assert response.headers["x-request-id"] != "not-a-uuid"
    assert UUID(response.headers["x-request-id"])


def test_valid_request_id_is_reused():
    app = FastAPI()
    configure_problem_details(app)
    request_id = str(uuid4())

    response = asyncio.run(_request(app, "/missing", headers={"X-Request-ID": request_id}))

    assert response.headers["x-request-id"] == request_id
