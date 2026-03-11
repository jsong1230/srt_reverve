# F-08 에러 리커버리 -- 변경 설계서

## 1. 참조

- 인수조건: docs/project/features.md #F-08
- 시스템 분석: docs/system/system-analysis.md
- CLI 설계: docs/system/cli-design.md (5.3 에러 리커버리)

## 2. 개요

### 기능 목표

네트워크 오류, 세션 만료, 브라우저 크래시 등 런타임 장애 상황에서 자동으로 복구하여 예약 프로세스를 지속하는 기능.

### 인수조건 (features.md #F-08)

1. 네트워크 오류 (TimeoutException, ConnectionError) 발생 시 최대 3회 자동 재시도
2. 세션 만료 감지 시 자동 재로그인 후 검색 재개
3. 브라우저 크래시 감지 시 WebDriver 재초기화 후 전체 프로세스 재시작
4. 재시도 횟수 및 복구 이력 로깅
5. 최대 재시도 횟수 초과 시 명확한 에러 메시지와 함께 종료

### 마일스톤 위치

M1 (안정성 강화), 병렬 그룹 A. 의존성: F-01 (로그인), F-03 (자동 새로고침 및 예약) 완료.

## 3. 현황 분석

### 3.1 기존 에러 핸들링

| 예외 | 현재 처리 | 위치 |
|------|-----------|------|
| `ElementClickInterceptedException` | JavaScript `click()` 재시도 (1회) | `login()`, `book_ticket()` |
| `StaleElementReferenceException` | 무시하고 `standard_seat = "매진"` 처리 | `check_result()` |
| `UnexpectedAlertPresentException` | Alert 자동 수락 후 재시도 | `login()`, `go_search()` |
| 브라우저 세션 끊김 (`InvalidSessionIdException`, `WebDriverException`) | `_is_browser_session_lost()` 감지 -> 에러 메시지 출력 후 종료 | `run()`, `refresh_result()`, `close_driver()` |

### 3.2 현재 코드 구조 (관련 메서드)

**`check_result()` (main.py:762-792)**:
- `while True` 무한 루프
- 예약 성공 시에만 정상 종료
- `refresh_result()` 예외 발생 시 예외 전파 (즉시 종료)
- 네트워크 타임아웃, 세션 만료에 대한 처리 없음

**`run()` (main.py:794-849)**:
- 순차 실행: `run_driver() -> set_log_info() -> login() -> check_login() -> go_search() -> check_result()`
- 최상위 try-except: 브라우저 세션 끊김만 특별 처리
- 그 외 예외는 `logger.error()` 후 `raise`
- 재시도 루프 없음

**`refresh_result()` (main.py:731-745)**:
- `_is_browser_session_lost()` 감지 후 `raise`
- 일반 예외도 `raise` (재시도 없음)

### 3.3 문제점

1. **네트워크 오류 즉시 종료**: `TimeoutException`, `ConnectionError` 발생 시 재시도 없이 프로세스 종료
2. **세션 만료 감지 불가**: 로그인 페이지 리다이렉트를 감지하지 않음. SRT 세션 만료 시 검색 결과 대신 로그인 페이지가 표시되지만 이를 판별하는 로직 없음
3. **브라우저 크래시 복구 불가**: `_is_browser_session_lost()` 감지 후 에러 메시지만 출력하고 종료
4. **무한 루프 탈출 조건 부족**: `check_result()`에 최대 시도 횟수 없음 (system-analysis.md 약점 #5)

## 4. 아키텍처 결정

### 결정 1: 복구 로직 분리 방식

- **선택지**: A) SRT 클래스 내부에 직접 추가 / B) 별도 `recovery.py` 모듈로 분리
- **결정**: B) 별도 `recovery.py` 모듈
- **근거**: SRT 클래스가 이미 약 850줄의 God Object (system-analysis.md 약점 #1). 복구 로직 추가 시 더 비대해짐. 관심사 분리 원칙에 따라 별도 모듈로 분리하여 테스트 용이성과 유지보수성 확보.

### 결정 2: 재시도 패턴

- **선택지**: A) 데코레이터 기반 재시도 / B) 전략 패턴 클래스 / C) 단순 함수 기반
- **결정**: B) 전략 패턴 클래스
- **근거**: 네트워크 오류, 세션 만료, 브라우저 크래시 각각의 복구 전략이 다르고, 향후 확장 가능성 고려. 각 전략 클래스가 독립적으로 테스트 가능.

### 결정 3: SRT 클래스 수정 범위

- **선택지**: A) 메서드 시그니처 변경 포함 / B) 시그니처 유지, 내부 로직만 변경
- **결정**: B) 시그니처 유지
- **근거**: 기존 테스트 9개 클래스의 호환성 유지. `run()`, `check_result()` 내부 로직만 수정하여 recovery 모듈 호출 추가.

### 결정 4: 세션 만료 감지 방법

- **선택지**: A) URL 변경 감지 / B) 페이지 내 특정 요소 존재 여부 / C) 둘 다
- **결정**: C) 둘 다
- **근거**: SRT 세션 만료 시 로그인 페이지(`selectLoginForm`)로 리다이렉트 되거나, Alert 메시지가 표시됨. 두 가지 경우 모두 감지해야 안정적.

## 5. 변경 사항

### 5.1 신규 파일

#### `srt_reservation/recovery.py`

복구 전략을 담당하는 독립 모듈.

```
recovery.py
  |
  +-- RecoveryError(Exception)          # 복구 불가 시 최종 예외
  |
  +-- RecoveryContext                    # 복구 상태 추적 (재시도 횟수, 이력)
  |     - network_retry_count: int       # 네트워크 재시도 현재 횟수
  |     - session_retry_count: int       # 세션 복구 현재 횟수
  |     - browser_retry_count: int       # 브라우저 복구 현재 횟수
  |     - history: list[dict]            # 복구 이력 [{timestamp, error_type, action, success}]
  |     + record(error_type, action, success) -> None
  |     + reset_network_count() -> None
  |     + get_summary() -> str           # 로깅용 요약 문자열
  |
  +-- NetworkErrorRecovery              # 네트워크 오류 재시도
  |     - max_retries: int = 3
  |     - base_delay: float = 5.0       # 기본 대기 시간 (초)
  |     - max_delay: float = 30.0       # 최대 대기 시간 (초)
  |     + should_retry(context) -> bool
  |     + wait_before_retry(context) -> None   # 지수 백오프 대기
  |     + execute_retry(context, operation: Callable) -> Any
  |       # operation 콜백 실행. 성공 시 결과 반환, 실패 시 RecoveryError
  |
  +-- SessionRecovery                   # 세션 만료 복구
  |     - max_retries: int = 2
  |     - login_url_pattern: str = "selectLoginForm"
  |     + is_session_expired(driver) -> bool
  |       # URL에 login_url_pattern 포함 여부 확인
  |       # 반환: True (세션 만료), False (세션 유효)
  |     + recover(context, srt_instance) -> bool
  |       # srt_instance.login() + srt_instance.go_search() 호출
  |       # 반환: True (복구 성공), False (복구 실패)
  |
  +-- BrowserRecovery                   # 브라우저 크래시 복구
  |     - max_retries: int = 1
  |     + is_browser_crashed(driver) -> bool
  |       # driver 통신 불가 여부 확인 (current_url 접근 시도)
  |       # 반환: True (크래시), False (정상)
  |     + recover(context, srt_instance, login_id, login_psw) -> bool
  |       # close_driver() -> run_driver() -> login() -> go_search()
  |       # 반환: True (복구 성공), False (복구 실패)
  |
  +-- is_network_error(exc) -> bool     # 모듈 레벨 유틸 함수
  |     # TimeoutException, ConnectionError, URLError 등 판별
  |     # 반환: True (네트워크 오류), False (아님)
  |
  +-- is_session_error(exc) -> bool     # 모듈 레벨 유틸 함수
        # UnexpectedAlertPresentException + 세션 관련 키워드 판별
        # 반환: True (세션 오류), False (아님)
```

**공유 유틸리티 반환값 계약**:

- `RecoveryContext.get_summary() -> str`: 복구 이력 요약 문자열. 형식: `"[복구 이력] 네트워크 재시도: {n}회, 세션 복구: {m}회, 브라우저 복구: {k}회"`
- `NetworkErrorRecovery.should_retry(context) -> bool`: `True` = 재시도 가능 (횟수 미초과), `False` = 재시도 불가 (최대 횟수 초과)
- `NetworkErrorRecovery.execute_retry(context, operation) -> Any`: 성공 시 operation 반환값, 실패 시 `RecoveryError` 발생
- `SessionRecovery.is_session_expired(driver) -> bool`: `True` = 세션 만료 (재로그인 필요), `False` = 세션 유효
- `SessionRecovery.recover(context, srt_instance) -> bool`: `True` = 재로그인 성공, `False` = 재로그인 실패
- `BrowserRecovery.is_browser_crashed(driver) -> bool`: `True` = 드라이버 통신 불가, `False` = 정상
- `BrowserRecovery.recover(context, srt_instance, login_id, login_psw) -> bool`: `True` = 브라우저 재시작 + 로그인 + 검색 복구 성공, `False` = 복구 실패
- `is_network_error(exc) -> bool`: `True` = 네트워크 관련 예외, `False` = 기타 예외
- `is_session_error(exc) -> bool`: `True` = 세션 관련 예외, `False` = 기타 예외

### 5.2 기존 파일 수정

#### `srt_reservation/main.py` -- SRT 클래스

**수정 메서드 1: `__init__()` (기존 시그니처 유지)**

추가되는 내부 속성:
```python
# recovery.py import 추가
from srt_reservation.recovery import (
    RecoveryContext, NetworkErrorRecovery, SessionRecovery,
    BrowserRecovery, is_network_error, is_session_error, RecoveryError
)

# __init__ 내부에 추가
self._recovery_context = RecoveryContext()
self._network_recovery = NetworkErrorRecovery(max_retries=3)
self._session_recovery = SessionRecovery(max_retries=2)
self._browser_recovery = BrowserRecovery(max_retries=1)
```

**수정 메서드 2: `check_result()` (시그니처 유지)**

현재 구조:
```python
def check_result(self):
    while True:
        for i in range(1, self.num_trains_to_check+1):
            # 좌석 확인 ...
            # book_ticket / reserve_ticket ...
        # 대기 + refresh_result()
```

변경 후 구조:
```python
def check_result(self):
    while True:
        try:
            for i in range(1, self.num_trains_to_check+1):
                try:
                    # 기존 좌석 확인 로직 (변경 없음)
                except StaleElementReferenceException:
                    # 기존 처리 (변경 없음)
                except Exception as e:
                    # [신규] 세션 만료 감지
                    if self._session_recovery.is_session_expired(self.driver):
                        logger.warning("세션 만료 감지, 재로그인 시도")
                        if self._session_recovery.recover(self._recovery_context, self):
                            logger.info("세션 복구 성공, 검색 재개")
                            break  # for 루프 탈출하여 처음부터 검색
                        else:
                            raise RecoveryError("세션 복구 실패: 최대 재시도 초과")
                    # [신규] 네트워크 오류 감지
                    elif is_network_error(e):
                        logger.warning(f"네트워크 오류 감지: {e}")
                        if self._network_recovery.should_retry(self._recovery_context):
                            self._network_recovery.wait_before_retry(self._recovery_context)
                            break  # for 루프 탈출하여 재시도
                        else:
                            raise RecoveryError("네트워크 오류 복구 실패: 최대 재시도 초과")
                    else:
                        # 기존 처리 (변경 없음)
                        standard_seat = "매진"
                        reservation = "매진"
            else:
                # for 루프가 break 없이 완료된 경우 (정상 흐름)
                self._recovery_context.reset_network_count()  # 성공 시 카운터 리셋
                if self.is_booked:
                    return self.driver
                # 대기 + refresh_result()
                delay = randint(self.retry_delay_min, self.retry_delay_max)
                logger.info(f"다음 시도까지 {delay}초 대기...")
                time.sleep(delay)
                self.refresh_result()

        except RecoveryError:
            raise  # 최대 재시도 초과 -> 상위로 전파
        except Exception as e:
            if _is_browser_session_lost(e):
                raise  # 브라우저 크래시 -> run()에서 처리
            raise
```

**수정 메서드 3: `run()` (시그니처 유지)**

현재 구조:
```python
def run(self, login_id, login_psw):
    try:
        self.run_driver()
        self.set_log_info(login_id, login_psw)
        self.login()
        # 로그인 확인 ...
        self.go_search()
        self.check_result()
    except Exception as e:
        # 브라우저 세션 끊김 처리 ...
        raise
```

변경 후 구조:
```python
def run(self, login_id, login_psw):
    try:
        self.run_driver()
        self.set_log_info(login_id, login_psw)
        self.login()
        # 로그인 확인 (기존 로직 유지) ...
        self.go_search()
        self.check_result()

        if self.is_booked:
            logger.info("예약 프로세스 완료")
        else:
            logger.warning("예약을 완료하지 못했습니다.")

    except RecoveryError as e:
        # [신규] 최대 재시도 초과 시 명확한 에러 메시지
        logger.error(f"복구 실패로 프로세스를 종료합니다: {e}")
        logger.info(self._recovery_context.get_summary())
        raise

    except Exception as e:
        if _is_browser_session_lost(e):
            # [신규] 브라우저 크래시 복구 시도
            logger.warning("브라우저 연결 끊김 감지, 복구 시도")
            if self._browser_recovery.recover(
                self._recovery_context, self, login_id, login_psw
            ):
                logger.info("브라우저 복구 성공, 예약 프로세스 재시작")
                logger.info(self._recovery_context.get_summary())
                # 복구 후 check_result()부터 재시작 (login, go_search는 recover 내부에서 수행)
                try:
                    self.check_result()
                    if self.is_booked:
                        logger.info("예약 프로세스 완료 (브라우저 복구 후)")
                    return
                except Exception as inner_e:
                    logger.error(f"브라우저 복구 후 재시도 실패: {inner_e}")
                    raise RecoveryError("브라우저 복구 후 재시도 실패") from inner_e
            else:
                logger.error(
                    "브라우저 복구 실패. Chrome을 중간에 닫으셨거나 연결이 끊어진 것 같습니다. "
                    "다시 실행해 주세요."
                )
                logger.info(self._recovery_context.get_summary())
                raise RecoveryError("브라우저 복구 실패") from e
        else:
            logger.error(f"예약 프로세스 중 오류 발생: {e}")
            logger.info(self._recovery_context.get_summary())
            raise
    finally:
        pass  # 기존과 동일 (브라우저 창 유지)
```

#### `srt_reservation/exceptions.py`

변경 없음. `RecoveryError`는 `recovery.py`에서 정의.

#### `srt_reservation/__init__.py`

`RecoveryError` re-export 추가:
```python
from srt_reservation.recovery import RecoveryError
```

## 6. 시퀀스 흐름

### 6.1 네트워크 오류 -> 재시도 -> 성공

```
check_result() loop
  |-> find_element() -> TimeoutException 발생
  |-> is_network_error(e) = True
  |-> NetworkErrorRecovery.should_retry(context) = True (1/3)
  |-> context.record("network", "retry", pending)
  |-> wait_before_retry(context)  # 5초 (1차)
  |-> break (for 루프)
  |-> check_result() while 루프 재진입
  |-> find_element() -> 성공
  |-> context.reset_network_count()
  |-> book_ticket() -> 성공
  |-> return driver
```

### 6.2 세션 만료 -> 재로그인 -> 검색 재개

```
check_result() loop
  |-> find_element() -> Exception 발생
  |-> SessionRecovery.is_session_expired(driver) = True
  |     (driver.current_url에 "selectLoginForm" 포함)
  |-> context.record("session", "relogin", pending)
  |-> SessionRecovery.recover(context, srt)
  |     |-> srt.login()
  |     |-> srt.check_login()
  |     |-> srt.go_search()
  |     |-> return True
  |-> context.record("session", "relogin", True)
  |-> break (for 루프)
  |-> check_result() while 루프 재진입 (검색 결과 확인)
```

### 6.3 브라우저 크래시 -> WebDriver 재초기화

```
run()
  |-> check_result()
  |     |-> refresh_result() -> WebDriverException (session lost)
  |     |-> _is_browser_session_lost(e) = True -> raise
  |-> run() except 블록 진입
  |-> _is_browser_session_lost(e) = True
  |-> BrowserRecovery.recover(context, srt, login_id, login_psw)
  |     |-> srt.close_driver()  # 기존 세션 정리 (예외 무시)
  |     |-> srt.run_driver()    # 새 WebDriver 초기화
  |     |-> srt.login()
  |     |-> srt.check_login()
  |     |-> srt.go_search()
  |     |-> return True
  |-> srt.check_result()  # 복구 후 재시작
```

### 6.4 최대 재시도 초과 -> 종료

```
check_result() loop
  |-> TimeoutException 발생 (3번째)
  |-> NetworkErrorRecovery.should_retry(context) = False (3/3 초과)
  |-> raise RecoveryError("네트워크 오류 복구 실패: 최대 재시도 초과")
  |
run() except 블록
  |-> RecoveryError 캐치
  |-> logger.error("복구 실패로 프로세스를 종료합니다: ...")
  |-> logger.info(context.get_summary())
  |-> raise
```

## 7. 재시도 전략 상세

### 7.1 네트워크 오류 (TimeoutException, ConnectionError)

| 항목 | 값 |
|------|-----|
| 최대 재시도 | 3회 |
| 대기 시간 | 지수 백오프: `base_delay * (2 ** retry_count)` |
| 기본 대기 | 5초 |
| 최대 대기 | 30초 |
| 대기 시간 예시 | 1차: 5초, 2차: 10초, 3차: 20초 |
| 지터 | +-1초 랜덤 추가 (봇 탐지 회피) |
| 성공 시 | 카운터 리셋 (`reset_network_count()`) |

판별 대상 예외:
- `selenium.common.exceptions.TimeoutException`
- `ConnectionError` (표준 라이브러리)
- `urllib.error.URLError`
- `selenium.common.exceptions.WebDriverException` 중 "timeout" 포함 메시지

### 7.2 세션 만료

| 항목 | 값 |
|------|-----|
| 최대 재시도 | 2회 |
| 감지 방법 1 | `driver.current_url`에 `"selectLoginForm"` 포함 |
| 감지 방법 2 | Alert 텍스트에 "세션" 또는 "로그인" 키워드 포함 |
| 복구 절차 | `login()` -> `check_login()` -> `go_search()` |
| 복구 후 | `check_result()` while 루프 재진입 (처음부터 검색) |

### 7.3 브라우저 크래시

| 항목 | 값 |
|------|-----|
| 최대 재시도 | 1회 (무한 루프 방지) |
| 감지 방법 | `_is_browser_session_lost()` 기존 함수 재활용 |
| 복구 절차 | `close_driver()` -> `run_driver()` -> `login()` -> `check_login()` -> `go_search()` |
| 복구 후 | `check_result()` 재시작 |

## 8. 영향 범위 분석

### 8.1 기존 API 변경

| 메서드 | 현재 | 변경 후 | 하위 호환성 |
|--------|------|---------|------------|
| `SRT.__init__()` | 10개 파라미터 | 시그니처 동일, 내부에 recovery 속성 추가 | 완전 호환 |
| `SRT.check_result()` | 예약 성공 시 driver 반환, 예외 시 전파 | 동일 + `RecoveryError` 추가 발생 가능 | 호환 (새 예외 타입 추가) |
| `SRT.run()` | `login_id, login_psw` 2개 인자 | 시그니처 동일, 내부에 복구 로직 추가 | 완전 호환 |

### 8.2 사이드 이펙트

| 기존 기능 | 영향 | 설명 |
|-----------|------|------|
| F-01 로그인 | 간접 영향 | `SessionRecovery.recover()` 내부에서 `login()` 재호출. 기존 login() 로직 변경 없음 |
| F-03 자동 새로고침 | 직접 영향 | `check_result()` 내부 에러 처리 로직 변경. 기존 refresh 로직은 유지 |
| F-05 봇 탐지 우회 | 간접 영향 | `BrowserRecovery.recover()` 내부에서 `run_driver()` 재호출. 기존 봇 탐지 옵션 유지 |
| F-06 CLI | 영향 없음 | CLI 인자 변경 없음 |

### 8.3 수정 필요 파일

| 파일 | 변경 유형 | 변경 내용 |
|------|-----------|-----------|
| `srt_reservation/main.py` | 수정 | `__init__`, `check_result`, `run` 메서드 내부 로직 변경. import 추가 |
| `srt_reservation/__init__.py` | 수정 | `RecoveryError` re-export 추가 |

### 8.4 신규 생성 파일

| 파일 | 설명 |
|------|------|
| `srt_reservation/recovery.py` | 복구 전략 모듈 (RecoveryContext, NetworkErrorRecovery, SessionRecovery, BrowserRecovery) |
| `tests/test_recovery.py` | recovery.py 유닛 테스트 |

## 9. 성능 설계

### 재시도 대기 시간 총계 (최악의 경우)

- 네트워크 오류 3회: 5 + 10 + 20 = 35초
- 세션 복구 2회: 각 약 10초 (로그인 + 검색) = 20초
- 브라우저 복구 1회: 약 15초 (드라이버 초기화 + 로그인 + 검색)
- 최악 총계: 약 70초 추가 소요

### 로깅 부하

- 복구 이력은 메모리 내 list에 저장 (dict 객체)
- 프로세스 종료 시까지만 유지 (영속화 없음)
- F-10 (로깅 개선) 구현 후 파일 로그에도 기록

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-08 에러 리커버리 변경 설계 |
