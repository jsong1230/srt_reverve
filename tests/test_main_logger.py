"""setup_logger 통합 및 로그 파일/포맷 검증 테스트"""

import logging
import logging.handlers
import os

import pytest

from srt_reservation.logger import setup_logger


@pytest.fixture(autouse=True)
def reset_srt_logger():
    """각 테스트 전후로 srt 로거 핸들러 초기화."""
    logger = logging.getLogger('srt')
    yield
    logger.handlers = []
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


@pytest.fixture()
def logs_dir(tmp_path, monkeypatch):
    """작업 디렉토리를 tmp_path로 변경하여 logs/ 격리."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


# ── setup_logger 호출 결과 ─────────────────────────────────────────────────────

class TestSetupLoggerCall:
    def test_setup_logger_returns_logger(self, logs_dir):
        result = setup_logger('INFO')
        assert isinstance(result, logging.Logger)

    def test_setup_logger_with_debug(self, logs_dir):
        logger = setup_logger('DEBUG')
        assert logger.level == logging.DEBUG

    def test_setup_logger_with_info(self, logs_dir):
        logger = setup_logger('INFO')
        assert logger.level == logging.INFO

    def test_setup_logger_with_warning(self, logs_dir):
        logger = setup_logger('WARNING')
        assert logger.level == logging.WARNING

    def test_setup_logger_with_error(self, logs_dir):
        logger = setup_logger('ERROR')
        assert logger.level == logging.ERROR

    def test_setup_logger_no_args_defaults_to_info(self, logs_dir):
        logger = setup_logger()
        assert logger.level == logging.INFO


# ── 로그 파일 생성 확인 ────────────────────────────────────────────────────────

class TestLogFileCreation:
    def test_logs_directory_exists_after_setup(self, logs_dir):
        setup_logger()
        assert os.path.isdir(str(logs_dir / 'logs'))

    def test_srt_log_file_exists_after_setup(self, logs_dir):
        setup_logger()
        assert os.path.isfile(str(logs_dir / 'logs' / 'srt.log'))

    def test_log_written_to_file(self, logs_dir):
        logger = setup_logger()
        logger.info('파일 기록 테스트')
        log_path = logs_dir / 'logs' / 'srt.log'
        content = log_path.read_text(encoding='utf-8')
        assert '파일 기록 테스트' in content

    def test_multiple_messages_written(self, logs_dir):
        logger = setup_logger()
        logger.info('메시지1')
        logger.warning('메시지2')
        log_path = logs_dir / 'logs' / 'srt.log'
        content = log_path.read_text(encoding='utf-8')
        assert '메시지1' in content
        assert '메시지2' in content


# ── 로그 포맷 검증 ─────────────────────────────────────────────────────────────

class TestLogFormat:
    def test_format_contains_timestamp(self, logs_dir):
        logger = setup_logger()
        logger.info('포맷 테스트')
        content = (logs_dir / 'logs' / 'srt.log').read_text(encoding='utf-8')
        # [YYYY-MM-DD HH:MM:SS] 형식 확인
        import re
        assert re.search(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', content)

    def test_format_contains_level(self, logs_dir):
        logger = setup_logger()
        logger.warning('레벨 테스트')
        content = (logs_dir / 'logs' / 'srt.log').read_text(encoding='utf-8')
        assert '[WARNING]' in content

    def test_format_contains_message(self, logs_dir):
        logger = setup_logger()
        logger.error('에러 메시지 내용')
        content = (logs_dir / 'logs' / 'srt.log').read_text(encoding='utf-8')
        assert '에러 메시지 내용' in content

    def test_format_bracket_style(self, logs_dir):
        logger = setup_logger()
        logger.info('괄호 스타일 확인')
        content = (logs_dir / 'logs' / 'srt.log').read_text(encoding='utf-8')
        assert '[INFO]' in content


# ── 레벨 필터링 검증 ───────────────────────────────────────────────────────────

class TestLevelFiltering:
    def test_debug_messages_not_written_at_info_level(self, logs_dir):
        logger = setup_logger('INFO')
        logger.debug('디버그 메시지 (무시되어야 함)')
        log_path = logs_dir / 'logs' / 'srt.log'
        if log_path.exists():
            content = log_path.read_text(encoding='utf-8')
            assert '디버그 메시지 (무시되어야 함)' not in content

    def test_info_message_written_at_info_level(self, logs_dir):
        logger = setup_logger('INFO')
        logger.info('INFO 메시지 작성')
        content = (logs_dir / 'logs' / 'srt.log').read_text(encoding='utf-8')
        assert 'INFO 메시지 작성' in content

    def test_warning_message_written_at_info_level(self, logs_dir):
        logger = setup_logger('INFO')
        logger.warning('WARNING 메시지')
        content = (logs_dir / 'logs' / 'srt.log').read_text(encoding='utf-8')
        assert 'WARNING 메시지' in content
