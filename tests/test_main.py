# -*- coding: utf-8 -*-
"""
SRT 예매 프로그램 테스트 코드
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from selenium.common.exceptions import WebDriverException, NoAlertPresentException

from srt_reservation.main import SRT
from srt_reservation.exceptions import (
    InvalidStationNameError,
    InvalidDateError,
    InvalidDateFormatError,
    InvalidTimeFormatError
)
from srt_reservation.validation import station_list


class TestSRTInputValidation:
    """입력 검증 테스트"""
    
    def test_valid_input(self):
        """유효한 입력값 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08", 2, False)
        assert srt.dpt_stn == "동탄"
        assert srt.arr_stn == "동대구"
        assert srt.dpt_dt == "20240115"
        assert srt.dpt_tm == "08"
        assert srt.num_trains_to_check == 2
        assert srt.want_reserve == False
    
    def test_invalid_departure_station(self):
        """잘못된 출발역 테스트"""
        with pytest.raises(InvalidStationNameError, match="출발역 오류"):
            SRT("잘못된역", "동대구", "20240115", "08")
    
    def test_invalid_arrival_station(self):
        """잘못된 도착역 테스트"""
        with pytest.raises(InvalidStationNameError, match="도착역 오류"):
            SRT("동탄", "잘못된역", "20240115", "08")
    
    def test_same_departure_and_arrival_station(self):
        """출발역과 도착역이 같은 경우 테스트"""
        with pytest.raises(InvalidStationNameError, match="출발역과 도착역이 같을 수 없습니다"):
            SRT("동탄", "동탄", "20240115", "08")
    
    def test_invalid_date_format_non_numeric(self):
        """숫자가 아닌 날짜 형식 테스트"""
        with pytest.raises(InvalidDateFormatError, match="날짜는 숫자로만 이루어져야 합니다"):
            SRT("동탄", "동대구", "2024-01-15", "08")
    
    def test_invalid_date_format_wrong_format(self):
        """잘못된 날짜 형식 테스트"""
        with pytest.raises(InvalidDateError, match="날짜가 잘못 되었습니다"):
            SRT("동탄", "동대구", "20240132", "08")  # 존재하지 않는 날짜
    
    def test_invalid_date_format_short(self):
        """짧은 날짜 형식 테스트"""
        with pytest.raises(InvalidDateError, match="날짜가 잘못 되었습니다"):
            SRT("동탄", "동대구", "2024015", "08")
    
    def test_invalid_time_format_odd_hour(self):
        """홀수 시간 테스트 (짝수 시간만 허용)"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 짝수 시간만 허용됩니다"):
            SRT("동탄", "동대구", "20240115", "09")
    
    def test_invalid_time_format_out_of_range_high(self):
        """범위를 벗어난 시간 테스트 (24 이상)"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 0-23 사이의 값이어야 합니다"):
            SRT("동탄", "동대구", "20240115", "24")
    
    def test_invalid_time_format_out_of_range_low(self):
        """범위를 벗어난 시간 테스트 (음수)"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 0-23 사이의 값이어야 합니다"):
            SRT("동탄", "동대구", "20240115", "-2")
    
    def test_invalid_time_format_non_numeric(self):
        """숫자가 아닌 시간 형식 테스트"""
        with pytest.raises(InvalidTimeFormatError, match="시간은 숫자 형식이어야 합니다"):
            SRT("동탄", "동대구", "20240115", "abc")
    
    def test_valid_even_hours(self):
        """유효한 짝수 시간들 테스트"""
        valid_hours = ["00", "02", "04", "06", "08", "10", "12", "14", "16", "18", "20", "22"]
        for hour in valid_hours:
            srt = SRT("동탄", "동대구", "20240115", hour)
            assert srt.dpt_tm == hour
    
    def test_future_date(self):
        """미래 날짜 테스트"""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        srt = SRT("동탄", "동대구", future_date, "08")
        assert srt.dpt_dt == future_date
    
    def test_all_stations_in_list(self):
        """모든 역이 station_list에 있는지 테스트"""
        for station in station_list:
            # 각 역을 출발역으로 사용할 수 있는지 확인
            arrival = '동대구' if station != '동대구' else '부산'
            srt = SRT(station, arrival, "20240115", "08")
            assert srt.dpt_stn == station


class TestSRTLoginInfo:
    """로그인 정보 검증 테스트"""
    
    def test_set_valid_login_info(self):
        """유효한 로그인 정보 설정 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        srt.set_log_info("test_id", "test_password")
        assert srt.login_id == "test_id"
        assert srt.login_psw == "test_password"
    
    def test_set_empty_login_id(self):
        """빈 로그인 ID 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        with pytest.raises(ValueError, match="로그인 ID와 비밀번호는 필수입니다"):
            srt.set_log_info("", "test_password")
    
    def test_set_empty_login_password(self):
        """빈 로그인 비밀번호 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        with pytest.raises(ValueError, match="로그인 ID와 비밀번호는 필수입니다"):
            srt.set_log_info("test_id", "")
    
    def test_set_none_login_id(self):
        """None 로그인 ID 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        with pytest.raises(ValueError, match="로그인 ID와 비밀번호는 필수입니다"):
            srt.set_log_info(None, "test_password")
    
    def test_set_none_login_password(self):
        """None 로그인 비밀번호 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        with pytest.raises(ValueError, match="로그인 ID와 비밀번호는 필수입니다"):
            srt.set_log_info("test_id", None)


class TestSRTDriver:
    """WebDriver 관련 테스트"""
    
    @patch('srt_reservation.main.Service')
    @patch('srt_reservation.main.webdriver.Chrome')
    def test_run_driver_success(self, mock_chrome, mock_service):
        """WebDriver 초기화 성공 테스트"""
        mock_service_instance = Mock()
        mock_service.return_value = mock_service_instance
        mock_driver_instance = Mock()
        mock_chrome.return_value = mock_driver_instance
        
        srt = SRT("동탄", "동대구", "20240115", "08")
        srt.run_driver()
        
        assert srt.driver == mock_driver_instance
        mock_chrome.assert_called_once()
    
    @patch('srt_reservation.main.Service')
    @patch('srt_reservation.main.webdriver.Chrome')
    @patch('srt_reservation.main.ChromeDriverManager')
    def test_run_driver_fallback_to_manager(self, mock_manager, mock_chrome, mock_service):
        """WebDriver 초기화 실패 시 WebDriver Manager 사용 테스트"""
        mock_service_instance = Mock()
        mock_service.return_value = mock_service_instance
        
        # 첫 번째 시도에서 예외 발생 (WebDriverException)
        fallback_driver = Mock()
        mock_chrome.side_effect = [WebDriverException("Driver not found"), fallback_driver]

        mock_manager_instance = Mock()
        mock_manager_instance.install.return_value = "/path/to/driver"
        mock_manager.return_value = mock_manager_instance

        srt = SRT("동탄", "동대구", "20240115", "08")
        srt.run_driver()

        # WebDriver Manager가 호출되었는지 확인
        assert mock_manager_instance.install.called
        assert srt.driver == fallback_driver
    
    def test_close_driver(self):
        """WebDriver 종료 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        srt.driver = mock_driver
        
        srt.close_driver()
        
        mock_driver.quit.assert_called_once()
    
    def test_close_driver_when_none(self):
        """WebDriver가 None일 때 종료 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        srt.driver = None
        
        # 예외가 발생하지 않아야 함
        srt.close_driver()


class TestSRTAlertHandling:
    """Alert 처리 테스트"""
    
    def test_handle_alert_success(self):
        """Alert 처리 성공 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_alert = Mock()
        mock_alert.text = "Test alert message"
        mock_driver.switch_to.alert = mock_alert
        srt.driver = mock_driver
        
        result = srt.handle_alert()
        
        assert result is True
        mock_alert.accept.assert_called_once()
    
    def test_handle_alert_no_alert(self):
        """Alert가 없을 때 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()

        class SwitchToMock:
            @property
            def alert(self):
                raise NoAlertPresentException()

        mock_driver.switch_to = SwitchToMock()
        srt.driver = mock_driver

        result = srt.handle_alert()

        assert result is False


class TestSRTLogin:
    """로그인 관련 테스트"""
    
    @patch('srt_reservation.main.WebDriverWait')
    @patch('srt_reservation.main.SRT.handle_alert')
    def test_login_success(self, mock_handle_alert, mock_webdriver_wait):
        """로그인 성공 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        srt.set_log_info("test_id", "test_password")
        
        mock_driver = Mock()
        srt.driver = mock_driver

        mock_id_input = Mock()
        mock_pw_input = Mock()
        mock_button = Mock()

        mock_wait_instance = Mock()
        mock_wait_instance.until.side_effect = [mock_id_input, mock_pw_input, mock_button]
        mock_webdriver_wait.return_value = mock_wait_instance

        result = srt.login()

        assert result == mock_driver
        mock_driver.get.assert_called()
        mock_id_input.clear.assert_called_once()
        mock_id_input.send_keys.assert_called_once_with('test_id')
        mock_pw_input.clear.assert_called_once()
        mock_pw_input.send_keys.assert_called_once_with('test_password')
        mock_button.click.assert_called_once()
    
    @patch('srt_reservation.main.WebDriverWait')
    @patch('srt_reservation.main.SRT.handle_alert')
    def test_login_with_alert(self, mock_handle_alert, mock_webdriver_wait):
        """Alert가 있을 때 로그인 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        srt.set_log_info("test_id", "test_password")
        
        mock_driver = Mock()
        from selenium.common.exceptions import UnexpectedAlertPresentException
        mock_driver.get.side_effect = [UnexpectedAlertPresentException(), None]
        srt.driver = mock_driver

        mock_id_input = Mock()
        mock_pw_input = Mock()
        mock_button = Mock()

        mock_wait_instance = Mock()
        mock_wait_instance.until.side_effect = [mock_id_input, mock_pw_input, mock_button]
        mock_webdriver_wait.return_value = mock_wait_instance
        
        srt.login()
        
        # Alert 처리가 호출되었는지 확인
        assert mock_handle_alert.called
        mock_button.click.assert_called_once()


class TestSRTCheckLogin:
    """로그인 확인 테스트"""
    
    def test_check_login_success(self):
        """로그인 확인 성공 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text = "환영합니다 홍길동님"
        mock_driver.find_element.return_value = mock_element
        srt.driver = mock_driver
        
        result = srt.check_login()
        
        assert result is True
    
    def test_check_login_failure(self):
        """로그인 확인 실패 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text = "로그인하세요"
        mock_driver.find_element.return_value = mock_element
        srt.driver = mock_driver
        
        result = srt.check_login()
        
        assert result is False


class TestSRTBookTicket:
    """티켓 예약 테스트"""
    
    def test_book_ticket_available(self):
        """예약 가능한 경우 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        mock_driver.find_elements.return_value = [Mock()]  # 예약 성공 요소 존재
        srt.driver = mock_driver
        
        result = srt.book_ticket("예약하기", 1)
        
        assert result == mock_driver
        assert srt.is_booked is True
    
    def test_book_ticket_unavailable(self):
        """예약 불가능한 경우 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        mock_driver.find_elements.return_value = []  # 예약 성공 요소 없음
        srt.driver = mock_driver
        
        result = srt.book_ticket("예약하기", 1)
        
        assert result is None
        assert srt.is_booked is False
        mock_driver.back.assert_called_once()
    
    def test_book_ticket_sold_out(self):
        """매진인 경우 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        srt.driver = mock_driver
        
        result = srt.book_ticket("매진", 1)
        
        assert result is None
        assert not mock_driver.find_element.called


class TestSRTReserveTicket:
    """예약 대기 테스트"""
    
    def test_reserve_ticket_available(self):
        """예약 대기 가능한 경우 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        srt.driver = mock_driver
        
        result = srt.reserve_ticket("신청하기", 1)
        
        assert result is True
        assert srt.is_booked is True
        mock_driver.find_element.assert_called_once()
    
    def test_reserve_ticket_unavailable(self):
        """예약 대기 불가능한 경우 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        srt.driver = mock_driver
        
        result = srt.reserve_ticket("매진", 1)
        
        assert result is False
        assert not mock_driver.find_element.called


class TestSRTRefreshResult:
    """결과 새로고침 테스트"""
    
    def test_refresh_result(self):
        """새로고침 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08")
        mock_driver = Mock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        srt.driver = mock_driver
        
        initial_count = srt.cnt_refresh
        srt.refresh_result()
        
        assert srt.cnt_refresh == initial_count + 1
        mock_driver.execute_script.assert_called_once()


class TestSRTCheckResult:
    """결과 확인 테스트"""
    
    def test_check_result_with_booking_success(self):
        """예약 성공 시 결과 확인 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08", num_trains_to_check=1)
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text = "예약하기"
        mock_driver.find_element.return_value = mock_element
        mock_driver.find_elements.return_value = [Mock()]  # 예약 성공
        srt.driver = mock_driver
        
        # book_ticket이 성공하도록 설정
        with patch.object(srt, 'book_ticket', return_value=mock_driver):
            result = srt.check_result()
        
        assert result == mock_driver
    
    def test_check_result_refresh_until_error_or_booked(self):
        """예약 불가 시 새로고침을 반복하다가 refresh_result 오류 시 예외 전파 테스트"""
        srt = SRT("동탄", "동대구", "20240115", "08", num_trains_to_check=1)
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text = "매진"
        mock_driver.find_element.return_value = mock_element
        srt.driver = mock_driver

        with patch.object(srt, 'refresh_result', side_effect=Exception("연결 끊김")) as mock_refresh:
            with pytest.raises(Exception, match="연결 끊김"):
                srt.check_result()
        assert mock_refresh.called

