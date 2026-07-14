from __future__ import annotations

import pytest

from nexus_u.server.http import NexusHandler, _bounded_query


def _handler(authorization: str | None = None) -> NexusHandler:
    handler = object.__new__(NexusHandler)
    handler.headers = {} if authorization is None else {"Authorization": authorization}
    return handler


def test_health_routes_are_public_but_metrics_are_not(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_U_API_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_U_ALLOW_UNAUTHENTICATED", raising=False)
    handler = _handler()
    assert handler._authorized("/health") is True
    assert handler._authorized("/health/ready") is True
    assert handler._authorized("/metrics") is False
    assert handler._authorized("/v1/artifacts") is False


def test_bearer_token_authorization(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_U_API_TOKEN", "correct-secret-💡")
    assert _handler("Bearer correct-secret-💡")._authorized("/v1/artifacts") is True
    assert _handler("Bearer wrong-secret")._authorized("/v1/artifacts") is False
    assert _handler()._authorized("/v1/artifacts") is False


def test_unauthenticated_mode_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_U_API_TOKEN", raising=False)
    monkeypatch.setenv("NEXUS_U_ALLOW_UNAUTHENTICATED", "true")
    assert _handler()._authorized("/v1/artifacts") is True


def test_query_limit_is_validated_and_capped() -> None:
    assert _bounded_query("limit=12")["limit"] == ["12"]
    assert _bounded_query("limit=99999")["limit"] == ["1000"]


@pytest.mark.parametrize("value", ["", "0", "-1", "not-a-number"])
def test_query_limit_must_be_positive(value: str) -> None:
    with pytest.raises(ValueError):
        _bounded_query(f"limit={value}")
