# -*- coding: utf-8 -*-
"""
srt_reservation.recovery 모듈 단위 테스트

RecoveryContext, NetworkErrorRecovery, SessionRecovery, BrowserRecovery 테스트
"""
import pytest
from unittest.mock import MagicMock, patch, call
from selenium.common.exceptions import TimeoutException, NoAlertPresentException

from srt_reservation.recovery import (
    RecoveryContext,
    RecoveryError,
    ErrorType,
    NetworkErrorRecovery,
    SessionRecovery,
    BrowserRecovery,
    is_network_error,
    is_session_error,
)


# ─────────────────────────────────────────────────────────────
# RecoveryContext 테스트
# ─────────────────────────────────────────────────────────────

class TestRecoveryContext:
    def test_initial_counts_are_zero(self):
        ctx = RecoveryContext()
        for error_type in ErrorType:
            assert ctx.retry_count[error_type] == 0

    def test_can_retry_initially_true(self):
        ctx = RecoveryContext(max_retries=3)
        assert ctx.can_retry(ErrorType.NETWORK) is True
        assert ctx.can_retry(ErrorType.SESSION) is True
        assert ctx.can_retry(ErrorType.BROWSER) is True

    def test_increment_returns_current_count(self):
        ctx = RecoveryContext()
        assert ctx.increment(ErrorType.NETWORK) == 1
        assert ctx.increment(ErrorType.NETWORK) == 2
        assert ctx.increment(ErrorType.NETWORK) == 3

    def test_can_retry_false_when_exhausted(self):
        ctx = RecoveryContext(max_retries=3)
        ctx.increment(ErrorType.NETWORK)
        ctx.increment(ErrorType.NETWORK)
        ctx.increment(ErrorType.NETWORK)
        assert ctx.can_retry(ErrorType.NETWORK) is False

    def test_reset_clears_count(self):
        ctx = RecoveryContext()
        ctx.increment(ErrorType.SESSION)
        ctx.increment(ErrorType.SESSION)
        ctx.reset(ErrorType.SESSION)
        assert ctx.retry_count[ErrorType.SESSION] == 0
        assert ctx.can_retry(ErrorType.SESSION) is True

    def test_error_types_are_independent(self):
        ctx = RecoveryContext(max_retries=2)
        ctx.increment(ErrorType.NETWORK)
        ctx.increment(ErrorType.NETWORK)
        # NETWORK 소진해도 SESSION은 독립
        assert ctx.can_retry(ErrorType.NETWORK) is False
        assert ctx.can_retry(ErrorType.SESSION) is True

    def test_custom_max_retries(self):
        ctx = RecoveryContext(max_retries=1)
        ctx.increment(ErrorType.BROWSER)
        assert ctx.can_retry(ErrorType.BROWSER) is False


# ─────────────────────────────────────────────────────────────
# NetworkErrorRecovery 테스트
# ─────────────────────────────────────────────────────────────

class TestNetworkErrorRecovery:
    def test_should_retry_timeout_exception(self):
        assert NetworkErrorRecovery.should_retry(TimeoutException()) is True

    def test_should_retry_connection_error(self):
        assert NetworkErrorRecovery.should_retry(ConnectionError()) is True

    def test_should_retry_os_error(self):
        assert NetworkErrorRecovery.should_retry(OSError()) is True

    def test_should_not_retry_value_error(self):
        assert NetworkErrorRecovery.should_retry(ValueError("bad")) is False

    def test_should_not_retry_runtime_error(self):
        assert NetworkErrorRecovery.should_retry(RuntimeError("boom")) is False

    def test_get_wait_time_first_retry(self):
        wait = NetworkErrorRecovery.get_wait_time(1)
        # 1회: base=5, jitter=±1 → 4~6초
        assert 4.0 <= wait <= 6.0

    def test_get_wait_time_second_retry(self):
        wait = NetworkErrorRecovery.get_wait_time(2)
        # 2회: base=10, jitter=±1 → 9~11초
        assert 9.0 <= wait <= 11.0

    def test_get_wait_time_third_retry(self):
        wait = NetworkErrorRecovery.get_wait_time(3)
        # 3회: base=20, jitter=±1 → 19~21초
        assert 19.0 <= wait <= 21.0

    def test_recover_success_on_first_try(self):
        ctx = RecoveryContext(max_retries=3)
        operation = MagicMock(return_value="ok")

        result = NetworkErrorRecovery.recover(operation, ctx)
        assert result == "ok"
        operation.assert_called_once()

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_retries_on_timeout(self, mock_sleep):
        ctx = RecoveryContext(max_retries=3)
        # 2번 실패 후 성공
        operation = MagicMock(side_effect=[
            TimeoutException(), TimeoutException(), "success"
        ])

        result = NetworkErrorRecovery.recover(operation, ctx)
        assert result == "success"
        assert operation.call_count == 3

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_raises_after_max_retries(self, mock_sleep):
        ctx = RecoveryContext(max_retries=3)
        operation = MagicMock(side_effect=TimeoutException())

        with pytest.raises(RecoveryError, match="최대 재시도"):
            NetworkErrorRecovery.recover(operation, ctx)

    def test_recover_raises_non_network_error(self):
        ctx = RecoveryContext(max_retries=3)
        operation = MagicMock(side_effect=ValueError("not a network error"))

        with pytest.raises(ValueError):
            NetworkErrorRecovery.recover(operation, ctx)

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_resets_count_on_success(self, mock_sleep):
        ctx = RecoveryContext(max_retries=3)
        operation = MagicMock(side_effect=[TimeoutException(), "ok"])

        NetworkErrorRecovery.recover(operation, ctx)
        assert ctx.retry_count[ErrorType.NETWORK] == 0


# ─────────────────────────────────────────────────────────────
# SessionRecovery 테스트
# ─────────────────────────────────────────────────────────────

class TestSessionRecovery:
    def test_session_expired_login_url(self):
        driver = MagicMock()
        driver.current_url = "https://example.com/login/form"
        assert SessionRecovery.is_session_expired(driver) is True

    def test_session_expired_member_url(self):
        driver = MagicMock()
        driver.current_url = "https://example.com/member/auth"
        assert SessionRecovery.is_session_expired(driver) is True

    def test_session_not_expired_normal_url(self):
        from unittest.mock import PropertyMock
        driver = MagicMock()
        driver.current_url = "https://etk.srail.co.kr/hpg/hra/01/selectScheduleList.do"
        type(driver.switch_to).alert = PropertyMock(side_effect=NoAlertPresentException())
        assert SessionRecovery.is_session_expired(driver) is False

    def test_session_expired_alert_present(self):
        driver = MagicMock()
        driver.current_url = "https://etk.srail.co.kr/some/page"
        alert = MagicMock()
        driver.switch_to.alert = alert

        assert SessionRecovery.is_session_expired(driver) is True
        alert.accept.assert_called_once()

    def test_session_expired_when_driver_raises(self):
        from unittest.mock import PropertyMock
        driver = MagicMock()
        # current_url 접근 시 예외 발생 → alert도 없으면 False
        type(driver).current_url = PropertyMock(side_effect=Exception("driver dead"))
        type(driver.switch_to).alert = PropertyMock(side_effect=NoAlertPresentException())
        assert SessionRecovery.is_session_expired(driver) is False

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_login_success(self, mock_sleep):
        driver = MagicMock()
        srt = MagicMock()
        ctx = RecoveryContext(max_retries=2)

        result = SessionRecovery.recover(driver, srt, ctx)
        assert result is True
        srt.login.assert_called_once()

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_retries_on_login_failure(self, mock_sleep):
        driver = MagicMock()
        srt = MagicMock()
        srt.login.side_effect = [Exception("login failed"), None]
        ctx = RecoveryContext(max_retries=2)

        result = SessionRecovery.recover(driver, srt, ctx)
        assert result is True
        assert srt.login.call_count == 2

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_raises_after_max_retries(self, mock_sleep):
        driver = MagicMock()
        srt = MagicMock()
        srt.login.side_effect = Exception("always fails")
        ctx = RecoveryContext(max_retries=2)

        with pytest.raises(RecoveryError, match="세션 복구"):
            SessionRecovery.recover(driver, srt, ctx)

    @patch("srt_reservation.recovery.time.sleep")
    def test_recover_resets_count_on_success(self, mock_sleep):
        driver = MagicMock()
        srt = MagicMock()
        ctx = RecoveryContext(max_retries=2)

        SessionRecovery.recover(driver, srt, ctx)
        assert ctx.retry_count[ErrorType.SESSION] == 0


# ─────────────────────────────────────────────────────────────
# BrowserRecovery 테스트
# ─────────────────────────────────────────────────────────────

class TestBrowserRecovery:
    def test_is_browser_alive_true(self):
        driver = MagicMock()
        driver.current_window_handle = "abc"
        assert BrowserRecovery.is_browser_alive(driver) is True

    def test_is_browser_alive_false_when_exception(self):
        driver = MagicMock()
        type(driver).current_window_handle = property(
            lambda self: (_ for _ in ()).throw(Exception("session dead"))
        )
        assert BrowserRecovery.is_browser_alive(driver) is False

    def test_recover_success(self):
        driver = MagicMock()
        srt = MagicMock()
        ctx = RecoveryContext()

        result = BrowserRecovery.recover(driver, srt, ctx)
        assert result is True
        driver.quit.assert_called_once()
        srt.run_driver.assert_called_once()
        srt.login.assert_called_once()
        srt.go_search.assert_called_once()

    def test_recover_quits_old_driver_even_on_quit_error(self):
        driver = MagicMock()
        driver.quit.side_effect = Exception("already closed")
        srt = MagicMock()
        ctx = RecoveryContext()

        result = BrowserRecovery.recover(driver, srt, ctx)
        assert result is True
        # quit 실패해도 복구 성공
        srt.run_driver.assert_called_once()

    def test_recover_raises_on_run_driver_failure(self):
        driver = MagicMock()
        srt = MagicMock()
        srt.run_driver.side_effect = Exception("cannot start browser")
        ctx = RecoveryContext()

        with pytest.raises(RecoveryError, match="브라우저 복구 실패"):
            BrowserRecovery.recover(driver, srt, ctx)

    def test_recover_raises_on_login_failure(self):
        driver = MagicMock()
        srt = MagicMock()
        srt.login.side_effect = Exception("login error")
        ctx = RecoveryContext()

        with pytest.raises(RecoveryError, match="브라우저 복구 실패"):
            BrowserRecovery.recover(driver, srt, ctx)

    def test_recover_increments_browser_count(self):
        driver = MagicMock()
        srt = MagicMock()
        ctx = RecoveryContext()

        BrowserRecovery.recover(driver, srt, ctx)
        assert ctx.retry_count[ErrorType.BROWSER] == 1


# ─────────────────────────────────────────────────────────────
# 편의 함수 테스트
# ─────────────────────────────────────────────────────────────

class TestConvenienceFunctions:
    def test_is_network_error_true(self):
        assert is_network_error(TimeoutException()) is True
        assert is_network_error(ConnectionError()) is True
        assert is_network_error(OSError()) is True

    def test_is_network_error_false(self):
        assert is_network_error(ValueError()) is False
        assert is_network_error(RuntimeError()) is False

    def test_is_session_error_login_url(self):
        driver = MagicMock()
        driver.current_url = "https://example.com/login"
        assert is_session_error(driver) is True

    def test_is_session_error_normal_url(self):
        from unittest.mock import PropertyMock
        driver = MagicMock()
        driver.current_url = "https://etk.srail.co.kr/search"
        type(driver.switch_to).alert = PropertyMock(side_effect=NoAlertPresentException())
        assert is_session_error(driver) is False
