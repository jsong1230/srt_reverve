"""logger.py 단위 테스트"""

import logging
import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from srt_reservation.logger import setup_logger


@pytest.fixture(autouse=True)
def clean_logger():
    """각 테스트 전후 srt 로거 초기화."""
    logger = logging.getLogger('srt')
    yield logger
    logger.handlers = []
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


@pytest.fixture()
def temp_logs_dir(tmp_path, monkeypatch):
    """logs/ 디렉토리를 tmp_path로 리다이렉트."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


# ── 핸들러 생성 테스트 ─────────────────────────────────────────────────────────

class TestSetupLoggerHandlers:
    def test_returns_logger_instance(self, temp_logs_dir):
        result = setup_logger()
        assert isinstance(result, logging.Logger)

    def test_logger_name_is_srt(self, temp_logs_dir):
        result = setup_logger()
        assert result.name == 'srt'

    def test_creates_two_handlers(self, temp_logs_dir):
        logger = setup_logger()
        assert len(logger.handlers) == 2

    def test_has_stream_handler(self, temp_logs_dir):
        logger = setup_logger()
        handler_types = [type(h) for h in logger.handlers]
        assert logging.StreamHandler in handler_types

    def test_has_timed_rotating_file_handler(self, temp_logs_dir):
        logger = setup_logger()
        handler_types = [type(h) for h in logger.handlers]
        assert logging.handlers.TimedRotatingFileHandler in handler_types

    def test_no_propagate_to_root(self, temp_logs_dir):
        logger = setup_logger()
        assert logger.propagate is False

    def test_duplicate_call_does_not_add_handlers(self, temp_logs_dir):
        setup_logger()
        setup_logger()
        logger = logging.getLogger('srt')
        assert len(logger.handlers) == 2


# ── 포맷 검증 ─────────────────────────────────────────────────────────────────

class TestLogFormat:
    def test_console_handler_format(self, temp_logs_dir):
        logger = setup_logger()
        stream_handler = next(
            h for h in logger.handlers
            if type(h) is logging.StreamHandler
        )
        fmt = stream_handler.formatter._fmt
        assert '%(asctime)s' in fmt
        assert '%(levelname)s' in fmt
        assert '%(message)s' in fmt

    def test_console_handler_datefmt(self, temp_logs_dir):
        logger = setup_logger()
        stream_handler = next(
            h for h in logger.handlers
            if type(h) is logging.StreamHandler
        )
        assert stream_handler.formatter.datefmt == '%Y-%m-%d %H:%M:%S'

    def test_file_handler_format_matches_console(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        stream_handler = next(
            h for h in logger.handlers
            if type(h) is logging.StreamHandler
        )
        assert file_handler.formatter._fmt == stream_handler.formatter._fmt


# ── 로그 레벨 필터링 테스트 ────────────────────────────────────────────────────

class TestLogLevel:
    def test_default_level_is_info(self, temp_logs_dir):
        logger = setup_logger()
        assert logger.level == logging.INFO

    def test_debug_level(self, temp_logs_dir):
        logger = setup_logger('DEBUG')
        assert logger.level == logging.DEBUG

    def test_warning_level(self, temp_logs_dir):
        logger = setup_logger('WARNING')
        assert logger.level == logging.WARNING

    def test_error_level(self, temp_logs_dir):
        logger = setup_logger('ERROR')
        assert logger.level == logging.ERROR

    def test_info_level_explicit(self, temp_logs_dir):
        logger = setup_logger('INFO')
        assert logger.level == logging.INFO

    def test_invalid_level_falls_back_to_info(self, temp_logs_dir):
        logger = setup_logger('INVALID_LEVEL')
        assert logger.level == logging.INFO

    def test_lowercase_level_accepted(self, temp_logs_dir):
        logger = setup_logger('debug')
        assert logger.level == logging.DEBUG

    def test_handler_level_matches_logger(self, temp_logs_dir):
        logger = setup_logger('WARNING')
        for handler in logger.handlers:
            assert handler.level == logging.WARNING


# ── 파일 생성 테스트 ───────────────────────────────────────────────────────────

class TestFileCreation:
    def test_logs_directory_created(self, temp_logs_dir):
        setup_logger()
        assert os.path.isdir('logs')

    def test_srt_log_file_created(self, temp_logs_dir):
        setup_logger()
        assert os.path.isfile('logs/srt.log')

    def test_log_file_is_writable(self, temp_logs_dir):
        logger = setup_logger()
        logger.info('테스트 메시지')
        assert os.path.getsize('logs/srt.log') > 0

    def test_log_message_content(self, temp_logs_dir):
        logger = setup_logger()
        logger.info('테스트 로그 내용')
        with open('logs/srt.log', encoding='utf-8') as f:
            content = f.read()
        assert '테스트 로그 내용' in content

    def test_log_level_appears_in_file(self, temp_logs_dir):
        logger = setup_logger('INFO')
        logger.info('INFO 메시지')
        with open('logs/srt.log', encoding='utf-8') as f:
            content = f.read()
        assert 'INFO' in content


# ── 파일 회전 설정 테스트 ──────────────────────────────────────────────────────

class TestFileRotation:
    def test_rotation_when_is_midnight(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        assert file_handler.when == 'MIDNIGHT'

    def test_rotation_interval_is_1(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        assert file_handler.interval == 86400  # 1일(초)

    def test_backup_count_is_7(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        assert file_handler.backupCount == 7

    def test_namer_converts_log_rotation_filename(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        result = file_handler.namer('logs/srt.log.2026-03-11')
        assert result == 'logs/srt_2026-03-11.log'

    def test_namer_passes_through_unexpected_name(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        result = file_handler.namer('unexpected_format.log')
        assert result == 'unexpected_format.log'

    def test_encoding_is_utf8(self, temp_logs_dir):
        logger = setup_logger()
        file_handler = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        assert file_handler.encoding == 'utf-8'


# ── 파일 append 동작 테스트 ────────────────────────────────────────────────────

class TestFileAppend:
    def test_second_call_appends_to_existing_log(self, temp_logs_dir):
        logger1 = setup_logger()
        logger1.info('첫 번째 메시지')
        logger1.handlers = []

        logger2 = setup_logger()
        logger2.info('두 번째 메시지')

        with open('logs/srt.log', encoding='utf-8') as f:
            content = f.read()
        assert '첫 번째 메시지' in content
        assert '두 번째 메시지' in content


# ── import 필요 ────────────────────────────────────────────────────────────────
import logging.handlers
