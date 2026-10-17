"""The synchronous input route accepts complete JSON prompts without retries."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cli_agent_orchestrator.api import main
from cli_agent_orchestrator.api.main import app


@pytest.fixture(autouse=True)
def registry(monkeypatch):
    monkeypatch.setattr(main, "get_plugin_registry", lambda request: None)


@pytest.mark.parametrize(
    "text", ["hello", "Qualification\n" + "λ & ? # source\n" * 10000], ids=["short", "large_utf8"]
)
def test_json_input_delivers_exact_text_once(text):
    with patch(
        "cli_agent_orchestrator.api.main.terminal_service.send_input", return_value=True
    ) as send:
        response = TestClient(app, base_url="http://localhost").post(
            "/terminals/abcd1234/input", json={"message": text}
        )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert send.call_count == 1 and send.call_args.args[:2] == ("abcd1234", text)
    assert response.request.url.query == b""


def test_query_callers_remain_supported():
    with patch(
        "cli_agent_orchestrator.api.main.terminal_service.send_input", return_value=True
    ) as send:
        response = TestClient(app, base_url="http://localhost").post(
            "/terminals/abcd1234/input", params={"message": "legacy"}
        )
    assert response.status_code == 200 and send.call_args.args[1] == "legacy"


@pytest.mark.parametrize("body", [{"message": "same"}, {"message": "different"}])
def test_two_message_sources_are_rejected_without_delivery(body):
    with patch("cli_agent_orchestrator.api.main.terminal_service.send_input") as send:
        response = TestClient(app, base_url="http://localhost").post(
            "/terminals/abcd1234/input", params={"message": "same"}, json=body
        )
    assert response.status_code == 400
    send.assert_not_called()


def test_missing_message_is_rejected_without_delivery():
    with patch("cli_agent_orchestrator.api.main.terminal_service.send_input") as send:
        response = TestClient(app, base_url="http://localhost").post("/terminals/abcd1234/input")
    assert response.status_code == 422
    send.assert_not_called()


def test_body_input_preserves_terminal_input_blocked_guard():
    from cli_agent_orchestrator.services.terminal_service import TerminalInputBlockedError

    with patch(
        "cli_agent_orchestrator.api.main.terminal_service.send_input",
        side_effect=TerminalInputBlockedError("Terminal awaits a user answer"),
    ) as send:
        response = TestClient(app, base_url="http://localhost").post(
            "/terminals/abcd1234/input", json={"message": "full prompt"}
        )
    assert response.status_code == 409
    assert send.call_count == 1


def test_body_input_false_result_does_not_claim_acceptance():
    with patch(
        "cli_agent_orchestrator.api.main.terminal_service.send_input", return_value=False
    ) as send:
        response = TestClient(app, base_url="http://localhost").post(
            "/terminals/abcd1234/input", json={"message": "full prompt"}
        )
    assert response.status_code == 200 and response.json() == {"success": False}
    assert send.call_count == 1
