# -*- coding: utf-8 -*-
"""generate_search_conditions() 단위 테스트"""
import pytest

from srt_reservation.main import SRT


class TestGenerateSearchConditions:
    """SRT.generate_search_conditions() 단위 테스트"""

    def test_two_dates_two_times_cartesian(self):
        """2 날짜 × 2 시간 = 4개 조건 카테시안 곱"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08,10")
        conditions = srt.generate_search_conditions()
        assert conditions == [
            {"dpt_dt": "20260315", "dpt_tm": "08"},
            {"dpt_dt": "20260315", "dpt_tm": "10"},
            {"dpt_dt": "20260316", "dpt_tm": "08"},
            {"dpt_dt": "20260316", "dpt_tm": "10"},
        ]

    def test_single_date_single_time(self):
        """1 날짜 × 1 시간 = 1개 조건 (하위 호환)"""
        srt = SRT("동탄", "동대구", "20260315", "08")
        conditions = srt.generate_search_conditions()
        assert conditions == [{"dpt_dt": "20260315", "dpt_tm": "08"}]

    def test_three_dates_one_time(self):
        """3 날짜 × 1 시간 = 3개 조건"""
        srt = SRT("동탄", "동대구", "20260315,20260316,20260317", "10")
        conditions = srt.generate_search_conditions()
        assert conditions == [
            {"dpt_dt": "20260315", "dpt_tm": "10"},
            {"dpt_dt": "20260316", "dpt_tm": "10"},
            {"dpt_dt": "20260317", "dpt_tm": "10"},
        ]

    def test_one_date_three_times(self):
        """1 날짜 × 3 시간 = 3개 조건"""
        srt = SRT("동탄", "동대구", "20260315", "08,10,12")
        conditions = srt.generate_search_conditions()
        assert conditions == [
            {"dpt_dt": "20260315", "dpt_tm": "08"},
            {"dpt_dt": "20260315", "dpt_tm": "10"},
            {"dpt_dt": "20260315", "dpt_tm": "12"},
        ]

    def test_order_date_first(self):
        """순서 보장 -- 날짜 우선 (입력 순서 유지)"""
        srt = SRT("동탄", "동대구", "20260316,20260315", "10,08")
        conditions = srt.generate_search_conditions()
        assert conditions == [
            {"dpt_dt": "20260316", "dpt_tm": "10"},
            {"dpt_dt": "20260316", "dpt_tm": "08"},
            {"dpt_dt": "20260315", "dpt_tm": "10"},
            {"dpt_dt": "20260315", "dpt_tm": "08"},
        ]

    def test_search_conditions_count_matches_cartesian(self):
        """search_conditions 길이가 날짜×시간 수와 일치"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08,10")
        assert len(srt.search_conditions) == 4
