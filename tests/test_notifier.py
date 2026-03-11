# -*- coding: utf-8 -*-
"""TelegramNotifier 유닛 테스트"""
import os
import json
import urllib.error
from io import BytesIO
from unittest import mock
from unittest.mock import MagicMock, patch, call

import pytest

from srt_reservation.notifier import TelegramNotifier


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def configured_env(monkeypatch):
    """TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 환경변수 설정"""
    monkeypatch.setenv("TELEGRAM_TOKEN", "test_token_123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345678")


@pytest.fixture
def unconfigured_env(monkeypatch):
    """환경변수 미설정"""
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)


@pytest.fixture
def notifier_configured(configured_env):
    return TelegramNotifier()


@pytest.fixture
def notifier_unconfigured(unconfigured_env):
    return TelegramNotifier()


# ---------------------------------------------------------------------------
# __init__ 테스트
# ---------------------------------------------------------------------------

class TestTelegramNotifierInit:
    def test_loads_token_from_env(self, configured_env):
        n = TelegramNotifier()
        assert n.token == "test_token_123"

    def test_loads_chat_id_from_env(self, configured_env):
        n = TelegramNotifier()
        assert n.chat_id == "12345678"

    def test_token_none_when_not_set(self, unconfigured_env):
        n = TelegramNotifier()
        assert n.token is None

    def test_chat_id_none_when_not_set(self, unconfigured_env):
        n = TelegramNotifier()
        assert n.chat_id is None

    def test_partial_config_token_only(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_TOKEN", "tok")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        n = TelegramNotifier()
        assert n.token == "tok"
        assert n.chat_id is None

    def test_partial_config_chat_id_only(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
        n = TelegramNotifier()
        assert n.token is None
        assert n.chat_id == "999"


# ---------------------------------------------------------------------------
# is_configured 테스트
# ---------------------------------------------------------------------------

class TestIsConfigured:
    def test_true_when_both_set(self, notifier_configured):
        assert notifier_configured.is_configured() is True

    def test_false_when_neither_set(self, notifier_unconfigured):
        assert notifier_unconfigured.is_configured() is False

    def test_false_when_token_only(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_TOKEN", "tok")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        n = TelegramNotifier()
        assert n.is_configured() is False

    def test_false_when_chat_id_only(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        n = TelegramNotifier()
        assert n.is_configured() is False

    def test_false_when_token_empty_string(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_TOKEN", "")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        n = TelegramNotifier()
        assert n.is_configured() is False

    def test_false_when_chat_id_empty_string(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
        n = TelegramNotifier()
        assert n.is_configured() is False


# ---------------------------------------------------------------------------
# send_message 테스트
# ---------------------------------------------------------------------------

class TestSendMessage:
    def _make_response(self, status=200, body=b'{"ok":true}'):
        resp = MagicMock()
        resp.status = status
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_returns_false_when_not_configured(self, notifier_unconfigured):
        result = notifier_unconfigured.send_message("hello")
        assert result is False

    def test_does_not_call_api_when_not_configured(self, notifier_unconfigured):
        with patch("urllib.request.urlopen") as mock_urlopen:
            notifier_unconfigured.send_message("hello")
            mock_urlopen.assert_not_called()

    def test_returns_true_on_success(self, notifier_configured):
        resp = self._make_response(status=200)
        with patch("urllib.request.urlopen", return_value=resp):
            result = notifier_configured.send_message("hello")
        assert result is True

    def test_calls_correct_api_url(self, notifier_configured):
        resp = self._make_response(status=200)
        with patch("urllib.request.urlopen", return_value=resp) as mock_urlopen:
            notifier_configured.send_message("test")
            args = mock_urlopen.call_args
            req = args[0][0]
            assert "api.telegram.org" in req.full_url
            assert "test_token_123" in req.full_url

    def test_sends_correct_chat_id(self, notifier_configured):
        resp = self._make_response(status=200)
        with patch("urllib.request.urlopen", return_value=resp) as mock_urlopen:
            notifier_configured.send_message("test")
            req = mock_urlopen.call_args[0][0]
            body = req.data.decode("utf-8")
            assert "12345678" in body

    def test_sends_message_text_in_body(self, notifier_configured):
        resp = self._make_response(status=200)
        with patch("urllib.request.urlopen", return_value=resp) as mock_urlopen:
            notifier_configured.send_message("안녕하세요")
            req = mock_urlopen.call_args[0][0]
            body = req.data.decode("utf-8")
            assert "chat_id" in body
            assert "text" in body

    def test_returns_false_on_non_200_status(self, notifier_configured):
        resp = self._make_response(status=400)
        with patch("urllib.request.urlopen", return_value=resp):
            result = notifier_configured.send_message("hello")
        assert result is False

    def test_returns_false_on_http_error(self, notifier_configured):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.HTTPError(None, 500, "Server Error", {}, None)):
            result = notifier_configured.send_message("hello")
        assert result is False

    def test_returns_false_on_url_error(self, notifier_configured):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            result = notifier_configured.send_message("hello")
        assert result is False

    def test_returns_false_on_generic_exception(self, notifier_configured):
        with patch("urllib.request.urlopen", side_effect=Exception("unexpected")):
            result = notifier_configured.send_message("hello")
        assert result is False

    def test_does_not_raise_on_failure(self, notifier_configured):
        with patch("urllib.request.urlopen", side_effect=Exception("boom")):
            # 예외가 전파되지 않아야 함
            try:
                notifier_configured.send_message("hello")
            except Exception:
                pytest.fail("send_message raised an exception")

    def test_timeout_5_seconds(self, notifier_configured):
        resp = self._make_response(status=200)
        with patch("urllib.request.urlopen", return_value=resp) as mock_urlopen:
            notifier_configured.send_message("hello")
            args, kwargs = mock_urlopen.call_args
            assert kwargs.get("timeout") == 5 or args[1] == 5


# ---------------------------------------------------------------------------
# notify_success 테스트
# ---------------------------------------------------------------------------

class TestNotifySuccess:
    def test_returns_true_on_success(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            result = notifier_configured.notify_success({
                "dept_time": "08:30",
                "arri_time": "11:00",
                "seat_type": "일반석",
            })
        assert result is True

    def test_message_contains_dept_time(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            notifier_configured.notify_success({
                "dept_time": "08:30",
                "arri_time": "11:00",
                "seat_type": "일반석",
            })
            msg = mock_send.call_args[0][0]
            assert "08:30" in msg

    def test_message_contains_arri_time(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            notifier_configured.notify_success({
                "dept_time": "08:30",
                "arri_time": "11:00",
                "seat_type": "일반석",
            })
            msg = mock_send.call_args[0][0]
            assert "11:00" in msg

    def test_message_contains_seat_type(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            notifier_configured.notify_success({
                "dept_time": "08:30",
                "arri_time": "11:00",
                "seat_type": "특실",
            })
            msg = mock_send.call_args[0][0]
            assert "특실" in msg

    def test_defaults_when_keys_missing(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            notifier_configured.notify_success({})
            msg = mock_send.call_args[0][0]
            assert "N/A" in msg
            assert "일반석" in msg

    def test_returns_false_when_not_configured(self, notifier_unconfigured):
        result = notifier_unconfigured.notify_success({"dept_time": "08:30"})
        assert result is False

    def test_returns_false_when_send_fails(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=False):
            result = notifier_configured.notify_success({
                "dept_time": "08:30",
                "arri_time": "11:00",
                "seat_type": "일반석",
            })
        assert result is False


# ---------------------------------------------------------------------------
# notify_failure 테스트
# ---------------------------------------------------------------------------

class TestNotifyFailure:
    def test_returns_true_on_success(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True):
            result = notifier_configured.notify_failure("타임아웃")
        assert result is True

    def test_message_contains_reason(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            notifier_configured.notify_failure("타임아웃")
            msg = mock_send.call_args[0][0]
            assert "타임아웃" in msg

    def test_default_reason(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=True) as mock_send:
            notifier_configured.notify_failure()
            msg = mock_send.call_args[0][0]
            assert "최대 재시도 초과" in msg

    def test_returns_false_when_not_configured(self, notifier_unconfigured):
        result = notifier_unconfigured.notify_failure("오류")
        assert result is False

    def test_returns_false_when_send_fails(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", return_value=False):
            result = notifier_configured.notify_failure("오류")
        assert result is False

    def test_does_not_raise_on_failure(self, notifier_configured):
        with patch.object(notifier_configured, "send_message", side_effect=Exception("boom")):
            try:
                notifier_configured.notify_failure("오류")
            except Exception:
                pytest.fail("notify_failure raised an exception")
