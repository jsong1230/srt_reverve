"""설정 관리 모듈 - .env 파일과 CLI 인자의 폴백 체인 처리"""

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv


class Config:
    """SRT 설정 관리 클래스.

    폴백 체인: CLI 인자 > 환경변수(.env) > 기본값
    """

    # 환경변수 키 → 설정 키 매핑
    ENV_KEY_MAP: Dict[str, str] = {
        'SRT_USER': 'user',
        'SRT_PASSWORD': 'psw',
        'SRT_DPT': 'dpt',
        'SRT_ARR': 'arr',
        'SRT_DT': 'dt',
        'SRT_TM': 'tm',
        'SRT_NUM': 'num',
        'SRT_RESERVE': 'reserve',
        'ANTI_BOT_METHOD': 'anti_bot',
        'RETRY_DELAY_MIN': 'delay_min',
        'RETRY_DELAY_MAX': 'delay_max',
        'LOG_LEVEL': 'log_level',
    }

    # 선택 인자 기본값
    DEFAULTS: Dict[str, Any] = {
        'num': 2,
        'reserve': False,
        'anti_bot': 'undetected',
        'delay_min': 60,
        'delay_max': 120,
        'use_profile': True,
        'profile_dir': None,
        'log_level': 'INFO',
    }

    # 필수 설정 키 목록
    REQUIRED_KEYS = ['user', 'psw', 'dpt', 'arr', 'dt', 'tm']

    # 정수형으로 변환할 키
    _INT_KEYS = {'num', 'delay_min', 'delay_max'}

    # 불리언으로 변환할 키
    _BOOL_KEYS = {'reserve', 'use_profile'}

    @staticmethod
    def _to_bool(value: str) -> bool:
        """문자열을 bool로 변환한다."""
        return value.lower() in ('true', '1', 'yes', 'y', 't')

    @staticmethod
    def load_from_env(env_file: Optional[str] = None) -> Dict[str, Any]:
        """.env 파일에서 환경변수를 로드한다.

        Args:
            env_file: .env 파일 경로. None이면 자동 탐색.

        Returns:
            환경변수에서 읽은 설정 딕셔너리.
        """
        if env_file is not None:
            load_dotenv(env_file)
        else:
            load_dotenv()

        env_config: Dict[str, Any] = {}
        for env_key, config_key in Config.ENV_KEY_MAP.items():
            value = os.getenv(env_key)
            if value is None:
                continue
            if config_key in Config._INT_KEYS:
                env_config[config_key] = int(value)
            elif config_key in Config._BOOL_KEYS:
                env_config[config_key] = Config._to_bool(value)
            else:
                env_config[config_key] = value

        return env_config

    @staticmethod
    def load_from_cli(args: Any) -> Dict[str, Any]:
        """CLI 인자(argparse Namespace)에서 설정값을 추출한다.

        None인 값(미지정)은 제외하여 폴백이 동작하도록 한다.

        Args:
            args: argparse.parse_args() 반환 객체.

        Returns:
            None이 아닌 인자만 포함한 설정 딕셔너리.
        """
        return {key: value for key, value in vars(args).items() if value is not None}

    @staticmethod
    def merge(
        cli_config: Dict[str, Any],
        env_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """CLI, ENV, DEFAULTS를 우선순위에 따라 병합한다.

        우선순위: CLI > ENV > DEFAULTS

        Args:
            cli_config: CLI 인자에서 추출한 설정.
            env_config: 환경변수에서 로드한 설정.

        Returns:
            병합된 최종 설정 딕셔너리.
        """
        merged = Config.DEFAULTS.copy()
        merged.update(env_config)
        merged.update(cli_config)
        return merged

    @staticmethod
    def validate_required(config: Dict[str, Any]) -> bool:
        """필수 설정값이 모두 존재하는지 검증한다.

        Args:
            config: 병합된 설정 딕셔너리.

        Returns:
            True (모든 필수값 존재 시).

        Raises:
            ValueError: 필수값이 하나라도 누락된 경우.
        """
        missing = [
            k for k in Config.REQUIRED_KEYS
            if k not in config or config[k] is None
        ]

        if missing:
            raise ValueError(
                f"필수 설정값이 누락되었습니다: {', '.join(missing)}\n"
                "CLI 인자로 지정하거나 .env 파일에서 설정하세요."
            )

        return True
