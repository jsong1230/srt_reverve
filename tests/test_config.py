"""Config 클래스 단위 테스트"""

import argparse
import os
from unittest.mock import patch

import pytest

from srt_reservation.config import Config


# ---------------------------------------------------------------------------
# load_from_env 테스트
# ---------------------------------------------------------------------------

class TestLoadFromEnv:
    def test_empty_env_returns_empty_dict(self):
        """환경변수 미설정 시 빈 딕셔너리 반환"""
        with patch.dict(os.environ, {}, clear=True):
            result = Config.load_from_env(env_file='/tmp/_nonexistent_test_.env')
        assert result == {}

    def test_loads_user_and_password(self):
        """SRT_USER, SRT_PASSWORD 정상 로드"""
        env = {'SRT_USER': 'myid', 'SRT_PASSWORD': 'mypw'}
        with patch.dict(os.environ, env, clear=True):
            result = Config.load_from_env()
        assert result['user'] == 'myid'
        assert result['psw'] == 'mypw'

    def test_loads_route_info(self):
        """SRT_DPT, SRT_ARR, SRT_DT, SRT_TM 정상 로드"""
        env = {'SRT_DPT': '동탄', 'SRT_ARR': '동대구', 'SRT_DT': '20240315', 'SRT_TM': '08'}
        with patch.dict(os.environ, env, clear=True):
            result = Config.load_from_env()
        assert result['dpt'] == '동탄'
        assert result['arr'] == '동대구'
        assert result['dt'] == '20240315'
        assert result['tm'] == '08'

    def test_int_conversion_num(self):
        """SRT_NUM 정수 변환"""
        with patch.dict(os.environ, {'SRT_NUM': '5'}, clear=True):
            result = Config.load_from_env()
        assert result['num'] == 5
        assert isinstance(result['num'], int)

    def test_int_conversion_delay_min(self):
        """RETRY_DELAY_MIN 정수 변환"""
        with patch.dict(os.environ, {'RETRY_DELAY_MIN': '30'}, clear=True):
            result = Config.load_from_env()
        assert result['delay_min'] == 30
        assert isinstance(result['delay_min'], int)

    def test_int_conversion_delay_max(self):
        """RETRY_DELAY_MAX 정수 변환"""
        with patch.dict(os.environ, {'RETRY_DELAY_MAX': '90'}, clear=True):
            result = Config.load_from_env()
        assert result['delay_max'] == 90

    def test_bool_conversion_reserve_true(self):
        """SRT_RESERVE=True 불리언 변환"""
        with patch.dict(os.environ, {'SRT_RESERVE': 'True'}, clear=True):
            result = Config.load_from_env()
        assert result['reserve'] is True

    def test_bool_conversion_reserve_false(self):
        """SRT_RESERVE=False 불리언 변환"""
        with patch.dict(os.environ, {'SRT_RESERVE': 'False'}, clear=True):
            result = Config.load_from_env()
        assert result['reserve'] is False

    def test_bool_conversion_reserve_1(self):
        """SRT_RESERVE=1 불리언 변환"""
        with patch.dict(os.environ, {'SRT_RESERVE': '1'}, clear=True):
            result = Config.load_from_env()
        assert result['reserve'] is True

    def test_bool_conversion_reserve_0(self):
        """SRT_RESERVE=0 불리언 변환"""
        with patch.dict(os.environ, {'SRT_RESERVE': '0'}, clear=True):
            result = Config.load_from_env()
        assert result['reserve'] is False

    def test_anti_bot_method_loaded(self):
        """ANTI_BOT_METHOD 정상 로드"""
        with patch.dict(os.environ, {'ANTI_BOT_METHOD': 'stealth'}, clear=True):
            result = Config.load_from_env()
        assert result['anti_bot'] == 'stealth'

    def test_partial_env_only_set_keys(self):
        """일부 환경변수만 설정 시 해당 키만 포함"""
        env = {'SRT_USER': 'user1', 'SRT_DPT': '수서'}
        with patch.dict(os.environ, env, clear=True):
            result = Config.load_from_env(env_file='/tmp/_nonexistent_test_.env')
        assert 'user' in result
        assert 'dpt' in result
        assert 'psw' not in result
        assert 'arr' not in result

    def test_unknown_env_keys_ignored(self):
        """매핑에 없는 환경변수는 무시됨"""
        with patch.dict(os.environ, {'UNKNOWN_KEY': 'value'}, clear=True):
            result = Config.load_from_env()
        assert 'UNKNOWN_KEY' not in result
        assert 'unknown_key' not in result


# ---------------------------------------------------------------------------
# load_from_cli 테스트
# ---------------------------------------------------------------------------

class TestLoadFromCli:
    def _make_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            'user': None, 'psw': None, 'dpt': None, 'arr': None,
            'dt': None, 'tm': None, 'num': None, 'reserve': None,
            'anti_bot': None, 'delay_min': None, 'delay_max': None,
            'use_profile': None, 'profile_dir': None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_none_values_excluded(self):
        """None 값은 결과에서 제외"""
        args = self._make_args(user=None, psw=None)
        result = Config.load_from_cli(args)
        assert 'user' not in result
        assert 'psw' not in result

    def test_provided_values_included(self):
        """지정된 값은 결과에 포함"""
        args = self._make_args(user='myid', dpt='동탄')
        result = Config.load_from_cli(args)
        assert result['user'] == 'myid'
        assert result['dpt'] == '동탄'

    def test_mixed_none_and_values(self):
        """None과 값이 섞인 경우 정확히 필터링"""
        args = self._make_args(user='id1', psw=None, dpt='수서', arr=None)
        result = Config.load_from_cli(args)
        assert 'user' in result
        assert 'dpt' in result
        assert 'psw' not in result
        assert 'arr' not in result

    def test_bool_false_not_excluded(self):
        """False 값은 None이 아니므로 포함됨"""
        args = self._make_args(reserve=False)
        result = Config.load_from_cli(args)
        assert 'reserve' in result
        assert result['reserve'] is False

    def test_int_zero_not_excluded(self):
        """0 값은 None이 아니므로 포함됨"""
        args = self._make_args(num=0)
        result = Config.load_from_cli(args)
        assert 'num' in result
        assert result['num'] == 0

    def test_empty_args_returns_empty_dict(self):
        """모든 값이 None이면 빈 딕셔너리 반환"""
        args = self._make_args()
        result = Config.load_from_cli(args)
        assert result == {}


# ---------------------------------------------------------------------------
# merge 테스트
# ---------------------------------------------------------------------------

class TestMerge:
    def test_defaults_applied_when_empty(self):
        """CLI, ENV 모두 비었을 때 DEFAULTS 적용"""
        result = Config.merge({}, {})
        assert result['num'] == Config.DEFAULTS['num']
        assert result['anti_bot'] == Config.DEFAULTS['anti_bot']
        assert result['reserve'] == Config.DEFAULTS['reserve']

    def test_env_overrides_defaults(self):
        """ENV가 DEFAULTS를 덮어씀"""
        env_config = {'num': 5, 'anti_bot': 'stealth'}
        result = Config.merge({}, env_config)
        assert result['num'] == 5
        assert result['anti_bot'] == 'stealth'

    def test_cli_overrides_env(self):
        """CLI가 ENV를 덮어씀"""
        cli_config = {'num': 3}
        env_config = {'num': 5}
        result = Config.merge(cli_config, env_config)
        assert result['num'] == 3

    def test_cli_overrides_defaults(self):
        """CLI가 DEFAULTS를 덮어씀"""
        cli_config = {'anti_bot': 'enhanced'}
        result = Config.merge(cli_config, {})
        assert result['anti_bot'] == 'enhanced'

    def test_full_priority_chain(self):
        """CLI > ENV > DEFAULTS 우선순위 체인 전체 검증"""
        cli_config = {'user': 'cli_user', 'num': 1}
        env_config = {'user': 'env_user', 'num': 2, 'dpt': 'env_dpt'}
        result = Config.merge(cli_config, env_config)
        # CLI 우선
        assert result['user'] == 'cli_user'
        assert result['num'] == 1
        # ENV 폴백
        assert result['dpt'] == 'env_dpt'
        # DEFAULTS 폴백
        assert result['reserve'] == Config.DEFAULTS['reserve']

    def test_merge_does_not_mutate_inputs(self):
        """merge는 입력 딕셔너리를 수정하지 않음"""
        cli_config = {'user': 'id'}
        env_config = {'anti_bot': 'stealth'}
        cli_copy = cli_config.copy()
        env_copy = env_config.copy()
        Config.merge(cli_config, env_config)
        assert cli_config == cli_copy
        assert env_config == env_copy


# ---------------------------------------------------------------------------
# validate_required 테스트
# ---------------------------------------------------------------------------

class TestValidateRequired:
    def _full_config(self) -> dict:
        return {
            'user': 'myid',
            'psw': 'mypw',
            'dpt': '동탄',
            'arr': '동대구',
            'dt': '20240315',
            'tm': '08',
            'num': 2,
            'reserve': False,
        }

    def test_valid_config_returns_true(self):
        """필수값 모두 존재 시 True 반환"""
        assert Config.validate_required(self._full_config()) is True

    def test_missing_user_raises(self):
        """user 누락 시 ValueError 발생"""
        config = self._full_config()
        del config['user']
        with pytest.raises(ValueError, match='user'):
            Config.validate_required(config)

    def test_missing_psw_raises(self):
        """psw 누락 시 ValueError 발생"""
        config = self._full_config()
        del config['psw']
        with pytest.raises(ValueError, match='psw'):
            Config.validate_required(config)

    def test_missing_dpt_raises(self):
        """dpt 누락 시 ValueError 발생"""
        config = self._full_config()
        del config['dpt']
        with pytest.raises(ValueError, match='dpt'):
            Config.validate_required(config)

    def test_missing_arr_raises(self):
        """arr 누락 시 ValueError 발생"""
        config = self._full_config()
        del config['arr']
        with pytest.raises(ValueError, match='arr'):
            Config.validate_required(config)

    def test_missing_dt_raises(self):
        """dt 누락 시 ValueError 발생"""
        config = self._full_config()
        del config['dt']
        with pytest.raises(ValueError, match='dt'):
            Config.validate_required(config)

    def test_missing_tm_raises(self):
        """tm 누락 시 ValueError 발생"""
        config = self._full_config()
        del config['tm']
        with pytest.raises(ValueError, match='tm'):
            Config.validate_required(config)

    def test_none_value_treated_as_missing(self):
        """None 값은 누락으로 처리"""
        config = self._full_config()
        config['user'] = None
        with pytest.raises(ValueError):
            Config.validate_required(config)

    def test_multiple_missing_keys_in_message(self):
        """여러 필수값 누락 시 에러 메시지에 모두 포함"""
        config = {'num': 2}
        with pytest.raises(ValueError) as exc_info:
            Config.validate_required(config)
        msg = str(exc_info.value)
        for key in Config.REQUIRED_KEYS:
            assert key in msg

    def test_error_message_contains_hint(self):
        """에러 메시지에 .env 힌트 포함"""
        with pytest.raises(ValueError) as exc_info:
            Config.validate_required({})
        assert '.env' in str(exc_info.value)
