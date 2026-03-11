# F-08 에러 리커버리 -- 테스트 명세

## 참조

- 설계서: docs/specs/F-08-에러리커버리/change-design.md
- 인수조건: docs/project/features.md #F-08

## 테스트 전략

### 테스트 파일 구조

```
tests/
  ├── test_recovery.py          # [신규] recovery.py 유닛 테스트
  ├── test_main.py              # [수정 불필요] 기존 테스트 호환성 유지 확인
  ├── test_main_recovery.py     # [신규] main.py 복구 통합 테스트
  ├── test_validation.py        # [수정 불필요]
  └── test_exceptions.py        # [수정 불필요]
```

### Mock 전략

| 대상 | Mock 방법 | 설명 |
|------|-----------|------|
| WebDriver | `unittest.mock.Mock()` | 기존 패턴 동일. `driver.current_url`, `driver.find_element()` 등 Mock |
| TimeoutException | `side_effect=TimeoutException()` | 네트워크 타임아웃 시뮬레이션 |
| ConnectionError | `side_effect=ConnectionError()` | 네트워크 연결 오류 시뮬레이션 |
| 세션 만료 | `driver.current_url = "...selectLoginForm..."` | URL 변경으로 세션 만료 시뮬레이션 |
| 브라우저 크래시 | `side_effect=InvalidSessionIdException()` | 세션 끊김 시뮬레이션 |
| `time.sleep` | `@patch('srt_reservation.recovery.time.sleep')` | 대기 시간 제거 (테스트 속도) |
| SRT 메서드 | `@patch.object(srt, 'login')` 등 | 복구 절차에서 호출되는 메서드 Mock |

## 단위 테스트 (tests/test_recovery.py)

### RecoveryContext

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| 초기 상태 확인 | `RecoveryContext()` | `network_retry_count == 0`, `session_retry_count == 0`, `browser_retry_count == 0`, `history == []` |
| 이력 기록 | `context.record("network", "retry", True)` | `len(history) == 1`, `history[0]["error_type"] == "network"`, `history[0]["action"] == "retry"`, `history[0]["success"] == True` |
| 이력에 타임스탬프 포함 | `context.record("network", "retry", True)` | `"timestamp" in history[0]`, 타임스탬프가 ISO 형식 문자열 |
| 네트워크 카운터 리셋 | `context.network_retry_count = 2` -> `context.reset_network_count()` | `network_retry_count == 0` |
| 요약 문자열 | `context` (network 2회, session 1회) | `"[복구 이력] 네트워크 재시도: 2회, 세션 복구: 1회, 브라우저 복구: 0회"` |

### NetworkErrorRecovery

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| 재시도 가능 (1/3) | `context.network_retry_count = 0` | `should_retry(context) == True` |
| 재시도 가능 (3/3) | `context.network_retry_count = 2` | `should_retry(context) == True` |
| 재시도 불가 (초과) | `context.network_retry_count = 3` | `should_retry(context) == False` |
| 대기 시간 1차 | `context.network_retry_count = 0` | `wait_before_retry` 호출 시 `time.sleep`에 4~6초 범위 전달 (base 5초 +- 1초 지터) |
| 대기 시간 2차 | `context.network_retry_count = 1` | `time.sleep`에 9~11초 범위 전달 (10초 +- 1초 지터) |
| 대기 시간 3차 | `context.network_retry_count = 2` | `time.sleep`에 19~21초 범위 전달 (20초 +- 1초 지터) |
| 대기 시간 상한 | `max_delay=30.0`, `context.network_retry_count = 10` | `time.sleep`에 30초 이하 전달 |
| execute_retry 성공 | `operation = lambda: "결과"` | 반환값: `"결과"`, `context.network_retry_count += 1`, `context.record()` 호출 |
| execute_retry 실패 (최대 초과) | `context.network_retry_count = 3`, `operation` raises `TimeoutException` | `RecoveryError("네트워크 오류 복구 실패: 최대 재시도 횟수(3회) 초과")` 발생 |
| 커스텀 max_retries | `NetworkErrorRecovery(max_retries=5)` | `max_retries == 5` |

### SessionRecovery

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| 세션 만료 감지 (URL) | `driver.current_url = "https://etk.srail.co.kr/cmc/01/selectLoginForm.do"` | `is_session_expired(driver) == True` |
| 세션 유효 (검색 결과 URL) | `driver.current_url = "https://etk.srail.co.kr/hpg/hra/01/selectScheduleList.do"` | `is_session_expired(driver) == False` |
| 세션 만료 감지 실패 (driver 예외) | `driver.current_url` raises `WebDriverException` | `is_session_expired(driver) == False` (예외 시 False 반환, 브라우저 크래시로 분류) |
| 복구 성공 | `srt.login()` 정상, `srt.check_login()` returns True, `srt.go_search()` 정상 | `recover(context, srt) == True`, `context.session_retry_count += 1` |
| 복구 실패 (로그인 실패) | `srt.check_login()` returns False | `recover(context, srt) == False` |
| 복구 실패 (최대 초과) | `context.session_retry_count = 2` (max=2) | `recover(context, srt) == False`, `context.record("session", "relogin", False)` |
| 커스텀 max_retries | `SessionRecovery(max_retries=1)` | `max_retries == 1` |

### BrowserRecovery

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| 크래시 감지 (current_url 접근 불가) | `driver.current_url` raises `InvalidSessionIdException` | `is_browser_crashed(driver) == True` |
| 크래시 감지 (WebDriverException session lost) | `driver.current_url` raises `WebDriverException("invalid session")` | `is_browser_crashed(driver) == True` |
| 정상 상태 | `driver.current_url = "https://..."` | `is_browser_crashed(driver) == False` |
| 복구 성공 | `srt.close_driver()` 정상, `srt.run_driver()` 정상, `srt.login()` 정상, `srt.go_search()` 정상 | `recover(context, srt, "id", "pw") == True`, `context.browser_retry_count == 1` |
| 복구 실패 (run_driver 예외) | `srt.run_driver()` raises `Exception` | `recover(context, srt, "id", "pw") == False` |
| 복구 실패 (최대 초과) | `context.browser_retry_count = 1` (max=1) | `recover(context, srt, "id", "pw") == False` |
| close_driver 예외 무시 | `srt.close_driver()` raises `Exception` | 예외 무시하고 `run_driver()` 진행 |

### 유틸 함수

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| TimeoutException 판별 | `TimeoutException()` | `is_network_error(exc) == True` |
| ConnectionError 판별 | `ConnectionError()` | `is_network_error(exc) == True` |
| WebDriverException timeout | `WebDriverException("timeout receiving message")` | `is_network_error(exc) == True` |
| StaleElementReferenceException | `StaleElementReferenceException()` | `is_network_error(exc) == False` |
| InvalidSessionIdException | `InvalidSessionIdException()` | `is_network_error(exc) == False` |
| ValueError | `ValueError()` | `is_network_error(exc) == False` |
| 세션 오류 판별 | `UnexpectedAlertPresentException()` | `is_session_error(exc) == True` |
| 일반 예외 | `Exception("일반 오류")` | `is_session_error(exc) == False` |

## 통합 테스트 (tests/test_main_recovery.py)

### check_result() 복구 통합

| 시나리오 | 설정 | 예상 결과 |
|----------|------|-----------|
| 타임아웃 1회 후 성공 | `find_element` 1차: `TimeoutException`, 2차: 정상 ("예약하기") | `book_ticket` 호출, `driver` 반환, `_recovery_context.network_retry_count >= 1` |
| 타임아웃 3회 후 성공 | `find_element` 1~3차: `TimeoutException`, 4차: 정상 | `driver` 반환, `_recovery_context.history`에 3건 기록 |
| 타임아웃 4회 (최대 초과) | `find_element` 계속 `TimeoutException` | `RecoveryError` 발생, 메시지: `"네트워크 오류 복구 실패: 최대 재시도 초과"` |
| 세션 만료 -> 재로그인 -> 성공 | `find_element` raises Exception, `driver.current_url` = login URL, 재로그인 후 정상 | `login()` 재호출됨, `go_search()` 재호출됨, `driver` 반환 |
| 세션 만료 -> 재로그인 실패 | `find_element` raises Exception, `driver.current_url` = login URL, `check_login()` returns False | `RecoveryError` 발생, 메시지: `"세션 복구 실패: 최대 재시도 초과"` |

### run() 복구 통합

| 시나리오 | 설정 | 예상 결과 |
|----------|------|-----------|
| 브라우저 크래시 -> 복구 -> 성공 | `check_result` 1차: `InvalidSessionIdException`, 복구 후 2차: 정상 | `run_driver()` 2번 호출, `login()` 2번 호출, `is_booked == True` |
| 브라우저 크래시 -> 복구 실패 | `check_result` 1차: `InvalidSessionIdException`, `run_driver()` 2차: `Exception` | `RecoveryError` 발생, 메시지: `"브라우저 복구 실패"` |
| RecoveryError 전파 | `check_result` raises `RecoveryError("최대 재시도 초과")` | `RecoveryError` 그대로 전파, `get_summary()` 로그 출력 |
| 일반 예외 전파 | `check_result` raises `ValueError("알 수 없는 오류")` | `ValueError` 그대로 전파 |

### 로깅 검증

| 시나리오 | 설정 | 예상 결과 |
|----------|------|-----------|
| 네트워크 재시도 로그 | `TimeoutException` 1회 발생 후 성공 | `logger.warning` 호출에 `"네트워크 오류 감지"` 포함 |
| 세션 복구 로그 | 세션 만료 감지 후 복구 성공 | `logger.warning` 호출에 `"세션 만료 감지"` 포함, `logger.info` 호출에 `"세션 복구 성공"` 포함 |
| 브라우저 복구 로그 | 브라우저 크래시 후 복구 시도 | `logger.warning` 호출에 `"브라우저 연결 끊김 감지"` 포함 |
| 복구 이력 요약 로그 | 프로세스 종료 시 | `logger.info` 호출에 `"[복구 이력]"` 포함 |
| 최대 재시도 초과 로그 | `RecoveryError` 발생 | `logger.error` 호출에 `"복구 실패로 프로세스를 종료합니다"` 포함 |

## 경계 조건 / 에러 케이스

- `NetworkErrorRecovery(max_retries=0)` 설정 시 `should_retry()` 항상 `False` 반환
- `RecoveryContext`에 100회 이상 이력 기록 시 메모리 증가 없이 정상 동작 (list append)
- `SessionRecovery.is_session_expired()`에서 `driver`가 `None`일 때 `AttributeError` 대신 `False` 반환
- `BrowserRecovery.recover()`에서 `close_driver()` 예외 발생 시 무시하고 `run_driver()` 진행
- `is_network_error(None)` 호출 시 `False` 반환 (예외 발생 안 함)
- `RecoveryError` 메시지 정확한 문자열:
  - 네트워크 최대 초과: `"네트워크 오류 복구 실패: 최대 재시도 횟수(3회) 초과"`
  - 세션 복구 실패: `"세션 복구 실패: 최대 재시도 초과"`
  - 브라우저 복구 실패: `"브라우저 복구 실패"`
  - 브라우저 복구 후 재시도 실패: `"브라우저 복구 후 재시도 실패"`

## E2E 시나리오

### E2E-1: 네트워크 타임아웃 -> 자동 재시도 -> 예약 성공

```
1. SRT 인스턴스 생성 (동탄 -> 동대구)
2. run(login_id, login_psw) 호출
3. check_result() 진입
4. find_element() 호출 시 TimeoutException 발생 (Mock)
5. 자동 재시도 (5초 대기 후)
6. find_element() 호출 시 "예약하기" 반환 (Mock)
7. book_ticket() 성공
8. is_booked == True 확인
9. _recovery_context.history에 network retry 1건 기록 확인
```

### E2E-2: 세션 만료 -> 재로그인 -> 검색 재개 -> 예약 성공

```
1. SRT 인스턴스 생성
2. run() 호출 -> login() -> go_search() -> check_result() 진입
3. check_result() 중 find_element() 예외 발생 (Mock)
4. driver.current_url이 "selectLoginForm" 포함 (세션 만료 Mock)
5. SessionRecovery가 login() 재호출
6. check_login() 성공 확인
7. go_search() 재호출
8. check_result() while 루프 재진입
9. find_element() 정상 -> "예약하기" -> book_ticket() 성공
10. is_booked == True 확인
11. _recovery_context.history에 session relogin 1건 기록 확인
```

### E2E-3: 브라우저 크래시 -> WebDriver 재초기화 -> 프로세스 재시작

```
1. SRT 인스턴스 생성
2. run() 호출 -> 정상 진행
3. check_result() 중 refresh_result()에서 InvalidSessionIdException 발생 (Mock)
4. run() except 블록에서 브라우저 크래시 감지
5. BrowserRecovery.recover() 호출
6. close_driver() -> run_driver() -> login() -> go_search() (모두 Mock)
7. check_result() 재시작
8. "예약하기" 발견 -> book_ticket() 성공
9. is_booked == True 확인
10. _recovery_context.browser_retry_count == 1 확인
```

### E2E-4: 최대 재시도 초과 -> 에러 메시지 + 종료

```
1. SRT 인스턴스 생성
2. run() 호출
3. check_result() 진입
4. find_element() 호출 시 TimeoutException 계속 발생 (4회 이상, Mock)
5. 1~3차 재시도 수행 (대기 시간은 Mock으로 제거)
6. 4차에서 should_retry() == False
7. RecoveryError 발생
8. run() except 블록에서 "복구 실패로 프로세스를 종료합니다" 로그 출력 확인
9. _recovery_context.get_summary() 출력 확인: "[복구 이력] 네트워크 재시도: 3회, 세션 복구: 0회, 브라우저 복구: 0회"
10. RecoveryError 최종 전파 확인
```

### E2E-5: 복합 장애 -> 네트워크 재시도 후 세션 만료 -> 재로그인 -> 성공

```
1. SRT 인스턴스 생성
2. run() 호출
3. check_result() 진입
4. 1차: TimeoutException -> 네트워크 재시도
5. 2차: 정상 find_element() -> 좌석 확인 중 Exception + URL 변경 감지 (세션 만료)
6. SessionRecovery.recover() -> login() + go_search() 성공
7. 3차: "예약하기" -> book_ticket() 성공
8. is_booked == True 확인
9. history에 network 1건 + session 1건 기록 확인
```

## 회귀 테스트

### 기존 테스트 호환성 확인

| 기존 기능 | 영향 여부 | 검증 방법 |
|-----------|-----------|-----------|
| F-01 로그인 (TestSRTLogin) | 간접 | `test_login_success`, `test_login_with_alert` 통과 확인. `login()` 시그니처 변경 없음 |
| F-01 로그인 확인 (TestSRTCheckLogin) | 간접 | `test_check_login_success`, `test_check_login_failure` 통과 확인 |
| F-02 입력 검증 (TestSRTInputValidation) | 영향 없음 | 14개 테스트 전체 통과 확인. `__init__` 시그니처 변경 없음 |
| F-03 예약 (TestSRTBookTicket) | 영향 없음 | `test_book_ticket_available/unavailable/sold_out` 통과 확인 |
| F-03 새로고침 (TestSRTRefreshResult) | 영향 없음 | `test_refresh_result` 통과 확인 |
| F-03 결과 확인 (TestSRTCheckResult) | 직접 영향 | `test_check_result_with_booking_success` 통과 확인 (정상 경로 변경 없음). `test_check_result_refresh_until_error_or_booked` 통과 확인 (예외 전파 동작 유지) |
| F-04 예약 대기 (TestSRTReserveTicket) | 영향 없음 | `test_reserve_ticket_available/unavailable` 통과 확인 |
| F-05 WebDriver (TestSRTDriver) | 영향 없음 | `test_run_driver_success/fallback/close` 통과 확인 |
| F-06 Alert (TestSRTAlertHandling) | 영향 없음 | `test_handle_alert_success/no_alert` 통과 확인 |

### 회귀 확인 명령

```bash
# 기존 테스트 전체 통과 확인
pytest tests/test_main.py tests/test_validation.py tests/test_exceptions.py -v

# 신규 테스트 실행
pytest tests/test_recovery.py tests/test_main_recovery.py -v

# 전체 테스트
pytest tests/ -v
```

### 기존 E2E 파일 업데이트

현재 E2E 테스트 파일 없음 (system-analysis.md 확인: "통합/E2E: 없음"). 기존 E2E 파일 업데이트 불필요.

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-08 에러 리커버리 테스트 명세 |
