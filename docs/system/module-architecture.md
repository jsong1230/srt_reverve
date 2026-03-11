# 모듈 아키텍처 설계

## 1. 참조

- 시스템 분석: docs/system/system-analysis.md
- CLI 설계: docs/system/cli-design.md
- 기능 백로그: docs/project/features.md
- 로드맵: docs/project/roadmap.md

## 2. 현재 패키지 구조

```
srt_reservation/
├── __init__.py           # SRT 클래스 re-export
├── main.py               # SRT 클래스 (예약 로직 전체, ~850줄)
├── exceptions.py         # 커스텀 예외 4종
├── validation.py         # 역 목록 검증 (station_list)
└── util.py               # CLI 인자 파싱 (argparse, 12개 인자)
```

루트 진입점:
```
quickstart.py             # 자동 로그인 모드 진입점
manual_login.py           # 수동 로그인 모드 진입점
srt_playwright.py         # Playwright 기반 독립 스크립트 (실험적)
test_browser.py           # 브라우저 동작 수동 테스트
```

테스트:
```
tests/
├── __init__.py
├── test_main.py          # SRT 클래스 단위 테스트 (9개 클래스)
├── test_validation.py    # 역 목록 검증 테스트 (4개)
└── test_exceptions.py    # 예외 클래스 테스트 (5개)
```

## 3. SRT 클래스 책임 분석 (God Object 현황)

### 현재 SRT 클래스 책임 맵

SRT 클래스(`main.py`, ~850줄)가 담당하는 6개 책임 영역:

| 책임 영역 | 메서드 | 대략 줄 수 |
|-----------|--------|-----------|
| 입력 검증 | `__init__`, `check_input` | 75줄 |
| WebDriver 관리 | `_chrome_options`, `_run_driver_undetected`, `_run_driver_stealth`, `_run_driver_enhanced`, `run_driver`, `close_driver` | 200줄 |
| 봇 탐지 우회 | `_inject_stealth_scripts` | 65줄 |
| 인간 행동 시뮬레이션 | `_human_like_delay`, `_human_like_type`, `_smooth_scroll`, `_random_mouse_movement` | 60줄 |
| 인증 (로그인) | `set_log_info`, `login`, `check_login` | 100줄 |
| 검색 및 예약 | `go_search`, `check_result`, `refresh_result`, `book_ticket`, `reserve_ticket` | 150줄 |
| 오케스트레이션 | `run` | 50줄 |

### 문제점

1. **단일 책임 원칙(SRP) 위반**: 드라이버 관리, 봇 우회, 로그인, 검색, 예약이 하나의 클래스에 혼재
2. **테스트 어려움**: WebDriver 의존성으로 인해 개별 메서드 단위 테스트가 복잡 (Mock 과다 사용)
3. **확장 제약**: F-08(에러 리커버리), F-09(알림), F-10(로깅) 추가 시 SRT 클래스가 더 비대해질 위험
4. **코드 중복**: `srt_playwright.py`가 SRT 패키지를 전혀 사용하지 않고 독립 구현

## 4. 리팩토링 계획 (점진적 분리)

### Phase 1: M1 시점 -- 새 모듈 추출 (기존 인터페이스 유지)

M1(F-07, F-08) 구현과 함께 다음 모듈을 신규 생성한다. SRT 클래스의 외부 인터페이스(`run()`, `__init__` 시그니처)는 유지하여 하위 호환성을 보장한다.

#### 4.1 config.py -- 설정 관리 (F-07)

```python
# srt_reservation/config.py

class Config:
    """CLI 인자 + .env 환경변수 통합 설정 관리"""

    def __init__(self):
        self.user: str | None = None
        self.password: str | None = None
        self.dpt_stn: str = ""
        self.arr_stn: str = ""
        self.dpt_dt: str = ""
        self.dpt_tm: str = ""
        self.num_trains: int = 2
        self.want_reserve: bool = False
        self.anti_bot_method: str = "undetected"
        self.retry_delay_min: int = 60
        self.retry_delay_max: int = 120
        self.use_profile: bool = True
        self.profile_dir: str | None = None
        self.log_level: str = "INFO"          # F-10
        self.headless: bool = False            # F-12
        self.telegram_token: str | None = None # F-09
        self.telegram_chat_id: str | None = None # F-09

    @classmethod
    def from_env_and_cli(cls, cli_args) -> "Config":
        """CLI 인자 > 환경변수(.env) > 기본값 우선순위로 설정 로드"""
        ...

    def validate(self) -> None:
        """설정값 검증. 실패 시 커스텀 예외 발생."""
        ...
```

반환값 계약:
- `from_env_and_cli()`: Config 인스턴스 반환. CLI 인자가 None이면 환경변수에서 로드, 환경변수도 없으면 기본값 사용.
- `validate()`: 반환값 없음. 검증 실패 시 `InvalidStationNameError`, `InvalidDateFormatError`, `InvalidDateError`, `InvalidTimeFormatError` 예외 발생.

#### 4.2 recovery.py -- 에러 리커버리 (F-08)

```python
# srt_reservation/recovery.py

class RecoveryManager:
    """에러 감지 및 자동 복구 관리"""

    MAX_NETWORK_RETRIES = 3
    MAX_SESSION_RETRIES = 2
    MAX_CRASH_RETRIES = 1

    def __init__(self, srt_instance):
        self.srt = srt_instance
        self.retry_counts: dict[str, int] = {
            "network": 0,
            "session": 0,
            "crash": 0
        }

    def with_network_retry(self, func, *args, **kwargs):
        """네트워크 오류 시 최대 3회 재시도. 성공 시 함수 반환값, 초과 시 예외 발생."""
        ...

    def handle_session_expired(self, login_id: str, login_psw: str) -> bool:
        """세션 만료 감지 시 재로그인. 성공: True, 최대 재시도 초과: False."""
        ...

    def handle_browser_crash(self) -> bool:
        """브라우저 크래시 시 WebDriver 재초기화. 성공: True, 실패: False."""
        ...

    def get_recovery_summary(self) -> dict:
        """복구 이력 요약 반환. {"network": 횟수, "session": 횟수, "crash": 횟수}"""
        ...
```

반환값 계약:
- `with_network_retry()`: 감싼 함수의 반환값을 그대로 반환. 최대 재시도 초과 시 마지막 예외를 그대로 raise.
- `handle_session_expired()`: `True` = 재로그인 성공, `False` = 최대 재시도 초과
- `handle_browser_crash()`: `True` = WebDriver 재초기화 성공, `False` = 복구 실패

### Phase 2: M2 시점 -- 알림 및 로깅 분리 (F-09, F-10)

#### 4.3 notifier.py -- 알림 (F-09)

```python
# srt_reservation/notifier.py

class TelegramNotifier:
    """Telegram Bot API를 통한 알림 발송"""

    def __init__(self, token: str | None, chat_id: str | None):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def notify_success(self, train_info: dict) -> bool:
        """예약 성공 알림. True: 발송 성공, False: 발송 실패 (예약에 영향 없음)."""
        ...

    def notify_failure(self, error_msg: str) -> bool:
        """예약 실패 알림. True: 발송 성공, False: 발송 실패."""
        ...
```

반환값 계약:
- `notify_success()` / `notify_failure()`: `True` = 메시지 발송 성공, `False` = 발송 실패. 발송 실패가 예약 프로세스에 영향을 주지 않아야 한다 (예외 전파 금지).

#### 4.4 logger.py -- 로깅 설정 (F-10)

```python
# srt_reservation/logger.py

def setup_logger(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """듀얼 핸들러 로거 설정 (콘솔 + 파일).

    Args:
        log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR"
        log_dir: 로그 파일 저장 디렉토리

    Returns:
        logging.Logger: 설정 완료된 로거 인스턴스

    파일 핸들러:
        - 파일명: srt_{YYYY-MM-DD}.log
        - 로테이션: TimedRotatingFileHandler, 7일 보관
        - 포맷: [{YYYY-MM-DD HH:MM:SS}] [{LEVEL}] {message}
    """
    ...
```

### Phase 3: M3 시점 -- 기능 확장 (F-11, F-12)

F-11(다중 검색 조건)과 F-12(헤드리스 모드)는 기존 SRT 클래스와 util.py의 수정으로 구현하며, 별도 모듈 추출은 불필요하다.

- F-11: `util.py`에서 복수 날짜/시간 파싱 지원, `SRT.check_result()`에서 조건 순환 로직 추가
- F-12: `SRT._chrome_options()`에 `--headless=new` 옵션 추가, 예약 결과 콘솔 출력 보강

### Phase 4: 장기 -- God Object 분리 (M4 이후)

M1~M3 완료 후 SRT 클래스의 내부 책임을 별도 클래스로 추출한다. 이 단계는 로드맵에 명시되어 있지 않으며 기술 부채 해소 목적이다.

#### 4.5 WebDriverManager 클래스 추출

```python
# srt_reservation/driver.py

class WebDriverManager:
    """WebDriver 생명주기 관리"""

    def __init__(self, anti_bot_method, use_profile, profile_dir, headless):
        ...

    def create_driver(self) -> WebDriver:
        """anti_bot_method에 따라 WebDriver 초기화. WebDriver 인스턴스 반환."""
        ...

    def close_driver(self) -> None:
        """WebDriver 리소스 정리. 예외 발생 시 로깅 후 무시."""
        ...

    def is_alive(self) -> bool:
        """브라우저 세션 생존 확인. True: 활성, False: 끊김."""
        ...
```

#### 4.6 HumanSimulator 클래스 추출

```python
# srt_reservation/human_sim.py

class HumanSimulator:
    """인간 행동 시뮬레이션"""

    def __init__(self, driver: WebDriver):
        ...

    def delay(self, min_sec=0.5, max_sec=2.0) -> None: ...
    def type_text(self, element, text: str) -> None: ...
    def scroll_to(self, element) -> None: ...
    def random_mouse_move(self) -> None: ...
```

#### 4.7 분리 후 SRT 클래스 (컴포지션)

```python
class SRT:
    def __init__(self, config: Config):
        self.config = config
        self.driver_manager = WebDriverManager(...)
        self.simulator: HumanSimulator | None = None  # driver 생성 후 초기화
        self.recovery = RecoveryManager(self)
        self.notifier = TelegramNotifier(...)
        self.is_booked = False
        self.cnt_refresh = 0

    def run(self, login_id: str, login_psw: str) -> None:
        """전체 예약 프로세스 오케스트레이션"""
        driver = self.driver_manager.create_driver()
        self.simulator = HumanSimulator(driver)
        self._login(driver, login_id, login_psw)
        self._search(driver)
        self._book_loop(driver)
```

## 5. 목표 패키지 구조 (M3 완료 시점)

```
srt_reservation/
├── __init__.py           # SRT 클래스 re-export (하위 호환)
├── main.py               # SRT 클래스 (오케스트레이션 + 검색/예약 핵심 로직)
├── config.py             # 설정 관리 (CLI + .env 통합) [F-07]
├── recovery.py           # 에러 리커버리 [F-08]
├── notifier.py           # Telegram 알림 [F-09]
├── logger.py             # 로깅 설정 (듀얼 핸들러, 로테이션) [F-10]
├── exceptions.py         # 커스텀 예외 4종 (기존 유지)
├── validation.py         # 역 목록 검증 (기존 유지)
└── util.py               # CLI 인자 파싱 (기존 유지, 인자 추가)
```

루트 진입점 (기존 유지):
```
quickstart.py             # 자동 로그인 모드
manual_login.py           # 수동 로그인 모드
srt_playwright.py         # Playwright 기반 (독립 유지, 통합은 Phase 4 이후)
```

## 6. 테스트 전략

### 현재 테스트 커버리지

| 테스트 파일 | 대상 | 테스트 수 | 커버리지 |
|-------------|------|-----------|----------|
| `test_validation.py` | 역 목록 무결성 | 4개 | 높음 |
| `test_exceptions.py` | 예외 클래스 | 5개 | 높음 |
| `test_main.py` | SRT 클래스 | 9개 클래스 | 중간 |

### 신규 모듈 테스트 계획

| 모듈 | 테스트 파일 | 마일스톤 | 주요 시나리오 |
|------|-------------|----------|---------------|
| `config.py` | `tests/test_config.py` | M1 | .env 로드, CLI 우선순위, 유효성 검증, .env 없을 때 폴백 |
| `recovery.py` | `tests/test_recovery.py` | M1 | 네트워크 재시도 3회, 세션 재로그인, 브라우저 크래시 복구, 최대 초과 종료 |
| `notifier.py` | `tests/test_notifier.py` | M2 | 성공/실패 알림 발송, 미설정 시 비활성화, 발송 실패 시 예외 미전파 |
| `logger.py` | `tests/test_logger.py` | M2 | 듀얼 핸들러 생성, 로그 파일 생성, 로테이션 동작, 레벨 설정 |

### 기존 테스트 영향

| 기존 테스트 | M1 영향 | M2 영향 | M3 영향 |
|-------------|---------|---------|---------|
| `test_main.py` | SRT `__init__` 시그니처 변경 가능 -- Config 객체 수용 시 수정 필요 | 알림/로깅 연동 시 Mock 추가 필요 | 다중 조건/헤드리스 관련 테스트 추가 |
| `test_validation.py` | 영향 없음 | 영향 없음 | 영향 없음 |
| `test_exceptions.py` | 영향 없음 | 영향 없음 | 영향 없음 |

### 테스트 패턴 유지

- `unittest.mock`의 `Mock`, `MagicMock`, `patch` 계속 사용
- 외부 의존성(Selenium, Telegram API) Mock 처리
- 환경변수 테스트: `unittest.mock.patch.dict(os.environ, ...)` 사용

## 7. 의존성 관리

### 현재 (`requirements.txt`)

```
selenium>=4.15.0
undetected-chromedriver>=3.5.0
selenium-stealth>=1.0.6
webdriver-manager>=4.0.0
pytest>=7.4.0
pytest-mock>=3.11.0
```

### M1 추가

```
python-dotenv>=1.0.0      # F-07: .env 파일 로드
```

### M2 추가

```
requests>=2.31.0           # F-09: Telegram Bot API 호출 (경량, 추가 의존성 최소)
```

> `python-telegram-bot` 대신 `requests` 직접 사용 권장. 이유: Telegram API 호출이 단순(sendMessage 1개 엔드포인트)하므로 경량 라이브러리로 충분.

### M3 추가

추가 외부 의존성 없음.

## 8. 코드 중복 해결 계획

### 문제: srt_playwright.py 독립 구현

`srt_playwright.py`(Playwright 기반)가 `srt_reservation` 패키지를 전혀 사용하지 않고 SRT 로그인, 검색, 예약 로직을 독자적으로 재구현하고 있다.

### 해결 방향

M1~M3 기간에는 **현상 유지**한다. 이유:

1. Playwright 스크립트는 실험적 상태이며 주요 사용 경로가 아님
2. Selenium과 Playwright의 API가 근본적으로 다르므로 추상화 비용이 높음
3. M1~M3의 핵심 기능(설정 관리, 에러 리커버리, 알림, 로깅)은 Selenium 기반에 집중

M4(통합 테스트 및 배포) 이후 별도 리팩토링 이슈로 처리:

1. `config.py`, `validation.py`, `exceptions.py`는 드라이버 독립적이므로 Playwright 스크립트에서 즉시 재사용 가능
2. 드라이버 인터페이스 추상화(Strategy 패턴)는 장기 과제로 분류

## 9. 성능 고려사항

### 메모리 관리

- WebDriver 세션: `detach` 모드 사용으로 스크립트 종료 후에도 Chrome 유지
- `close_driver()`: `finally` 블록에서 호출하여 비정상 종료 시에도 리소스 해제
- 무한 루프(`check_result`): 루프 내에서 불필요한 객체 생성 최소화

### 재시도 간격

- 기본값: 60~120초 (코드 기준)
- CLAUDE.md 기술값: 15~30초 (문서-코드 불일치 -- system-analysis.md 9.2항 참조)
- 봇 탐지 회피를 위해 현재 기본값(60~120초) 유지 권장

### 로깅 성능 (F-10)

- `TimedRotatingFileHandler` 사용 시 파일 I/O 부하 최소
- 7일 보관 후 자동 삭제로 디스크 사용량 제한
- DEBUG 레벨은 개발 시에만 사용, 운영 시 INFO 이상 권장

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-11 | 초안 작성 | M0 설계 문서 작성 |
