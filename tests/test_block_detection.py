# -*- coding: utf-8 -*-
"""
SRT IP 차단 페이지 감지 테스트.

실제로 한 번 차단을 당한 후 추가한 안전망. 본문 텍스트에 매크로 차단 안내
문구가 두 개 이상 매칭되면 BlockedByServerError 가 raise되어야 한다.
"""
import pytest
from unittest.mock import MagicMock

from srt_reservation.main import SRT
from srt_reservation.exceptions import BlockedByServerError


REAL_BLOCK_PAGE_BODY = (
    "SR SRT 예약발매시스템 접속 제한 안내 "
    "해당 IP는 SRT 예약발매시스템에 비정상적인 접근이 감지되어, "
    "시스템 보안을 위해 접속이 일시적으로 제한되었습니다. "
    "매크로 프로그램 사용은 SR 영업정책에 따라 엄격히 금지되어 있으며, "
    "향후 동일한 행위가 반복될 경우 회원 자격상실 및 이용제한이 될 수 있음을 안내드립니다. "
    "요청 ID: a19afddb5aab "
    "[자동화된 요청으로 감지되어 차단되었습니다.] 확인"
)


def _make_srt_with_body(body_text: str) -> SRT:
    """body.innerText 가 body_text 를 돌려주는 mock driver 를 가진 SRT 인스턴스."""
    srt = SRT("동탄", "동대구", "20260601", "08", 2, False)
    srt.driver = MagicMock()
    srt.driver.execute_script.return_value = body_text
    # notifier 도 mock 으로 (실제 텔레그램 발송 방지)
    srt.notifier = MagicMock()
    srt.notifier.is_configured.return_value = False
    return srt


class TestDetectBlockedPage:
    """차단 페이지 감지 동작"""

    def test_real_block_page_raises(self):
        """실제 캡쳐한 차단 페이지 본문에서 BlockedByServerError 발생"""
        srt = _make_srt_with_body(REAL_BLOCK_PAGE_BODY)
        with pytest.raises(BlockedByServerError) as exc_info:
            srt._detect_blocked_page()
        # 요청 ID 추출 확인
        assert exc_info.value.request_id == "a19afddb5aab"
        # 두 개 이상 시그너처 매칭
        assert len(exc_info.value.matched_signatures) >= 2

    def test_normal_search_result_does_not_raise(self):
        """정상 검색 결과 페이지는 raise 하지 않음"""
        normal = (
            "잔여석조회결과 출발 도착 일반석 특실 "
            "수서→부산 14:00→16:42 예약하기 예약하기 매진 매진"
        )
        srt = _make_srt_with_body(normal)
        # 예외 없이 정상 종료해야 함
        srt._detect_blocked_page()

    def test_single_signature_does_not_raise(self):
        """오탐 방지: 단일 시그너처만 있는 경우 raise 안 함 (예: 공지사항 텍스트)"""
        body = "공지: 일부 시간대에 접속 제한이 있을 수 있습니다."  # '접속 제한' 1개만
        srt = _make_srt_with_body(body)
        srt._detect_blocked_page()

    def test_two_signatures_triggers_block(self):
        """경계 조건: 정확히 2개 시그너처 매칭되면 raise"""
        body = "비정상적인 접근이 감지되었습니다. 매크로 프로그램 사용 금지."
        srt = _make_srt_with_body(body)
        with pytest.raises(BlockedByServerError):
            srt._detect_blocked_page()

    def test_empty_body_does_not_raise(self):
        """body 가 비어있어도 안전하게 통과"""
        srt = _make_srt_with_body("")
        srt._detect_blocked_page()

    def test_driver_error_swallowed(self):
        """execute_script 가 예외를 던져도 검사 자체는 통과 (검색 흐름 보호)"""
        srt = SRT("동탄", "동대구", "20260601", "08", 2, False)
        srt.driver = MagicMock()
        srt.driver.execute_script.side_effect = Exception("driver crash")
        srt.notifier = MagicMock()
        # 예외 안 던지고 None 리턴
        srt._detect_blocked_page()

    def test_no_request_id_uses_unknown(self):
        """요청 ID 가 본문에 없을 때 'unknown' 으로 채워짐"""
        body = "접속 제한 안내. 비정상적인 접근이 감지되었습니다. 매크로 프로그램 사용은 금지."
        srt = _make_srt_with_body(body)
        with pytest.raises(BlockedByServerError) as exc_info:
            srt._detect_blocked_page()
        assert exc_info.value.request_id == "unknown"


class TestBlockNotification:
    """차단 감지 시 텔레그램 알림 발송"""

    def test_sends_telegram_when_configured(self):
        srt = _make_srt_with_body(REAL_BLOCK_PAGE_BODY)
        srt.notifier.is_configured.return_value = True
        with pytest.raises(BlockedByServerError):
            srt._detect_blocked_page()
        srt.notifier.send_message.assert_called_once()
        sent_msg = srt.notifier.send_message.call_args[0][0]
        assert "SRT IP 차단" in sent_msg
        assert "a19afddb5aab" in sent_msg

    def test_skips_telegram_when_not_configured(self):
        srt = _make_srt_with_body(REAL_BLOCK_PAGE_BODY)
        srt.notifier.is_configured.return_value = False
        with pytest.raises(BlockedByServerError):
            srt._detect_blocked_page()
        srt.notifier.send_message.assert_not_called()
