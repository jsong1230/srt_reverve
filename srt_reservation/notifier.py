# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import urllib.error
import json
import logging
import os

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram Bot API를 통한 알림 발송 클래스.

    환경변수 TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 설정 시 활성화됩니다.
    발송 실패 시에도 예외를 전파하지 않으므로 예약 프로세스에 영향을 주지 않습니다.
    """

    def __init__(self) -> None:
        self.token: str | None = os.environ.get("TELEGRAM_TOKEN")
        self.chat_id: str | None = os.environ.get("TELEGRAM_CHAT_ID")

    def is_configured(self) -> bool:
        """Telegram 설정 여부 확인 (token, chat_id 모두 있어야 True)"""
        return bool(self.token and self.chat_id)

    def send_message(self, message: str) -> bool:
        """Telegram Bot API로 메시지 발송.

        실패해도 예약 프로세스에 영향 없음 (예외 미전파).

        :param message: 발송할 텍스트 메시지
        :return: 발송 성공 여부
        """
        if not self.is_configured():
            logger.debug("[Telegram] 미설정 상태 — 메시지 발송 생략")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = urllib.parse.urlencode(
                {
                    "chat_id": self.chat_id,
                    "text": message,
                }
            ).encode("utf-8")

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    logger.debug("[Telegram] 메시지 발송 성공")
                    return True

            logger.warning("[Telegram] API 응답 오류")
            return False

        except urllib.error.HTTPError as e:
            logger.warning(f"[Telegram] HTTP 오류: {e.code} {e.reason}")
            return False
        except urllib.error.URLError as e:
            logger.warning(f"[Telegram] URL 오류: {e.reason}")
            return False
        except Exception as e:
            logger.warning(f"[Telegram] 메시지 발송 실패: {str(e)}")
            return False

    def notify_success(self, train_info: dict) -> bool:
        """예약 성공 알림 발송.

        :param train_info: 열차 정보 dict.
                           키: dept_time, arri_time, seat_type
        :return: 발송 성공 여부
        """
        dept_time = train_info.get("dept_time", "N/A")
        arri_time = train_info.get("arri_time", "N/A")
        seat_type = train_info.get("seat_type", "일반석")
        message = (
            f"예약 성공!\n"
            f"- 열차: {dept_time}~{arri_time}\n"
            f"- 좌석: {seat_type}"
        )
        return self.send_message(message)

    def notify_failure(self, reason: str = "최대 재시도 초과") -> bool:
        """예약 실패 알림 발송.

        실패해도 예외를 전파하지 않습니다.

        :param reason: 실패 사유
        :return: 발송 성공 여부
        """
        try:
            message = f"예약 실패: {reason}"
            return self.send_message(message)
        except Exception as e:
            logger.warning(f"[Telegram] notify_failure 처리 중 오류: {str(e)}")
            return False
