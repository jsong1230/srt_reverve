# -*- coding: utf-8 -*-
"""_normalize_to_list() 단위 테스트"""
import pytest

from srt_reservation.main import SRT


class TestNormalizeToList:
    """SRT._normalize_to_list() 단위 테스트"""

    def test_comma_separated_string(self):
        """쉼표 구분 문자열 파싱"""
        result = SRT._normalize_to_list("20260315,20260316")
        assert result == ["20260315", "20260316"]

    def test_single_string(self):
        """단일 문자열 처리"""
        result = SRT._normalize_to_list("20260315")
        assert result == ["20260315"]

    def test_list_input(self):
        """리스트 입력 그대로 반환"""
        result = SRT._normalize_to_list(["20260315", "20260316"])
        assert result == ["20260315", "20260316"]

    def test_whitespace_stripped(self):
        """공백 포함 쉼표 구분 -- strip 적용"""
        result = SRT._normalize_to_list("20260315, 20260316")
        assert result == ["20260315", "20260316"]

    def test_empty_items_filtered(self):
        """빈 항목 필터링"""
        result = SRT._normalize_to_list("20260315,,20260316")
        assert result == ["20260315", "20260316"]

    def test_single_item_list(self):
        """단일 항목 리스트 입력"""
        result = SRT._normalize_to_list(["08"])
        assert result == ["08"]

    def test_empty_string_returns_empty_list(self):
        """빈 문자열은 빈 리스트 반환"""
        result = SRT._normalize_to_list("")
        assert result == []

    def test_only_commas_returns_empty_list(self):
        """쉼표만 있으면 빈 리스트 반환"""
        result = SRT._normalize_to_list(",,,")
        assert result == []
