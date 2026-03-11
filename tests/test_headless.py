# -*- coding: utf-8 -*-
"""F-12 헤드리스 모드 테스트"""
import os
import sys
from unittest.mock import MagicMock, patch, call

import pytest

from srt_reservation.config import Config
from srt_reservation.util import parse_cli_args
from srt_reservation.main import SRT


# ---------------------------------------------------------------------------
# Config 테스트
# ---------------------------------------------------------------------------

class TestConfigHeadless:
    def test_headless_default_is_false(self):
        """DEFAULTS에 headless=False가 존재해야 한다"""
        assert Config.DEFAULTS['headless'] is False

    def test_headless_in_bool_keys(self):
        """_BOOL_KEYS에 headless가 포함되어야 한다"""
        assert 'headless' in Config._BOOL_KEYS

    def test_headless_in_env_key_map(self):
        """ENV_KEY_MAP에 HEADLESS → headless 매핑이 존재해야 한다"""
        assert Config.ENV_KEY_MAP.get('HEADLESS') == 'headless'

    def test_env_headless_true(self):
        """HEADLESS=true 환경변수가 headless=True로 변환되어야 한다"""
        with patch.dict(os.environ, {'HEADLESS': 'true'}, clear=True):
            result = Config.load_from_env()
        assert result['headless'] is True

    def test_env_headless_false(self):
        """HEADLESS=false 환경변수가 headless=False로 변환되어야 한다"""
        with patch.dict(os.environ, {'HEADLESS': 'false'}, clear=True):
            result = Config.load_from_env()
        assert result['headless'] is False

    def test_env_headless_unset(self):
        """HEADLESS 환경변수가 없으면 config에 포함되지 않아야 한다"""
        with patch.dict(os.environ, {}, clear=True):
            result = Config.load_from_env(env_file='/tmp/_nonexistent_.env')
        assert 'headless' not in result

    def test_merge_headless_from_cli(self):
        """CLI headless=True가 병합 결과에 포함되어야 한다"""
        merged = Config.merge({'headless': True}, {})
        assert merged['headless'] is True

    def test_merge_headless_from_env(self):
        """ENV headless=True가 병합 결과에 포함되어야 한다"""
        merged = Config.merge({}, {'headless': True})
        assert merged['headless'] is True

    def test_merge_cli_overrides_env(self):
        """CLI headless=False가 ENV headless=True를 오버라이드해야 한다"""
        merged = Config.merge({'headless': False}, {'headless': True})
        assert merged['headless'] is False

    def test_merge_defaults_headless_false(self):
        """둘 다 미설정 시 DEFAULTS의 headless=False가 적용되어야 한다"""
        merged = Config.merge({}, {})
        assert merged['headless'] is False


# ---------------------------------------------------------------------------
# CLI 파싱 테스트
# ---------------------------------------------------------------------------

class TestUtilHeadless:
    def _parse(self, args):
        with patch('sys.argv', ['quickstart.py'] + args):
            return parse_cli_args()

    def test_headless_true(self):
        """--headless True 파싱 시 True를 반환해야 한다"""
        args = self._parse(['--headless', 'True', '--dpt', '동탄', '--arr', '동대구', '--dt', '20260315', '--tm', '08'])
        assert args.headless is True

    def test_headless_false(self):
        """--headless False 파싱 시 False를 반환해야 한다"""
        args = self._parse(['--headless', 'False', '--dpt', '동탄', '--arr', '동대구', '--dt', '20260315', '--tm', '08'])
        assert args.headless is False

    def test_headless_not_specified(self):
        """--headless 미지정 시 None을 반환해야 한다"""
        args = self._parse(['--dpt', '동탄', '--arr', '동대구', '--dt', '20260315', '--tm', '08'])
        assert args.headless is None

    def test_headless_lowercase_true(self):
        """--headless true (소문자)도 True로 파싱되어야 한다"""
        args = self._parse(['--headless', 'true'])
        assert args.headless is True

    def test_headless_invalid_value(self):
        """--headless maybe 같이 잘못된 값은 SystemExit을 발생시켜야 한다"""
        with pytest.raises(SystemExit):
            self._parse(['--headless', 'maybe'])


# ---------------------------------------------------------------------------
# SRT 생성자 테스트
# ---------------------------------------------------------------------------

class TestSRTHeadlessInit:
    def test_headless_true_stored(self):
        """headless=True 파라미터가 인스턴스에 저장되어야 한다"""
        srt = SRT("동탄", "동대구", "20260315", "08", headless=True)
        assert srt.headless is True

    def test_headless_false_default(self):
        """headless 기본값은 False여야 한다"""
        srt = SRT("동탄", "동대구", "20260315", "08")
        assert srt.headless is False

    def test_headless_false_explicit(self):
        """headless=False 명시 시 False로 저장되어야 한다"""
        srt = SRT("동탄", "동대구", "20260315", "08", headless=False)
        assert srt.headless is False

    def test_existing_params_unaffected(self):
        """headless 추가 후 기존 파라미터가 정상 동작해야 한다"""
        srt = SRT("동탄", "동대구", "20260315", "08", 2, False)
        assert srt.headless is False
        assert srt.dpt_stn == "동탄"
        assert srt.num_trains_to_check == 2


# ---------------------------------------------------------------------------
# Chrome 옵션 빌드 테스트
# ---------------------------------------------------------------------------

class TestChromeOptionsHeadless:
    def _make_srt(self, headless=False):
        srt = SRT("동탄", "동대구", "20260315", "08", headless=headless)
        return srt

    def test_headless_adds_headless_new_arg(self):
        """headless=True이면 --headless=new 옵션이 추가되어야 한다"""
        srt = self._make_srt(headless=True)
        opts = srt._chrome_options()
        assert any('headless=new' in arg for arg in opts.arguments)

    def test_headless_adds_window_size(self):
        """headless=True이면 --window-size=1920,1080이 추가되어야 한다"""
        srt = self._make_srt(headless=True)
        opts = srt._chrome_options()
        assert any('window-size' in arg for arg in opts.arguments)

    def test_headless_no_detach(self):
        """headless=True이면 detach 옵션이 설정되지 않아야 한다"""
        srt = self._make_srt(headless=True)
        opts = srt._chrome_options()
        exp_opts = opts.experimental_options or {}
        assert exp_opts.get('detach') is not True

    def test_headless_false_has_detach(self):
        """headless=False이면 detach=True가 설정되어야 한다 (for_undetected=False)"""
        srt = self._make_srt(headless=False)
        opts = srt._chrome_options(for_undetected=False)
        assert opts.experimental_options.get('detach') is True

    def test_headless_false_no_headless_arg(self):
        """headless=False이면 --headless=new가 없어야 한다"""
        srt = self._make_srt(headless=False)
        opts = srt._chrome_options()
        assert not any('headless=new' in arg for arg in opts.arguments)


# ---------------------------------------------------------------------------
# undetected-chromedriver headless 파라미터 전달 테스트
# ---------------------------------------------------------------------------

class TestRunDriverUndetectedHeadless:
    def test_uc_chrome_receives_headless_true(self):
        """headless=True이면 uc.Chrome()에 headless=True가 전달되어야 한다"""
        srt = SRT("동탄", "동대구", "20260315", "08", headless=True)

        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd = MagicMock()
        mock_driver.current_url = "about:blank"

        with patch('srt_reservation.main.UNDETECTED_AVAILABLE', True), \
             patch('srt_reservation.main.uc') as mock_uc:
            mock_uc.ChromeOptions.return_value = MagicMock(arguments=[], add_argument=lambda x: None)
            mock_uc.Chrome.return_value = mock_driver
            srt._run_driver_undetected()

        call_kwargs = mock_uc.Chrome.call_args[1]
        assert call_kwargs.get('headless') is True

    def test_uc_chrome_receives_headless_false(self):
        """headless=False이면 uc.Chrome()에 headless=False가 전달되어야 한다"""
        srt = SRT("동탄", "동대구", "20260315", "08", headless=False)

        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd = MagicMock()
        mock_driver.current_url = "about:blank"

        with patch('srt_reservation.main.UNDETECTED_AVAILABLE', True), \
             patch('srt_reservation.main.uc') as mock_uc:
            mock_uc.ChromeOptions.return_value = MagicMock(arguments=[], add_argument=lambda x: None)
            mock_uc.Chrome.return_value = mock_driver
            srt._run_driver_undetected()

        call_kwargs = mock_uc.Chrome.call_args[1]
        assert call_kwargs.get('headless') is False


# ---------------------------------------------------------------------------
# run() 메서드 headless 동작 테스트
# ---------------------------------------------------------------------------

class TestRunMethodHeadless:
    def _make_mock_srt(self, headless):
        srt = SRT("동탄", "동대구", "20260315", "08", headless=headless)
        srt.run_driver = MagicMock()
        srt.set_log_info = MagicMock()
        srt.login = MagicMock()
        srt.check_login = MagicMock(return_value=True)
        srt.go_search = MagicMock()
        srt.check_result = MagicMock()
        srt.notifier = MagicMock()
        srt.close_driver = MagicMock()
        return srt

    def test_headless_true_close_driver_called_on_success(self):
        """headless=True + 예약 성공 시 close_driver()가 호출되어야 한다"""
        srt = self._make_mock_srt(headless=True)
        srt.is_booked = True

        def set_booked():
            srt.is_booked = True

        srt.check_result = MagicMock(side_effect=set_booked)
        srt.run("id", "pw")
        srt.close_driver.assert_called_once()

    def test_headless_false_close_driver_not_called(self):
        """headless=False + 예약 성공 시 close_driver()가 호출되지 않아야 한다"""
        srt = self._make_mock_srt(headless=False)
        srt.is_booked = True
        srt.run("id", "pw")
        srt.close_driver.assert_not_called()

    def test_headless_true_close_driver_called_on_exception(self):
        """headless=True + 예외 발생 시에도 close_driver()가 finally에서 호출되어야 한다"""
        srt = self._make_mock_srt(headless=True)
        srt.check_result = MagicMock(side_effect=RuntimeError("test error"))
        srt.notifier.notify_failure = MagicMock()

        with pytest.raises(RuntimeError):
            srt.run("id", "pw")
        srt.close_driver.assert_called_once()

    def test_headless_false_close_driver_not_called_on_exception(self):
        """headless=False + 예외 발생 시 close_driver()가 호출되지 않아야 한다"""
        srt = self._make_mock_srt(headless=False)
        srt.check_result = MagicMock(side_effect=RuntimeError("test error"))
        srt.notifier.notify_failure = MagicMock()

        with pytest.raises(RuntimeError):
            srt.run("id", "pw")
        srt.close_driver.assert_not_called()
