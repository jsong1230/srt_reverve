# -*- coding: utf-8 -*-
"""
에러 리커버리 모듈

네트워크 오류, 세션 만료, 브라우저 크래시 시 자동 복구 전략을 제공합니다.
"""
import logging
import random
import time
from enum import Enum
from typing import Any, Callable

from selenium.common.exceptions import (
    NoAlertPresentException,
    TimeoutException,
)

logger = logging.getLogger(__name__)


class RecoveryError(Exception):
    """에러 리커버리 실패 예외"""
    pass


class ErrorType(Enum):
    NETWORK = "network"   # TimeoutException, ConnectionError
    SESSION = "session"   # 로그인 페이지 리다이렉트
    BROWSER = "browser"   # WebDriver 연결 끊김


class RecoveryContext:
    """복구 전략 컨텍스트 - 에러 유형별 재시도 횟수 추적"""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_count: dict[ErrorType, int] = {
            ErrorType.NETWORK: 0,
            ErrorType.SESSION: 0,
            ErrorType.BROWSER: 0,
        }

    def increment(self, error_type: ErrorType) -> int:
        self.retry_count[error_type] += 1
        return self.retry_count[error_type]

    def reset(self, error_type: ErrorType) -> None:
        self.retry_count[error_type] = 0

    def can_retry(self, error_type: ErrorType) -> bool:
        return self.retry_count[error_type] < self.max_retries


class NetworkErrorRecovery:
    """네트워크 오류 재시도 전략 - 지수 백오프 적용"""

    @staticmethod
    def should_retry(exception: Exception) -> bool:
        """네트워크 오류 여부 판단 (TimeoutException, ConnectionError, OSError 포함)"""
        return isinstance(exception, (TimeoutException, ConnectionError, OSError))

    @staticmethod
    def get_wait_time(retry_count: int) -> float:
        """지수 백오프: 1회차 5초, 2회차 10초, 3회차 20초 (±1초 지터)"""
        base_wait = 5 * (2 ** (retry_count - 1))
        jitter = random.uniform(-1, 1)
        return max(5.0, base_wait + jitter)

    @staticmethod
    def recover(
        operation: Callable[[], Any],
        context: RecoveryContext,
        max_retries: int = 3,
    ) -> Any:
        """
        네트워크 오류 시 자동 재시도.

        Args:
            operation: 재시도할 함수 (인자 없이 호출 가능)
            context: RecoveryContext 객체
            max_retries: 최대 재시도 횟수

        Returns:
            operation의 반환값

        Raises:
            RecoveryError: 최대 재시도 횟수 초과 시
        """
        while context.can_retry(ErrorType.NETWORK):
            try:
                result = operation()
                context.reset(ErrorType.NETWORK)
                return result
            except Exception as e:
                if not NetworkErrorRecovery.should_retry(e):
                    raise

                count = context.increment(ErrorType.NETWORK)
                wait_time = NetworkErrorRecovery.get_wait_time(count)

                logger.warning(
                    f"[{count}/{max_retries}] 네트워크 오류 재시도. "
                    f"{wait_time:.1f}초 대기 후 재시도..."
                )
                time.sleep(wait_time)

        context.reset(ErrorType.NETWORK)
        raise RecoveryError(
            f"네트워크 오류: 최대 재시도({max_retries}회) 초과"
        )


class SessionRecovery:
    """세션 만료 감지 및 재로그인 전략"""

    @staticmethod
    def is_session_expired(driver: Any) -> bool:
        """
        세션 만료 여부 판단.
        - 현재 URL이 로그인 페이지인 경우
        - 예상치 못한 Alert 발생 시
        """
        try:
            current_url = driver.current_url
            if "login" in current_url.lower() or "member" in current_url.lower():
                return True
        except Exception:
            pass

        try:
            alert = driver.switch_to.alert
            logger.warning("예상치 못한 Alert 감지: 세션 만료 가능성")
            alert.accept()
            return True
        except (NoAlertPresentException, Exception):
            pass

        return False

    @staticmethod
    def recover(
        driver: Any,
        srt_instance: Any,
        context: RecoveryContext,
        max_retries: int = 2,
    ) -> bool:
        """
        세션 만료 시 자동 재로그인.

        Args:
            driver: Selenium WebDriver
            srt_instance: SRT 클래스 인스턴스 (login 메서드 사용)
            context: RecoveryContext 객체
            max_retries: 최대 재시도 횟수

        Returns:
            bool: 재로그인 성공 여부

        Raises:
            RecoveryError: 최대 재시도 횟수 초과 시
        """
        while context.can_retry(ErrorType.SESSION):
            try:
                logger.info("[세션 복구] 자동 재로그인 시도...")
                srt_instance.login()
                logger.info("[세션 복구] 재로그인 성공. 검색 재개...")
                context.reset(ErrorType.SESSION)
                return True
            except Exception as e:
                count = context.increment(ErrorType.SESSION)
                logger.warning(f"[{count}/{max_retries}] 재로그인 실패: {str(e)}")

                if context.can_retry(ErrorType.SESSION):
                    time.sleep(3)

        context.reset(ErrorType.SESSION)
        raise RecoveryError(
            f"세션 복구: 최대 재시도({max_retries}회) 초과"
        )


class BrowserRecovery:
    """브라우저 크래시 감지 및 복구 전략"""

    @staticmethod
    def is_browser_alive(driver: Any) -> bool:
        """브라우저 세션이 살아있는지 확인 (current_window_handle ping)"""
        try:
            _ = driver.current_window_handle
            return True
        except Exception:
            return False

    @staticmethod
    def recover(
        driver: Any,
        srt_instance: Any,
        context: RecoveryContext,
    ) -> bool:
        """
        브라우저 크래시 시 복구.
        - 기존 WebDriver 정리
        - 새 WebDriver 초기화
        - 로그인 및 검색 재시작

        Returns:
            bool: 복구 성공 여부

        Raises:
            RecoveryError: 복구 실패 시
        """
        try:
            count = context.increment(ErrorType.BROWSER)
            logger.warning(
                f"[{count}/1] 브라우저 크래시 감지. 자동 복구 중..."
            )

            # 기존 세션 정리
            try:
                driver.quit()
            except Exception:
                pass

            # 새 WebDriver 초기화 및 재시작
            srt_instance.run_driver()
            srt_instance.login()
            srt_instance.go_search()

            logger.info("[브라우저 복구] 완료. 검색 재개...")
            return True

        except Exception as e:
            context.reset(ErrorType.BROWSER)
            raise RecoveryError(
                f"브라우저 복구 실패: {str(e)}"
            ) from e


# 편의 함수
def is_network_error(exception: Exception) -> bool:
    """네트워크 오류 판정"""
    return NetworkErrorRecovery.should_retry(exception)


def is_session_error(driver: Any) -> bool:
    """세션 만료 판정"""
    return SessionRecovery.is_session_expired(driver)
