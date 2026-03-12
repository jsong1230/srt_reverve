# -*- coding: utf-8 -*-
"""
main.py - recovery 통합 테스트

SRT.check_result()와 SRT.run() 메서드의 에러 리커버리 통합 동작 테스트
"""
import pytest
from unittest.mock import MagicMock, patch, call, PropertyMock
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException,
)

from srt_reservation.main import SRT
from srt_reservation.recovery import RecoveryError


VALID_KWARGS = dict(
    dpt_stn="동탄",
    arr_stn="동대구",
    dpt_dt="20260401",
    dpt_tm="08",
    anti_bot_method="enhanced",
)


def make_srt(**kwargs) -> SRT:
    merged = {**VALID_KWARGS, **kwargs}
    return SRT(**merged)


# ─────────────────────────────────────────────────────────────
# SRT.__init__ - RecoveryContext 초기화 확인
# ─────────────────────────────────────────────────────────────

class TestSRTRecoveryInit:
    def test_recovery_context_created(self):
        srt = make_srt()
        assert hasattr(srt, "recovery_context")
        assert srt.recovery_context.max_retries == 3

    def test_recovery_context_max_retries_default(self):
        from srt_reservation.recovery import RecoveryContext
        srt = make_srt()
        assert isinstance(srt.recovery_context, RecoveryContext)


# ─────────────────────────────────────────────────────────────
# SRT.check_result() - 네트워크 오류 재시도
# ─────────────────────────────────────────────────────────────

class TestCheckResultNetworkRecovery:
    @patch("srt_reservation.main.time.sleep")
    @patch("srt_reservation.main.NetworkErrorRecovery.recover")
    def test_check_result_calls_network_recover(self, mock_recover, mock_sleep):
        srt = make_srt()
        srt.driver = MagicMock()
        srt.is_booked = False
        srt.go_search = MagicMock()  # go_search mock 추가

        # 첫 번째 recover 호출에서 드라이버 반환 → 루프 종료
        mock_recover.return_value = srt.driver

        result = srt.check_result()
        assert mock_recover.called

    @patch("srt_reservation.main.time.sleep")
    @patch("srt_reservation.main.NetworkErrorRecovery.recover")
    def test_check_result_raises_recovery_error(self, mock_recover, mock_sleep):
        srt = make_srt()
        srt.driver = MagicMock()
        srt.go_search = MagicMock()  # go_search mock 추가

        mock_recover.side_effect = RecoveryError("네트워크 오류: 최대 재시도(3회) 초과")

        with pytest.raises(RecoveryError):
            srt.check_result()

    @patch("srt_reservation.main.SessionRecovery.is_session_expired")
    @patch("srt_reservation.main.time.sleep")
    @patch("srt_reservation.main.NetworkErrorRecovery.recover")
    def test_check_result_reraises_non_network_error(self, mock_recover, mock_sleep, mock_is_expired):
        srt = make_srt()
        srt.driver = MagicMock()
        srt.go_search = MagicMock()  # go_search mock 추가

        # recover가 ValueError 전파, 세션 만료 아님 → 그대로 재전파
        mock_recover.side_effect = ValueError("unexpected error")
        mock_is_expired.return_value = False

        with pytest.raises(ValueError):
            srt.check_result()


# ─────────────────────────────────────────────────────────────
# SRT.check_result() - 세션 만료 복구
# ─────────────────────────────────────────────────────────────

class TestCheckResultSessionRecovery:
    @patch("srt_reservation.main.time.sleep")
    @patch("srt_reservation.main.SessionRecovery.recover")
    @patch("srt_reservation.main.SessionRecovery.is_session_expired")
    @patch("srt_reservation.main.NetworkErrorRecovery.recover")
    def test_check_result_session_recovery(
        self, mock_net_recover, mock_is_expired, mock_sess_recover, mock_sleep
    ):
        srt = make_srt()
        srt.driver = MagicMock()
        srt.go_search = MagicMock()

        # 첫 번째 호출에서 일반 예외 → 세션 만료로 판정 → 복구 후 두 번째 호출에서 driver 반환
        call_count = {"n": 0}

        def net_recover_side_effect(operation, context, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("some error")
            return srt.driver

        mock_net_recover.side_effect = net_recover_side_effect
        mock_is_expired.return_value = True
        mock_sess_recover.return_value = True

        result = srt.check_result()
        assert mock_sess_recover.called
        assert srt.go_search.called

    @patch("srt_reservation.main.time.sleep")
    @patch("srt_reservation.main.SessionRecovery.recover")
    @patch("srt_reservation.main.SessionRecovery.is_session_expired")
    @patch("srt_reservation.main.NetworkErrorRecovery.recover")
    def test_check_result_session_recovery_failure_raises(
        self, mock_net_recover, mock_is_expired, mock_sess_recover, mock_sleep
    ):
        srt = make_srt()
        srt.driver = MagicMock()
        srt.go_search = MagicMock()  # go_search mock 추가

        mock_net_recover.side_effect = RuntimeError("some error")
        mock_is_expired.return_value = True
        mock_sess_recover.side_effect = RecoveryError("세션 복구 실패")

        with pytest.raises(RecoveryError):
            srt.check_result()


# ─────────────────────────────────────────────────────────────
# SRT.run() - 브라우저 크래시 복구
# ─────────────────────────────────────────────────────────────

class TestRunBrowserRecovery:
    @patch("srt_reservation.main.BrowserRecovery.recover")
    @patch("srt_reservation.main.time.sleep")
    def test_run_browser_crash_recovery(self, mock_sleep, mock_browser_recover):
        srt = make_srt()
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=True)
        srt.go_search = MagicMock()
        srt.check_result = MagicMock()
        srt.driver = MagicMock()
        srt.is_booked = True

        # check_result가 InvalidSessionIdException 발생 → 브라우저 복구
        srt.check_result.side_effect = [InvalidSessionIdException(), None]

        # 첫 번째 check_result 실패 시 BrowserRecovery.recover 호출 후 재시도
        mock_browser_recover.return_value = True

        # run 호출 시 InvalidSessionIdException → BrowserRecovery → 재시도
        with patch.object(srt, "check_result", side_effect=[InvalidSessionIdException(), None]):
            srt.run("test_user", "test_pass")

        mock_browser_recover.assert_called_once()

    @patch("srt_reservation.main.BrowserRecovery.recover")
    @patch("srt_reservation.main.time.sleep")
    def test_run_browser_crash_recovery_failure_raises(self, mock_sleep, mock_browser_recover):
        srt = make_srt()
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=True)
        srt.go_search = MagicMock()
        srt.driver = MagicMock()

        mock_browser_recover.side_effect = RecoveryError("복구 실패")

        with patch.object(srt, "check_result", side_effect=InvalidSessionIdException()):
            with pytest.raises(RuntimeError, match="브라우저 연결이 끊어졌습니다"):
                srt.run("test_user", "test_pass")

    def test_run_normal_success(self):
        srt = make_srt()
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=True)
        srt.check_result = MagicMock()
        srt.is_booked = True

        with patch("srt_reservation.main.time.sleep"):
            srt.run("user", "pass")

        srt.run_driver.assert_called_once()
        srt.login.assert_called_once()
        # go_search는 check_result() 내부에서 호출되므로, check_result 호출만 확인
        srt.check_result.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 복구 로깅 검증
# ─────────────────────────────────────────────────────────────

class TestRecoveryLogging:
    @patch("srt_reservation.recovery.time.sleep")
    def test_network_recovery_logs_warning(self, mock_sleep, caplog):
        import logging
        from srt_reservation.recovery import RecoveryContext, NetworkErrorRecovery
        ctx = RecoveryContext(max_retries=2)
        operation = MagicMock(side_effect=[TimeoutException(), "ok"])

        with caplog.at_level(logging.WARNING, logger="srt_reservation.recovery"):
            NetworkErrorRecovery.recover(operation, ctx)

        assert any("네트워크 오류 재시도" in r.message for r in caplog.records)

    @patch("srt_reservation.recovery.time.sleep")
    def test_session_recovery_logs_info(self, mock_sleep, caplog):
        import logging
        from srt_reservation.recovery import RecoveryContext, SessionRecovery
        driver = MagicMock()
        srt = MagicMock()
        ctx = RecoveryContext(max_retries=2)

        with caplog.at_level(logging.INFO, logger="srt_reservation.recovery"):
            SessionRecovery.recover(driver, srt, ctx)

        assert any("재로그인" in r.message for r in caplog.records)

    def test_browser_recovery_logs_warning(self, caplog):
        import logging
        from srt_reservation.recovery import RecoveryContext, BrowserRecovery
        driver = MagicMock()
        srt = MagicMock()
        ctx = RecoveryContext()

        with caplog.at_level(logging.WARNING, logger="srt_reservation.recovery"):
            BrowserRecovery.recover(driver, srt, ctx)

        assert any("크래시" in r.message for r in caplog.records)
