# -*- coding: utf-8 -*-
"""다중 검색 조건 도입 후 기존 단일 조건 회귀 테스트"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from srt_reservation.main import SRT
from srt_reservation.exceptions import (
    InvalidStationNameError,
    InvalidDateError,
    InvalidDateFormatError,
    InvalidTimeFormatError,
)


class TestSRTSingleConditionRegression:
    """기존 단일 --dt, --tm 입력이 새 코드에서도 동작하는지 회귀 테스트"""

    def test_single_dt_tm_still_works(self):
        """단일 dt/tm 입력 시 기존 동작 유지"""
        srt = SRT("동탄", "동대구", "20240115", "08", 2, False)
        assert srt.dpt_stn == "동탄"
        assert srt.arr_stn == "동대구"
        assert srt.dpt_dt == "20240115"
        assert srt.dpt_tm == "08"
        assert srt.num_trains_to_check == 2
        assert srt.want_reserve is False

    def test_single_condition_generates_one_search_condition(self):
        """단일 조건은 search_conditions가 1개"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        assert len(srt.search_conditions) == 1
        assert srt.search_conditions[0] == {"dpt_dt": "20240115", "dpt_tm": "08"}

    def test_existing_validation_still_raises_invalid_station(self):
        """기존 역 검증 로직 동작 유지"""
        with pytest.raises(InvalidStationNameError, match="출발역 오류"):
            SRT("잘못된역", "동대구", "20240115", "08")

    def test_existing_validation_still_raises_invalid_date(self):
        """기존 날짜 검증 로직 동작 유지"""
        with pytest.raises(InvalidDateFormatError, match="날짜는 숫자로만 이루어져야 합니다"):
            SRT("동탄", "동대구", "2024-01-15", "08")

    def test_existing_validation_still_raises_invalid_time(self):
        """기존 시간 검증 로직 동작 유지"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 짝수 시간만 허용됩니다"):
            SRT("동탄", "동대구", "20240115", "09")

    def test_check_result_single_condition_calls_go_search_once(self):
        """단일 조건 check_result -- go_search 1회 호출"""
        srt = SRT("동탄", "동대구", "20240115", "08", num_trains_to_check=1)
        mock_driver = Mock()
        srt.driver = mock_driver

        with patch.object(srt, 'go_search') as mock_go_search:
            with patch.object(srt, '_check_result_once', return_value=mock_driver):
                result = srt.check_result()

        assert result == mock_driver
        mock_go_search.assert_called_once_with(dpt_dt="20240115", dpt_tm="08")

    def test_all_valid_even_hours_single_condition(self):
        """유효한 짝수 시간들 단일 조건으로 테스트"""
        valid_hours = ["00", "02", "04", "06", "08", "10", "12", "14", "16", "18", "20", "22"]
        for hour in valid_hours:
            srt = SRT("동탄", "동대구", "20240115", hour)
            assert srt.dpt_tm == hour
            assert srt.dpt_times == [hour]
