# -*- coding: utf-8 -*-
"""SRT.run()과 TelegramNotifier 통합 테스트"""
from unittest.mock import MagicMock, patch, call
import pytest

from srt_reservation.main import SRT
from srt_reservation.notifier import TelegramNotifier
from srt_reservation.recovery import RecoveryError


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def srt():
    """SRT 인스턴스 (드라이버 초기화 없이)"""
    return SRT(
        dpt_stn="수서",
        arr_stn="동대구",
        dpt_dt="20260315",
        dpt_tm="08",
    )


# ---------------------------------------------------------------------------
# __init__ 내 notifier 생성 테스트
# ---------------------------------------------------------------------------

class TestSRTInitNotifier:
    def test_notifier_attribute_exists(self, srt):
        assert hasattr(srt, "notifier")

    def test_notifier_is_telegram_notifier(self, srt):
        assert isinstance(srt.notifier, TelegramNotifier)

    def test_notifier_is_unconfigured_by_default(self, srt, monkeypatch):
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        fresh = SRT("수서", "동대구", "20260315", "08")
        assert fresh.notifier.is_configured() is False


# ---------------------------------------------------------------------------
# run() 성공 시 notify_success 호출 테스트
# ---------------------------------------------------------------------------

class TestRunNotifySuccess:
    def _patch_run(self, srt, is_booked=True):
        """run() 내부 WebDriver 관련 메서드 전부 mock"""
        srt.driver = MagicMock()
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=True)
        srt.go_search = MagicMock()
        srt.check_result = MagicMock()
        srt.is_booked = is_booked

    def test_notify_success_called_when_booked(self, srt):
        self._patch_run(srt, is_booked=True)
        with patch.object(srt.notifier, "notify_success", return_value=True) as mock_notify:
            srt.run("user", "pass")
            mock_notify.assert_called_once()

    def test_notify_success_not_called_when_not_booked(self, srt):
        self._patch_run(srt, is_booked=False)
        with patch.object(srt.notifier, "notify_success", return_value=True) as mock_notify:
            srt.run("user", "pass")
            mock_notify.assert_not_called()

    def test_notify_success_receives_train_info_dict(self, srt):
        self._patch_run(srt, is_booked=True)
        with patch.object(srt.notifier, "notify_success", return_value=True) as mock_notify:
            srt.run("user", "pass")
            args = mock_notify.call_args[0][0]
            assert isinstance(args, dict)
            assert "dept_time" in args
            assert "arri_time" in args
            assert "seat_type" in args

    def test_booking_proceeds_even_if_notify_fails(self, srt):
        self._patch_run(srt, is_booked=True)
        with patch.object(srt.notifier, "notify_success", return_value=False):
            # 예외 없이 완료되어야 함
            srt.run("user", "pass")
            assert srt.is_booked is True


# ---------------------------------------------------------------------------
# run() 실패 시 notify_failure 호출 테스트
# ---------------------------------------------------------------------------

class TestRunNotifyFailure:
    def test_notify_failure_called_on_general_exception(self, srt):
        srt.run_driver = MagicMock(side_effect=RuntimeError("drv error"))
        with patch.object(srt.notifier, "notify_failure", return_value=True) as mock_notify:
            with pytest.raises(RuntimeError):
                srt.run("user", "pass")
            mock_notify.assert_called_once()

    def test_notify_failure_called_with_exception_message(self, srt):
        srt.run_driver = MagicMock(side_effect=RuntimeError("drv error"))
        with patch.object(srt.notifier, "notify_failure", return_value=True) as mock_notify:
            with pytest.raises(RuntimeError):
                srt.run("user", "pass")
            reason = mock_notify.call_args[0][0]
            assert "drv error" in reason

    def test_run_raises_even_if_notify_succeeds(self, srt):
        srt.run_driver = MagicMock(side_effect=RuntimeError("err"))
        with patch.object(srt.notifier, "notify_failure", return_value=True):
            with pytest.raises(RuntimeError):
                srt.run("user", "pass")

    def test_run_raises_even_if_notify_fails(self, srt):
        srt.run_driver = MagicMock(side_effect=RuntimeError("err"))
        with patch.object(srt.notifier, "notify_failure", return_value=False):
            with pytest.raises(RuntimeError):
                srt.run("user", "pass")

    def test_notify_failure_called_on_login_failure(self, srt):
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=False)
        srt.driver = MagicMock()
        with patch.object(srt.notifier, "notify_failure", return_value=True) as mock_notify:
            with pytest.raises(Exception, match="로그인"):
                srt.run("user", "pass")
            mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# 미설정 시 알림 무시 (에러 없음) 테스트
# ---------------------------------------------------------------------------

class TestNotifierUnconfigured:
    def test_run_succeeds_without_telegram_config(self, srt, monkeypatch):
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        fresh = SRT("수서", "동대구", "20260315", "08")
        fresh.run_driver = MagicMock()
        fresh.set_log_info = MagicMock()
        fresh.login = MagicMock()
        fresh.check_login = MagicMock(return_value=True)
        fresh.go_search = MagicMock()
        fresh.check_result = MagicMock()
        fresh.is_booked = True
        fresh.driver = MagicMock()
        # 예외 없이 완료되어야 함
        fresh.run("user", "pass")

    def test_run_fails_without_telegram_config(self, srt, monkeypatch):
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        fresh = SRT("수서", "동대구", "20260315", "08")
        fresh.run_driver = MagicMock(side_effect=RuntimeError("no driver"))
        # 알림 없이 정상적으로 예외 전파되어야 함
        with pytest.raises(RuntimeError):
            fresh.run("user", "pass")
