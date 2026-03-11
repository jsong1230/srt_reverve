"""config.py LOG_LEVEL 환경변수 및 폴백 체인 테스트"""

import os
from argparse import Namespace
from unittest.mock import patch

import pytest

from srt_reservation.config import Config


class TestLogLevelEnvVar:
    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        config = Config.load_from_env()
        assert config.get('log_level') == 'DEBUG'

    def test_log_level_warning_from_env(self, monkeypatch):
        monkeypatch.setenv('LOG_LEVEL', 'WARNING')
        config = Config.load_from_env()
        assert config.get('log_level') == 'WARNING'

    def test_log_level_absent_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.delenv('LOG_LEVEL', raising=False)
        # .env 파일 없이 로드하여 환경변수만 참조
        config = Config.load_from_env(env_file=str(tmp_path / '.env'))
        assert 'log_level' not in config

    def test_log_level_in_env_key_map(self):
        assert 'LOG_LEVEL' in Config.ENV_KEY_MAP
        assert Config.ENV_KEY_MAP['LOG_LEVEL'] == 'log_level'

    def test_log_level_default_is_info(self):
        assert Config.DEFAULTS.get('log_level') == 'INFO'


class TestLogLevelFallbackChain:
    def test_cli_overrides_env(self, monkeypatch):
        monkeypatch.setenv('LOG_LEVEL', 'WARNING')
        cli_args = Namespace(log_level='DEBUG')
        env_config = Config.load_from_env()
        cli_config = Config.load_from_cli(cli_args)
        config = Config.merge(cli_config, env_config)
        assert config['log_level'] == 'DEBUG'

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv('LOG_LEVEL', 'ERROR')
        env_config = Config.load_from_env()
        cli_config = Config.load_from_cli(Namespace())
        config = Config.merge(cli_config, env_config)
        assert config['log_level'] == 'ERROR'

    def test_default_used_when_no_cli_no_env(self, monkeypatch):
        monkeypatch.delenv('LOG_LEVEL', raising=False)
        env_config = Config.load_from_env()
        cli_config = Config.load_from_cli(Namespace())
        config = Config.merge(cli_config, env_config)
        assert config['log_level'] == 'INFO'

    def test_config_get_with_default_fallback(self, monkeypatch):
        monkeypatch.delenv('LOG_LEVEL', raising=False)
        env_config = Config.load_from_env()
        cli_config = Config.load_from_cli(Namespace())
        config = Config.merge(cli_config, env_config)
        assert config.get('log_level', 'INFO') == 'INFO'

    def test_log_level_none_in_cli_excluded(self):
        cli_args = Namespace(log_level=None, dpt='동탄')
        cli_config = Config.load_from_cli(cli_args)
        assert 'log_level' not in cli_config
        assert cli_config.get('dpt') == '동탄'
