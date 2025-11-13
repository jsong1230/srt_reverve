# -*- coding: utf-8 -*-
"""
검증 관련 테스트 코드
"""
import pytest
from srt_reservation.validation import station_list


class TestStationList:
    """역 목록 테스트"""
    
    def test_station_list_not_empty(self):
        """역 목록이 비어있지 않은지 테스트"""
        assert len(station_list) > 0
    
    def test_station_list_contains_major_stations(self):
        """주요 역들이 목록에 포함되어 있는지 테스트"""
        major_stations = ["수서", "동탄", "대전", "동대구", "부산"]
        for station in major_stations:
            assert station in station_list, f"{station}이(가) 목록에 없습니다"
    
    def test_station_list_all_strings(self):
        """모든 역 이름이 문자열인지 테스트"""
        for station in station_list:
            assert isinstance(station, str), f"{station}이(가) 문자열이 아닙니다"
    
    def test_station_list_no_duplicates(self):
        """역 목록에 중복이 없는지 테스트"""
        assert len(station_list) == len(set(station_list)), "역 목록에 중복이 있습니다"

