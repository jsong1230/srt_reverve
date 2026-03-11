"""로깅 설정 모듈 - 콘솔 + 파일 듀얼 핸들러"""

import logging
import logging.handlers
import os
import re


def setup_logger(level_name: str = 'INFO') -> logging.Logger:
    """로거 설정: 콘솔 + 파일 듀얼 핸들러.

    Args:
        level_name: 로그 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR')

    Returns:
        설정된 logging.Logger 인스턴스.
    """
    logger = logging.getLogger('srt')

    # 기존 핸들러 제거 (중복 방지)
    logger.handlers = []

    # 로그 레벨 설정
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)

    # 상위 로거로 전파하지 않음 (basicConfig 중복 방지)
    logger.propagate = False

    # 포맷 정의
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (TimedRotatingFileHandler)
    os.makedirs('logs', exist_ok=True)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename='logs/srt.log',
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # 파일명 커스텀: srt.log.YYYY-MM-DD → srt_YYYY-MM-DD.log
    def namer(default_name: str) -> str:
        match = re.match(r'(.*logs/srt\.log)\.(\d{4}-\d{2}-\d{2})', default_name)
        if match:
            return f'logs/srt_{match.group(2)}.log'
        return default_name

    file_handler.namer = namer
    logger.addHandler(file_handler)

    return logger
