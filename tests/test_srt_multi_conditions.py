# -*- coding: utf-8 -*-
"""다중 검색 조건 통합 테스트"""
import pytest
from unittest.mock import Mock, patch, call

from srt_reservation.main import SRT
from srt_reservation.exceptions import InvalidDateError, InvalidDateFormatError, InvalidTimeFormatError


class TestSRTInitMultiConditions:
    """__init__ 다중 조건 속성 초기화 테스트"""

    def test_multi_conditions_attributes(self):
        """다중 조건 속성 설정 -- dpt_dates, dpt_times, search_conditions"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08,10")
        assert srt.dpt_dates == ["20260315", "20260316"]
        assert srt.dpt_times == ["08", "10"]
        assert len(srt.search_conditions) == 4

    def test_single_value_backward_compat_attributes(self):
        """하위 호환 -- 단일값 입력 시 dpt_dt, dpt_tm 속성 유지"""
        srt = SRT("동탄", "동대구", "20260315", "08")
        assert srt.dpt_dates == ["20260315"]
        assert srt.dpt_times == ["08"]
        assert srt.dpt_dt == "20260315"
        assert srt.dpt_tm == "08"
        assert len(srt.search_conditions) == 1

    def test_existing_test_pattern_backward_compat(self):
        """하위 호환 -- 기존 테스트 패턴"""
        srt = SRT("동탄", "동대구", "20240115", "08", 2, False)
        assert srt.dpt_stn == "동탄"
        assert srt.dpt_dt == "20240115"
        assert srt.dpt_tm == "08"

    def test_empty_date_raises_value_error(self):
        """빈 날짜 입력 시 ValueError 발생"""
        with pytest.raises(ValueError, match="날짜를 1개 이상 입력해주세요"):
            SRT("동탄", "동대구", "", "08")

    def test_empty_time_raises_value_error(self):
        """빈 시간 입력 시 ValueError 발생"""
        with pytest.raises(ValueError, match="시간을 1개 이상 입력해주세요"):
            SRT("동탄", "동대구", "20260315", "")


class TestSRTCheckInputMulti:
    """check_input() 다중 날짜/시간 검증 테스트"""

    def test_multi_valid_dates(self):
        """다중 유효 날짜 -- 예외 없음"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08")
        # 예외가 발생하지 않으면 통과

    def test_multi_valid_times(self):
        """다중 유효 시간 -- 예외 없음"""
        srt = SRT("동탄", "동대구", "20260315", "08,10,12")
        # 예외가 발생하지 않으면 통과

    def test_first_date_invalid_length(self):
        """첫 번째 날짜 길이 오류"""
        with pytest.raises(InvalidDateError, match="날짜가 잘못 되었습니다"):
            SRT("동탄", "동대구", "2026031,20260316", "08")

    def test_second_date_invalid_calendar(self):
        """두 번째 날짜 존재하지 않는 날짜"""
        with pytest.raises(InvalidDateError, match="날짜가 잘못 되었습니다"):
            SRT("동탄", "동대구", "20260315,20260230", "08")

    def test_date_with_hyphen_format_error(self):
        """날짜에 하이픈 포함 -- 비숫자 오류"""
        with pytest.raises(InvalidDateFormatError, match="날짜는 숫자로만 이루어져야 합니다"):
            SRT("동탄", "동대구", "20260315,2026-03-16", "08")

    def test_odd_hour_in_multi_times(self):
        """홀수 시간 포함 -- 짝수 시간만 허용"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 짝수 시간만 허용됩니다"):
            SRT("동탄", "동대구", "20260315", "08,09")

    def test_out_of_range_hour_in_multi_times(self):
        """범위 초과 시간 포함"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 0-23 사이의 값이어야 합니다"):
            SRT("동탄", "동대구", "20260315", "08,24")

    def test_non_numeric_hour_in_multi_times(self):
        """비숫자 시간 포함"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 숫자 형식이어야 합니다"):
            SRT("동탄", "동대구", "20260315", "08,ab")


class TestGoSearchMulti:
    """go_search() 다중 조건 인자 전달 테스트"""

    def _make_mock_driver(self):
        mock_driver = Mock()
        mock_element = Mock()
        mock_select_element = Mock()
        mock_select_element.options = []
        mock_driver.find_element.return_value = mock_element
        return mock_driver

    @patch('srt_reservation.main.WebDriverWait')
    @patch('srt_reservation.main.Select')
    def test_go_search_with_specific_args(self, mock_select_cls, mock_wait_cls):
        """날짜/시간 인자 전달 시 해당 값으로 조회"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08,10")
        srt.driver = self._make_mock_driver()

        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = Mock()
        mock_wait_cls.return_value = mock_wait_instance

        mock_select_instance = Mock()
        mock_select_instance.options = []
        mock_select_cls.return_value = mock_select_instance

        srt.go_search(dpt_dt="20260316", dpt_tm="10")

        # select_by_value("20260316") 호출 확인
        mock_select_instance.select_by_value.assert_called_once_with("20260316")

    @patch('srt_reservation.main.WebDriverWait')
    @patch('srt_reservation.main.Select')
    def test_go_search_no_args_uses_defaults(self, mock_select_cls, mock_wait_cls):
        """인자 없이 호출 시 self.dpt_dt, self.dpt_tm 사용 (하위 호환)"""
        srt = SRT("동탄", "동대구", "20260315", "08")
        srt.driver = self._make_mock_driver()

        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = Mock()
        mock_wait_cls.return_value = mock_wait_instance

        mock_select_instance = Mock()
        mock_select_instance.options = []
        mock_select_cls.return_value = mock_select_instance

        srt.go_search()

        mock_select_instance.select_by_value.assert_called_once_with("20260315")


class TestCheckResultMulti:
    """check_result() 다중 조건 순회 테스트"""

    def test_first_condition_booking_success(self):
        """첫 번째 조건에서 예약 성공 -- go_search 1회, _check_result_once 1회"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08,10")
        mock_driver = Mock()
        srt.driver = mock_driver

        with patch.object(srt, 'go_search') as mock_go_search:
            with patch.object(srt, 'book_ticket', return_value=mock_driver):
                with patch.object(srt, '_check_result_once', return_value=mock_driver) as mock_once:
                    result = srt.check_result()

        assert result == mock_driver
        assert mock_go_search.call_count == 1
        assert mock_once.call_count == 1
        assert srt._booked_condition == {"dpt_dt": "20260315", "dpt_tm": "08"}

    def test_second_condition_booking_success(self):
        """두 번째 조건에서 예약 성공 -- go_search 2회, _check_result_once 2회"""
        srt = SRT("동탄", "동대구", "20260315,20260316", "08")
        mock_driver = Mock()
        srt.driver = mock_driver

        # 첫 번째 None (매진), 두 번째 성공
        with patch.object(srt, 'go_search') as mock_go_search:
            with patch.object(srt, '_check_result_once', side_effect=[None, mock_driver]) as mock_once:
                result = srt.check_result()

        assert result == mock_driver
        assert mock_go_search.call_count == 2
        assert mock_once.call_count == 2
        assert srt._booked_condition == {"dpt_dt": "20260316", "dpt_tm": "08"}

    @patch('srt_reservation.main.time.sleep')
    @patch('srt_reservation.main.randint', return_value=5)
    def test_all_conditions_miss_then_retry(self, mock_randint, mock_sleep):
        """모든 조건 매진 후 대기 및 재시도 -- go_search 4회 (3+1)"""
        srt = SRT("동탄", "동대구", "20260315,20260316,20260317", "08")
        mock_driver = Mock()
        srt.driver = mock_driver

        # 1라운드 3개 조건 모두 None, 2라운드 첫 번째 성공
        side_effects = [None, None, None, mock_driver]
        with patch.object(srt, 'go_search') as mock_go_search:
            with patch.object(srt, '_check_result_once', side_effect=side_effects):
                result = srt.check_result()

        assert result == mock_driver
        assert mock_go_search.call_count == 4
        mock_sleep.assert_called_once_with(5)
        assert srt.cnt_refresh == 1
