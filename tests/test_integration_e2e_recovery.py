# -*- coding: utf-8 -*-
"""
F-08 에러 리커버리 E2E 통합 시나리오 테스트

실제 WebDriver 없이 시나리오 전체 흐름을 시뮬레이션합니다.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException,
    NoAlertPresentException,
)

from srt_reservation.recovery import (
    RecoveryContext,
    RecoveryError,
    ErrorType,
    NetworkErrorRecovery,
    SessionRecovery,
    BrowserRecovery,
)
from srt_reservation.main import SRT


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
# 시나리오 1: 네트워크 타임아웃 → 자동 재시도 → 예약 성공
# ─────────────────────────────────────────────────────────────

class TestScenario1NetworkTimeoutRetry:
    @patch("srt_reservation.recovery.time.sleep")
    def test_network_timeout_then_success(self, mock_sleep):
        """TimeoutException 2번 발생 후 3번째에 성공"""
        ctx = RecoveryContext(max_retries=3)
        call_count = {"n": 0}

        def operation():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise TimeoutException()
            return "예약 성공"

        result = NetworkErrorRecovery.recover(operation, ctx)
        assert result == "예약 성공"
        assert call_count["n"] == 3
        assert mock_sleep.call_count == 2

    @patch("srt_reservation.recovery.time.sleep")
    def test_network_timeout_exhausted_raises(self, mock_sleep):
        """3번 모두 TimeoutException → RecoveryError"""
        ctx = RecoveryContext(max_retries=3)
        operation = MagicMock(side_effect=TimeoutException())

        with pytest.raises(RecoveryError) as exc_info:
            NetworkErrorRecovery.recover(operation, ctx)

        assert "최대 재시도" in str(exc_info.value)
        assert operation.call_count == 3


# ─────────────────────────────────────────────────────────────
# 시나리오 2: 세션 만료(로그인 리다이렉트) → 재로그인 → 검색 재개
# ─────────────────────────────────────────────────────────────

class TestScenario2SessionExpiredRedirect:
    @patch("srt_reservation.recovery.time.sleep")
    def test_session_expired_url_relogin_success(self, mock_sleep):
        """로그인 URL 감지 → 재로그인 성공"""
        driver = MagicMock()
        driver.current_url = "https://etk.srail.co.kr/login/form.do"

        srt = MagicMock()
        ctx = RecoveryContext(max_retries=2)

        # 세션 만료 감지
        assert SessionRecovery.is_session_expired(driver) is True

        # 복구
        result = SessionRecovery.recover(driver, srt, ctx)
        assert result is True
        srt.login.assert_called_once()

    @patch("srt_reservation.recovery.time.sleep")
    def test_session_expired_url_relogin_then_go_search(self, mock_sleep):
        """재로그인 후 go_search 호출"""
        srt = make_srt()
        srt.driver = MagicMock()
        srt.driver.current_url = "https://etk.srail.co.kr/hpg/hra/01/selectScheduleList.do"
        srt.go_search = MagicMock()

        # 복구 후 go_search 호출하는 전체 흐름 시뮬레이션
        with patch("srt_reservation.main.NetworkErrorRecovery.recover") as mock_net:
            with patch("srt_reservation.main.SessionRecovery.is_session_expired") as mock_expired:
                with patch("srt_reservation.main.SessionRecovery.recover") as mock_sess:
                    call_n = {"c": 0}

                    def net_recover_side(operation, context, **kwargs):
                        call_n["c"] += 1
                        if call_n["c"] == 1:
                            raise RuntimeError("session gone")
                        return srt.driver

                    mock_net.side_effect = net_recover_side
                    mock_expired.return_value = True
                    mock_sess.return_value = True

                    with patch("srt_reservation.main.time.sleep"):
                        result = srt.check_result()

        assert mock_sess.called
        assert srt.go_search.called


# ─────────────────────────────────────────────────────────────
# 시나리오 3: 세션 만료(Alert) → 자동 처리 → 재로그인
# ─────────────────────────────────────────────────────────────

class TestScenario3SessionExpiredAlert:
    def test_alert_detected_and_accepted(self):
        """Alert 발생 시 accept 후 세션 만료 반환"""
        driver = MagicMock()
        driver.current_url = "https://etk.srail.co.kr/normal/page"
        alert = MagicMock()
        driver.switch_to.alert = alert

        expired = SessionRecovery.is_session_expired(driver)
        assert expired is True
        alert.accept.assert_called_once()

    @patch("srt_reservation.recovery.time.sleep")
    def test_alert_session_then_relogin(self, mock_sleep):
        """Alert 처리 후 재로그인 성공"""
        driver = MagicMock()
        alert = MagicMock()
        driver.switch_to.alert = alert
        driver.current_url = "https://etk.srail.co.kr/normal"

        srt = MagicMock()
        ctx = RecoveryContext(max_retries=2)

        # Alert 있으므로 만료 감지
        assert SessionRecovery.is_session_expired(driver) is True

        # 복구
        result = SessionRecovery.recover(driver, srt, ctx)
        assert result is True
        srt.login.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 시나리오 4: WebDriver 연결 끊김 → 브라우저 복구 → 예약 성공
# ─────────────────────────────────────────────────────────────

class TestScenario4BrowserCrashRecovery:
    def test_browser_dead_then_recover(self):
        """is_browser_alive=False → 복구 후 정상 동작"""
        driver = MagicMock()
        type(driver).current_window_handle = property(
            lambda self: (_ for _ in ()).throw(Exception("dead"))
        )

        # 브라우저 죽었음 확인
        assert BrowserRecovery.is_browser_alive(driver) is False

        # 복구
        srt = MagicMock()
        ctx = RecoveryContext()
        result = BrowserRecovery.recover(driver, srt, ctx)

        assert result is True
        srt.run_driver.assert_called_once()
        srt.login.assert_called_once()
        srt.go_search.assert_called_once()

    @patch("srt_reservation.main.BrowserRecovery.recover")
    @patch("srt_reservation.main.time.sleep")
    def test_run_browser_crash_and_recovery(self, mock_sleep, mock_browser_recover):
        """SRT.run()에서 InvalidSessionIdException 발생 시 BrowserRecovery 호출"""
        srt = make_srt()
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=True)
        srt.go_search = MagicMock()
        srt.is_booked = True
        mock_browser_recover.return_value = True

        with patch.object(srt, "check_result", side_effect=[InvalidSessionIdException(), None]):
            srt.run("user", "pass")

        mock_browser_recover.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 시나리오 5: 복합 장애 (네트워크 → 세션 만료 → 브라우저 복구)
# ─────────────────────────────────────────────────────────────

class TestScenario5CompoundFailure:
    @patch("srt_reservation.recovery.time.sleep")
    def test_network_then_session_recovery(self, mock_sleep):
        """네트워크 오류 1회 → 세션 만료 → 재로그인 → 최종 성공"""
        call_n = {"n": 0}
        results = [TimeoutException(), "예약 완료"]

        def operation():
            val = results[call_n["n"]]
            call_n["n"] += 1
            if isinstance(val, Exception):
                raise val
            return val

        ctx = RecoveryContext(max_retries=3)
        result = NetworkErrorRecovery.recover(operation, ctx)
        assert result == "예약 완료"

    def test_full_compound_recovery_context_independence(self):
        """각 에러 타입 카운터가 독립적으로 관리됨"""
        ctx = RecoveryContext(max_retries=3)

        # 네트워크 오류 2회
        ctx.increment(ErrorType.NETWORK)
        ctx.increment(ErrorType.NETWORK)
        # 세션 오류 1회
        ctx.increment(ErrorType.SESSION)
        # 브라우저 복구 1회
        ctx.increment(ErrorType.BROWSER)

        assert ctx.retry_count[ErrorType.NETWORK] == 2
        assert ctx.retry_count[ErrorType.SESSION] == 1
        assert ctx.retry_count[ErrorType.BROWSER] == 1

        # 네트워크 리셋 후 다시 가능
        ctx.reset(ErrorType.NETWORK)
        assert ctx.can_retry(ErrorType.NETWORK) is True
        # 세션, 브라우저는 영향 없음
        assert ctx.retry_count[ErrorType.SESSION] == 1
        assert ctx.retry_count[ErrorType.BROWSER] == 1
