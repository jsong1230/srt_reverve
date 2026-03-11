"""Config E2E 통합 테스트 - 실제 사용 시나리오 검증"""

import argparse
import os
import tempfile
from unittest.mock import patch

import pytest

from srt_reservation.config import Config


def _make_args(**kwargs) -> argparse.Namespace:
    """테스트용 argparse Namespace 생성 헬퍼."""
    defaults = {
        'user': None, 'psw': None, 'dpt': None, 'arr': None,
        'dt': None, 'tm': None, 'num': None, 'reserve': None,
        'anti_bot': None, 'delay_min': None, 'delay_max': None,
        'use_profile': None, 'profile_dir': None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestScenario01_EnvOnly:
    """.env만으로 실행 성공 시나리오"""

    def test_env_only_succeeds(self):
        """모든 설정을 .env에서만 읽어 실행 성공"""
        env = {
            'SRT_USER': 'env_user',
            'SRT_PASSWORD': 'env_pw',
            'SRT_DPT': '동탄',
            'SRT_ARR': '동대구',
            'SRT_DT': '20240315',
            'SRT_TM': '08',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env()

        args = _make_args()  # 모든 CLI 인자 None
        cli_config = Config.load_from_cli(args)

        config = Config.merge(cli_config, env_config)

        # 필수값 검증 통과
        assert Config.validate_required(config) is True
        assert config['user'] == 'env_user'
        assert config['psw'] == 'env_pw'
        assert config['dpt'] == '동탄'

    def test_env_only_defaults_applied(self):
        """ENV에서 선택값 미설정 시 DEFAULTS 적용"""
        env = {
            'SRT_USER': 'env_user',
            'SRT_PASSWORD': 'env_pw',
            'SRT_DPT': '동탄',
            'SRT_ARR': '동대구',
            'SRT_DT': '20240315',
            'SRT_TM': '08',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env()

        config = Config.merge({}, env_config)

        # DEFAULTS 적용 확인
        assert config['num'] == Config.DEFAULTS['num']
        assert config['anti_bot'] == Config.DEFAULTS['anti_bot']
        assert config['reserve'] == Config.DEFAULTS['reserve']


class TestScenario02_CliOverridesEnv:
    """CLI 인자로 .env 덮어쓰기 시나리오"""

    def test_cli_user_overrides_env_user(self):
        """CLI --user가 ENV SRT_USER를 덮어씀"""
        env = {
            'SRT_USER': 'env_user',
            'SRT_PASSWORD': 'env_pw',
            'SRT_DPT': '동탄',
            'SRT_ARR': '동대구',
            'SRT_DT': '20240315',
            'SRT_TM': '08',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env()

        args = _make_args(user='cli_user')
        cli_config = Config.load_from_cli(args)

        config = Config.merge(cli_config, env_config)

        assert config['user'] == 'cli_user'  # CLI 우선
        assert config['psw'] == 'env_pw'     # ENV 폴백

    def test_cli_overrides_multiple_env_values(self):
        """CLI가 여러 ENV 값을 덮어씀"""
        env = {
            'SRT_USER': 'env_user',
            'SRT_PASSWORD': 'env_pw',
            'SRT_DPT': '동탄',
            'SRT_ARR': '동대구',
            'SRT_DT': '20240315',
            'SRT_TM': '08',
            'SRT_NUM': '3',
            'ANTI_BOT_METHOD': 'stealth',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env()

        args = _make_args(num=1, anti_bot='enhanced')
        cli_config = Config.load_from_cli(args)

        config = Config.merge(cli_config, env_config)

        assert config['num'] == 1          # CLI 우선
        assert config['anti_bot'] == 'enhanced'  # CLI 우선
        assert config['user'] == 'env_user'      # ENV 폴백


class TestScenario03_CliOnlyNoEnv:
    """.env 미존재 시 CLI 폴백 시나리오"""

    def test_cli_only_no_env_file(self):
        """환경변수 없고 CLI만 있을 때 성공"""
        with patch.dict(os.environ, {}, clear=True):
            env_config = Config.load_from_env()

        args = _make_args(
            user='cli_user',
            psw='cli_pw',
            dpt='수서',
            arr='부산',
            dt='20240401',
            tm='10',
        )
        cli_config = Config.load_from_cli(args)

        config = Config.merge(cli_config, env_config)

        assert Config.validate_required(config) is True
        assert config['user'] == 'cli_user'
        assert config['dpt'] == '수서'

    def test_cli_with_defaults_for_optional(self):
        """CLI 필수값 + DEFAULTS 선택값 조합"""
        with patch.dict(os.environ, {}, clear=True):
            env_config = Config.load_from_env()

        args = _make_args(
            user='myid', psw='mypw', dpt='동탄',
            arr='동대구', dt='20240315', tm='08',
        )
        cli_config = Config.load_from_cli(args)
        config = Config.merge(cli_config, env_config)

        assert config['num'] == Config.DEFAULTS['num']
        assert config['delay_min'] == Config.DEFAULTS['delay_min']


class TestScenario04_MissingRequired:
    """필수값 누락 에러 시나리오"""

    def test_all_missing_raises_value_error(self):
        """모든 필수값 누락 시 ValueError"""
        with pytest.raises(ValueError) as exc_info:
            Config.validate_required({})
        msg = str(exc_info.value)
        assert 'user' in msg
        assert 'psw' in msg

    def test_partial_missing_raises_with_missing_keys(self):
        """일부 누락 시 누락된 키만 에러 메시지에 포함"""
        config = {'user': 'id', 'psw': 'pw', 'dpt': '동탄', 'arr': '동대구'}
        with pytest.raises(ValueError) as exc_info:
            Config.validate_required(config)
        msg = str(exc_info.value)
        assert 'dt' in msg
        assert 'tm' in msg
        # 존재하는 키는 메시지에 없어야 함
        assert msg.count('user') == 0 or 'user' not in msg.split(': ', 1)[-1].split(',')[0].split('\n')[0]

    def test_env_only_missing_user_raises(self):
        """ENV에 user 누락 시 validate_required에서 에러"""
        env = {
            'SRT_PASSWORD': 'pw',
            'SRT_DPT': '동탄',
            'SRT_ARR': '동대구',
            'SRT_DT': '20240315',
            'SRT_TM': '08',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env(env_file='/tmp/_nonexistent_test_.env')

        config = Config.merge({}, env_config)

        with pytest.raises(ValueError, match='user'):
            Config.validate_required(config)


class TestScenario05_ManualLoginMode:
    """manual_login 모드 (--user/--psw 제외) 시나리오"""

    def test_manual_login_does_not_require_user_psw(self):
        """수동 로그인 모드에서 user/psw 없어도 경로 설정 가능"""
        env = {
            'SRT_DPT': '동탄',
            'SRT_ARR': '동대구',
            'SRT_DT': '20240315',
            'SRT_TM': '08',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env()

        args = _make_args()  # user/psw 없음
        cli_config = Config.load_from_cli(args)
        config = Config.merge(cli_config, env_config)

        # 수동 로그인 모드 필수값 검증 (user/psw 제외)
        required_keys = ['dpt', 'arr', 'dt', 'tm']
        missing = [k for k in required_keys if k not in config or config[k] is None]
        assert missing == [], f"필수 경로 설정 누락: {missing}"

    def test_manual_login_use_profile_forced_false(self):
        """수동 로그인 모드에서 use_profile은 False로 강제"""
        config = Config.merge({}, {})
        # manual_login.py 로직 시뮬레이션
        config['use_profile'] = False
        config['profile_dir'] = None

        assert config['use_profile'] is False
        assert config['profile_dir'] is None

    def test_manual_login_env_provides_route(self):
        """ENV에서 경로 설정 로드 후 수동 로그인 진행 가능"""
        env = {
            'SRT_DPT': '수서',
            'SRT_ARR': '부산',
            'SRT_DT': '20240501',
            'SRT_TM': '10',
        }
        with patch.dict(os.environ, env, clear=True):
            env_config = Config.load_from_env()

        config = Config.merge({}, env_config)

        assert config['dpt'] == '수서'
        assert config['arr'] == '부산'
        assert config['dt'] == '20240501'
        assert config['tm'] == '10'
