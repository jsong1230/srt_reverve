# -*- coding: utf-8 -*-
"""
예외 클래스 테스트 코드
"""
import pytest
from srt_reservation.exceptions import (
    InvalidStationNameError,
    InvalidDateError,
    InvalidDateFormatError,
    InvalidTimeFormatError
)


class TestExceptions:
    """예외 클래스 테스트"""
    
    def test_invalid_station_name_error(self):
        """InvalidStationNameError 테스트"""
        error = InvalidStationNameError("테스트 오류")
        assert isinstance(error, Exception)
        assert str(error) == "테스트 오류"
    
    def test_invalid_date_error(self):
        """InvalidDateError 테스트"""
        error = InvalidDateError("날짜 오류")
        assert isinstance(error, Exception)
        assert str(error) == "날짜 오류"
    
    def test_invalid_date_format_error(self):
        """InvalidDateFormatError 테스트"""
        error = InvalidDateFormatError("날짜 형식 오류")
        assert isinstance(error, Exception)
        assert str(error) == "날짜 형식 오류"
    
    def test_invalid_time_format_error(self):
        """InvalidTimeFormatError 테스트"""
        error = InvalidTimeFormatError("시간 형식 오류")
        assert isinstance(error, Exception)
        assert str(error) == "시간 형식 오류"
    
    def test_exception_inheritance(self):
        """예외 클래스가 Exception을 상속하는지 테스트"""
        assert issubclass(InvalidStationNameError, Exception)
        assert issubclass(InvalidDateError, Exception)
        assert issubclass(InvalidDateFormatError, Exception)
        assert issubclass(InvalidTimeFormatError, Exception)

