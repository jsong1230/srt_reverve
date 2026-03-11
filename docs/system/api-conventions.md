# 모듈 인터페이스 컨벤션

## 1. 개요

SRT 자동 예약 프로그램은 REST API가 없는 CLI 애플리케이션이다. 이 문서는 모듈 간 인터페이스 계약(함수 시그니처, 반환값, 예외 처리)을 표준화하여 기능 설계 시 일관성을 보장한다.

## 2. 함수/메서드 반환값 컨벤션

### 2.1 반환 타입별 규칙

| 반환 타입 | 사용 시점 | 실패 처리 |
|-----------|-----------|-----------|
| `None` | 상태 변경, 부수 효과 중심 작업 | 예외 발생 |
| `bool` | 성공/실패 판단이 필요한 간단한 검사 | `True` = 성공, `False` = 실패 |
| 구체 타입 (`WebDriver`, `Config`, `dict`) | 객체 생성, 데이터 조회 | 예외 발생 |
| `T | None` | 선택적 데이터 반환 | `None` = 데이터 없음 (정상) |

### 2.2 기존 모듈 인터페이스 (F-01 ~ F-06, 완료)

#### SRT 클래스 (main.py)

```python
class SRT:
    def __init__(self, dpt_stn: str, arr_stn: str, dpt_dt: str, dpt_tm: str,
                 num_trains_to_check: int = 2, want_reserve: bool = False,
                 anti_bot_method: str = "undetected",
                 retry_delay_min: int = 60, retry_delay_max: int = 120,
                 use_profile: bool = True, profile_dir: str | None = None) -> None:
        """SRT 예약 인스턴스 초기화. 입력 검증 실패 시 커스텀 예외 발생."""

    def check_input(self) -> None:
        """입력값 검증. 실패 시 예외 발생 (InvalidStation/Date/TimeError)."""

    def run_driver(self) -> None:
        """WebDriver 초기화. self.driver에 할당. 실패 시 WebDriverException 발생."""

    def login(self, login_id: str, login_psw: str) -> None:
        """SRT 로그인. 실패 시 로그 출력 후 프로세스 계속 (check_login으로 확인)."""

    def check_login(self) -> bool:
        """로그인 성공 여부 확인. True: 로그인됨, False: 미로그인."""

    def go_search(self) -> None:
        """검색 페이지 이동 + 조건 입력 + 조회 실행. 실패 시 예외 발생."""

    def check_result(self) -> None:
        """무한 루프로 예약 가능 좌석 탐색. 예약 성공 시 is_booked=True, 루프 탈출."""

    def book_ticket(self, standard_seat, i: int) -> None:
        """일반석 예약 시도. 성공 시 is_booked=True."""

    def reserve_ticket(self, reservation, i: int) -> None:
        """예약 대기 신청. 성공 시 is_booked=True."""

    def run(self, login_id: str, login_psw: str) -> None:
        """전체 프로세스 오케스트레이션. run_driver -> login -> go_search -> check_result."""

    def close_driver(self) -> None:
        """WebDriver 리소스 정리. 예외 발생 시 로깅 후 무시."""
```

#### exceptions.py

```python
class InvalidStationNameError(Exception):
    """역명 검증 실패. 메시지: '{역명}은(는) 유효하지 않은 역명입니다. 가능한 역: {목록}'"""

class InvalidDateFormatError(Exception):
    """날짜 형식 오류. 메시지: '날짜 형식이 올바르지 않습니다. YYYYMMDD 형식으로 입력하세요: {입력값}'"""

class InvalidDateError(Exception):
    """유효하지 않은 날짜. 메시지: '유효하지 않은 날짜입니다: {입력값}'"""

class InvalidTimeFormatError(Exception):
    """시간 형식 오류. 메시지: '시간은 짝수여야 합니다 (00, 02, ..., 22): {입력값}'"""
```

#### util.py

```python
def parse_cli_args() -> argparse.Namespace:
    """CLI 인자 파싱. argparse.Namespace 반환. 필수 인자 누락 시 argparse가 자동 에러 출력 후 종료."""
```

#### validation.py

```python
station_list: list[str]  # 17개 SRT 역 목록 (불변 데이터)
```

### 2.3 신규 모듈 인터페이스 (M1 ~ M3)

#### config.py (F-07, M1)

```python
class Config:
    """CLI 인자 + .env 환경변수 통합 설정 관리"""

    @classmethod
    def from_env_and_cli(cls, cli_args: argparse.Namespace) -> "Config":
        """설정 로드. CLI 인자 > 환경변수 > 기본값 우선순위.
        반환: Config 인스턴스 (항상 성공, 기본값으로 폴백)."""

    def validate(self) -> None:
        """설정값 검증. 반환값 없음.
        실패 시 InvalidStationNameError, InvalidDateFormatError,
        InvalidDateError, InvalidTimeFormatError 예외 발생."""

    def to_dict(self) -> dict:
        """설정을 딕셔너리로 변환. 민감 정보(password) 마스킹 포함.
        반환: {'user': '1234****', 'dpt_stn': '동탄', ...}"""
```

반환값 계약:
- `from_env_and_cli()`: Config 인스턴스 반환. CLI 인자가 None이면 환경변수에서 로드, 환경변수도 없으면 기본값 사용. 예외 발생하지 않음.
- `validate()`: 반환값 없음. 검증 실패 시 커스텀 예외 발생.
- `to_dict()`: dict 반환. password 필드는 마스킹 처리.

#### recovery.py (F-08, M1)

```python
class RecoveryManager:
    """에러 감지 및 자동 복구 관리"""

    MAX_NETWORK_RETRIES: int = 3
    MAX_SESSION_RETRIES: int = 2
    MAX_CRASH_RETRIES: int = 1

    def __init__(self, srt_instance: "SRT") -> None:
        """SRT 인스턴스 참조를 받아 초기화."""

    def with_network_retry(self, func: Callable, *args, **kwargs) -> Any:
        """네트워크 오류 시 최대 3회 재시도 래퍼.
        반환: 감싼 함수의 반환값을 그대로 반환.
        실패: 최대 재시도 초과 시 마지막 예외를 그대로 raise."""

    def handle_session_expired(self, login_id: str, login_psw: str) -> bool:
        """세션 만료 감지 시 재로그인.
        반환: True = 재로그인 성공, False = 최대 재시도 초과."""

    def handle_browser_crash(self) -> bool:
        """브라우저 크래시 시 WebDriver 재초기화.
        반환: True = 복구 성공, False = 복구 실패."""

    def get_recovery_summary(self) -> dict:
        """복구 이력 요약.
        반환: {'network': int, 'session': int, 'crash': int}"""
```

반환값 계약:
- `with_network_retry()`: 성공 시 감싼 함수의 반환값, 실패 시 마지막 예외 raise
- `handle_session_expired()`: `True` = 성공, `False` = 실패
- `handle_browser_crash()`: `True` = 성공, `False` = 실패

#### notifier.py (F-09, M2)

```python
class TelegramNotifier:
    """Telegram Bot API를 통한 알림 발송"""

    def __init__(self, token: str | None, chat_id: str | None) -> None:
        """초기화. token 또는 chat_id가 None이면 알림 비활성화."""

    @property
    def enabled(self) -> bool:
        """알림 활성화 여부. True: token과 chat_id 모두 설정됨."""

    def notify_success(self, train_info: dict) -> bool:
        """예약 성공 알림. 비활성화 상태에서는 True 반환 (무시).
        반환: True = 발송 성공 또는 비활성화, False = 발송 실패.
        규칙: 발송 실패 시에도 예외를 전파하지 않음."""

    def notify_failure(self, error_msg: str) -> bool:
        """예약 실패 알림.
        반환: True = 발송 성공 또는 비활성화, False = 발송 실패.
        규칙: 발송 실패 시에도 예외를 전파하지 않음."""
```

반환값 계약:
- `notify_success()` / `notify_failure()`: `True` = 성공 또는 비활성화, `False` = 실패. 예외 전파 금지.

#### logger.py (F-10, M2)

```python
def setup_logger(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """듀얼 핸들러 로거 설정 (콘솔 + 파일).

    Args:
        log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR"
        log_dir: 로그 파일 저장 디렉토리 (없으면 자동 생성)

    Returns:
        logging.Logger: 설정 완료된 로거 인스턴스

    파일 핸들러:
        - 파일명: srt_{YYYY-MM-DD}.log
        - 로테이션: TimedRotatingFileHandler, 7일 보관 (backupCount=7)
        - 포맷: [{YYYY-MM-DD HH:MM:SS}] [{LEVEL}] {message}

    콘솔 핸들러:
        - 포맷: [{YYYY-MM-DD HH:MM:SS}] [{LEVEL}] {message}
    """
```

## 3. 예외 처리 계약

### 3.1 예외 분류

| 분류 | 예외 타입 | 처리 방법 |
|------|-----------|-----------|
| 입력 검증 (재시도 불가) | `InvalidStationNameError` | 즉시 종료, exit code 2 |
| 입력 검증 (재시도 불가) | `InvalidDateFormatError` | 즉시 종료, exit code 2 |
| 입력 검증 (재시도 불가) | `InvalidDateError` | 즉시 종료, exit code 2 |
| 입력 검증 (재시도 불가) | `InvalidTimeFormatError` | 즉시 종료, exit code 2 |
| 네트워크 (재시도 가능) | `TimeoutException` | `RecoveryManager.with_network_retry()` |
| 네트워크 (재시도 가능) | `ConnectionError` | `RecoveryManager.with_network_retry()` |
| Selenium (자동 처리) | `StaleElementReferenceException` | 무시하고 계속 진행 |
| Selenium (자동 처리) | `UnexpectedAlertPresentException` | Alert 자동 수락 |
| Selenium (재시도) | `ElementClickInterceptedException` | JavaScript 클릭 fallback |
| 브라우저 (복구 시도) | `WebDriverException` (세션 끊김) | `RecoveryManager.handle_browser_crash()` |

### 3.2 예외 전파 규칙

- **진입점 (quickstart.py, manual_login.py)**: 모든 예외를 catch하여 사용자 친화적 메시지 출력 후 적절한 exit code로 종료
- **SRT 클래스**: 복구 불가능한 예외만 상위로 전파. 복구 가능한 예외는 내부에서 처리.
- **TelegramNotifier**: 모든 예외를 내부에서 catch. 알림 실패가 예약 프로세스에 영향 없음.
- **Config**: 검증 실패 시 커스텀 예외 발생. 로드 실패 시 기본값 폴백.

### 3.3 에러 메시지 작성 규칙

1. 한국어로 작성 (사용자 대상)
2. 원인을 먼저 기술, 해결 방법을 뒤에 제시
3. 기술 용어 최소화 (사용자는 개발자가 아닐 수 있음)
4. 에러 메시지에 입력값 포함 (디버깅 편의)

예시:
```
# 좋은 예
"동탄2은(는) 유효하지 않은 역명입니다. 가능한 역: 수서, 동탄, 평택지제, ..."

# 나쁜 예
"InvalidStationNameError: validation failed"
```

## 4. 모듈 의존성 규칙

### 4.1 의존성 방향 (허용)

```
진입점 (quickstart.py, manual_login.py)
    |
    v
config.py (F-07) -- 설정 로드
    |
    v
main.py (SRT 클래스) -- 핵심 로직
    |
    +---> recovery.py (F-08) -- 에러 복구
    +---> notifier.py (F-09) -- 알림
    +---> logger.py (F-10) -- 로깅
    |
    v
exceptions.py, validation.py -- 기반 모듈 (의존성 없음)
```

### 4.2 금지 의존성

- `exceptions.py`, `validation.py`는 다른 내부 모듈에 의존하지 않음
- `notifier.py`는 `main.py`에 의존하지 않음 (데이터는 dict로 전달)
- `logger.py`는 다른 내부 모듈에 의존하지 않음
- `config.py`는 `validation.py`, `exceptions.py`에만 의존 가능

### 4.3 외부 의존성 관리

| 모듈 | 외부 패키지 | 마일스톤 |
|------|-------------|----------|
| `main.py` | selenium, undetected-chromedriver, selenium-stealth, webdriver-manager | 기존 |
| `config.py` | python-dotenv | M1 |
| `notifier.py` | requests | M2 |
| `logger.py` | (표준 라이브러리만) | M2 |
| `recovery.py` | (표준 라이브러리만) | M1 |

## 5. 로깅 컨벤션

### 5.1 로거 이름

```python
import logging
logger = logging.getLogger(__name__)
```

모듈별로 `__name__`을 사용하여 로거를 생성한다. 로그 출력 시 모듈 출처를 식별할 수 있다.

### 5.2 레벨별 메시지 패턴

```python
# INFO: 단계별 진행 (사용자에게 유용한 정보)
logger.info("SRT 로그인 시도")
logger.info("기차 검색 시작: %s -> %s", dpt_stn, arr_stn)
logger.info("예약 가능 좌석 발견! 예약 시도 중...")
logger.info("검색 결과 새로고침 (%d회차)", cnt_refresh)

# WARNING: 재시도 가능한 문제
logger.warning("네트워크 타임아웃, %d초 후 재시도 (%d/%d)", delay, current, max)
logger.warning("Alert 발생, 자동 처리: %s", alert_text)

# ERROR: 치명적 오류
logger.error("로그인 실패 (최대 재시도 초과): %s", error)
logger.error("브라우저 연결 끊김: %s", error)

# DEBUG: 내부 상태 (개발/디버깅 시에만)
logger.debug("WebDriver 세션 ID: %s", session_id)
logger.debug("CSS Selector 탐색: %s", selector)
logger.debug("설정 로드됨: %s", config.to_dict())
```

### 5.3 민감 정보 로깅 금지

```python
# 금지
logger.info("로그인: ID=%s, PW=%s", user_id, password)

# 허용
logger.info("로그인: ID=%s****", user_id[:4])
```

## 6. 테스트 패턴 컨벤션

### 6.1 모킹 패턴

```python
# Selenium WebDriver 모킹
from unittest.mock import Mock, MagicMock, patch

mock_driver = MagicMock()
mock_driver.find_element.return_value = MagicMock()

# 환경변수 모킹 (config.py 테스트)
with patch.dict(os.environ, {"SRT_USER": "1234567890"}):
    config = Config.from_env_and_cli(args)

# requests 모킹 (notifier.py 테스트)
with patch("requests.post") as mock_post:
    mock_post.return_value.status_code = 200
    result = notifier.notify_success(train_info)
```

### 6.2 테스트 명명 규칙

```python
class TestConfig:
    def test_cli_args_override_env_vars(self): ...
    def test_env_fallback_when_cli_missing(self): ...
    def test_validate_raises_on_invalid_station(self): ...

class TestRecoveryManager:
    def test_network_retry_succeeds_on_second_attempt(self): ...
    def test_network_retry_exceeds_max_raises(self): ...
```

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-11 | 초안 작성 | /design 스킬 산출물 -- M0 전체 설계 |
