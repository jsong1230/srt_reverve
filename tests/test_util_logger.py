"""util.py --log-level 인자 파싱 테스트"""

import argparse
import sys
from unittest.mock import patch

import pytest

from srt_reservation.util import parse_cli_args


class TestLogLevelParsing:
    def _parse(self, *args):
        with patch('sys.argv', ['prog'] + list(args)):
            return parse_cli_args()

    def test_log_level_default_is_none(self):
        args = self._parse()
        assert args.log_level is None

    def test_log_level_debug(self):
        args = self._parse('--log-level', 'DEBUG')
        assert args.log_level == 'DEBUG'

    def test_log_level_info(self):
        args = self._parse('--log-level', 'INFO')
        assert args.log_level == 'INFO'

    def test_log_level_warning(self):
        args = self._parse('--log-level', 'WARNING')
        assert args.log_level == 'WARNING'

    def test_log_level_error(self):
        args = self._parse('--log-level', 'ERROR')
        assert args.log_level == 'ERROR'

    def test_invalid_log_level_raises_system_exit(self):
        with pytest.raises(SystemExit):
            self._parse('--log-level', 'VERBOSE')

    def test_log_level_attribute_exists_in_namespace(self):
        args = self._parse()
        assert hasattr(args, 'log_level')

    def test_other_args_unaffected_by_log_level(self):
        args = self._parse('--dpt', '동탄', '--log-level', 'DEBUG')
        assert args.dpt == '동탄'
        assert args.log_level == 'DEBUG'

    def test_log_level_is_string_type(self):
        args = self._parse('--log-level', 'INFO')
        assert isinstance(args.log_level, str)

    def test_log_level_none_does_not_interfere_with_other_args(self):
        args = self._parse('--num', '3')
        assert args.num == 3
        assert args.log_level is None
