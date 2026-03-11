# F-08 에러 리커버리 -- 구현 계획서

## 1. 개요

- 기능명: F-08 에러 리커버리
- 의존성: F-01 (SRT 로그인), F-03 (자동 새로고침 및 예약) 완료
- 마일스톤: M1
- 소요 시간 추정: 4~5시간 (복구 전략 구현, 통합 테스트, 모든 에러 경로 커버)

## 2. 참조

- 설계서: docs/specs/F-08-에러리커버리/change-design.md
- 인수조건: docs/project/features.md #F-08
- 테스트 명세: docs/specs/F-08-에러리커버리/test-spec.md

## 3. 태스크 목록

### Phase 1: 인프라 준비

- (추가 외부 의존성 없음 -- 표준 라이브러리 및 기존 selenium 사용)

### Phase 2: 구현

- [ ] [shared] srt_reservation/recovery.py 신규 모듈 작성
  - RecoveryError(Exception) 클래스 정의
  - RecoveryContext 클래스: network_retry_count, session_retry_count, browser_retry_count, history 속성 + record(), reset_network_count(), get_summary() 메서드
  - NetworkErrorRecovery 클래스 (max_retries=3, base_delay=5.0, max_delay=30.0): should_retry(), wait_before_retry(), execute_retry() 메서드
    - wait_before_retry: 지수 백오프 (`base_delay * (2 ** retry_count)`) + +-1초 지터, max_delay 상한 적용
  - SessionRecovery 클래스 (max_retries=2): is_session_expired(), recover() 메서드
    - is_session_expired: driver.current_url에 "selectLoginForm" 포함 여부 확인, 예외 시 False 반환
    - recover: login() -> check_login() -> go_search() 순 호출, 성공 True/실패 False 반환
  - BrowserRecovery 클래스 (max_retries=1): is_browser_crashed(), recover() 메서드
    - is_browser_crashed: driver.current_url 접근 시도, InvalidSessionIdException/WebDriverException 시 True
    - recover: close_driver() (예외 무시) -> run_driver() -> login() -> check_login() -> go_search()
  - 모듈 레벨 유틸 함수: is_network_error(exc), is_session_error(exc)
    - is_network_error: TimeoutException, ConnectionError, URLError, WebDriverException("timeout" 포함) 판별
    - is_session_error: UnexpectedAlertPresentException 판별

- [ ] [backend] srt_reservation/main.py 수정
  - 상단에 recovery 모듈 import 추가 (RecoveryContext, NetworkErrorRecovery, SessionRecovery, BrowserRecovery, is_network_error, is_session_error, RecoveryError)
  - __init__() 내부에 복구 컨텍스트 초기화 추가:
    - self._recovery_context = RecoveryContext()
    - self._network_recovery = NetworkErrorRecovery(max_retries=3)
    - self._session_recovery = SessionRecovery(max_retries=2)
    - self._browser_recovery = BrowserRecovery(max_retries=1)
  - check_result() 내부 에러 처리 개선:
    - for 루프 내 예외 처리에 세션 만료 감지 + SessionRecovery.recover() 호출 추가
    - 네트워크 오류 감지 + NetworkErrorRecovery.should_retry() / wait_before_retry() 호출 추가
    - 성공 시 reset_network_count() 호출
    - RecoveryError 발생 시 상위로 전파
  - run() 최상위 에러 처리 개선:
    - RecoveryError except 블록 추가: logger.error + get_summary() 로그 후 raise
    - 브라우저 세션 끊김 처리 블록에 BrowserRecovery.recover() 호출 + 복구 후 check_result() 재시작 추가
    - 복구 실패 시 RecoveryError 발생
  - 로깅 추가: 재시도 횟수, 복구 이력 (WARNING/INFO/ERROR 레벨 구분)

- [ ] [backend] srt_reservation/__init__.py 수정
  - RecoveryError re-export 추가: `from srt_reservation.recovery import RecoveryError`

### Phase 3: 테스트

- [ ] [shared] tests/test_recovery.py 신규 작성
  - RecoveryContext: 5개 케이스 (초기 상태, 이력 기록, 타임스탬프 포함, 카운터 리셋, 요약 문자열)
  - NetworkErrorRecovery: 9개 케이스 (should_retry 경계값, 대기 시간 1~3차, 상한, execute_retry 성공/실패, 커스텀 max_retries)
  - SessionRecovery: 7개 케이스 (만료 감지 URL, 유효 URL, driver 예외 시 False, 복구 성공/실패, 최대 초과, 커스텀 max_retries)
  - BrowserRecovery: 7개 케이스 (크래시 감지 2종, 정상, 복구 성공/실패, 최대 초과, close_driver 예외 무시)
  - 유틸 함수: 8개 케이스 (is_network_error 5종, is_session_error 2종, None 처리)
  - 경계 조건: 최소 35개 케이스

- [ ] [shared] tests/test_main_recovery.py 신규 작성
  - check_result() 복구 통합 5개 케이스:
    - 타임아웃 1회 후 성공
    - 타임아웃 3회 후 성공
    - 타임아웃 4회 (최대 초과) -> RecoveryError
    - 세션 만료 -> 재로그인 -> 성공
    - 세션 만료 -> 재로그인 실패 -> RecoveryError
  - run() 복구 통합 4개 케이스:
    - 브라우저 크래시 -> 복구 -> 성공
    - 브라우저 크래시 -> 복구 실패 -> RecoveryError
    - RecoveryError 전파
    - 일반 예외 전파
  - 로깅 검증 5개 케이스:
    - 네트워크 재시도 로그 ("네트워크 오류 감지" 포함)
    - 세션 복구 로그 ("세션 만료 감지", "세션 복구 성공" 포함)
    - 브라우저 복구 로그 ("브라우저 연결 끊김 감지" 포함)
    - 복구 이력 요약 로그 ("[복구 이력]" 포함)
    - 최대 초과 로그 ("복구 실패로 프로세스를 종료합니다" 포함)
  - 총 14개 케이스

- [ ] [shared] tests/test_integration_e2e_recovery.py 신규 작성
  - E2E-1: 네트워크 타임아웃 -> 자동 재시도 -> 예약 성공
  - E2E-2: 세션 만료 -> 재로그인 -> 검색 재개 -> 예약 성공
  - E2E-3: 브라우저 크래시 -> WebDriver 재초기화 -> 프로세스 재시작
  - E2E-4: 최대 재시도 초과 -> 에러 메시지 + RecoveryError 전파
  - E2E-5: 복합 장애 -> 네트워크 재시도 후 세션 만료 -> 재로그인 -> 성공
  - 총 5개 E2E 시나리오

### Phase 4: 검증

- [ ] [shared] 기존 F-01~F-06 테스트 전체 통과 확인 (회귀 테스트)
  - `pytest tests/test_main.py -v` -- check_result 정상 경로 + 기존 예외 처리 호환성
  - `pytest tests/test_validation.py -v` -- 역 목록 무결성
  - `pytest tests/test_exceptions.py -v` -- 예외 클래스 호환성

## 4. 태스크 의존성

```
Phase 2 (구현)
  recovery.py 신규 작성 (독립 모듈, 외부 의존성 없음)
    |
    v
  main.py 수정 (recovery.py import 후 진행)
    |
    v
  __init__.py 수정 (recovery.py 완료 후 진행)
  |
  v
Phase 3 (테스트)
  test_recovery.py (recovery.py 완료 후 작성 가능)
    |
    v
  test_main_recovery.py (main.py 수정 + test_recovery.py 완료 후)
    |
    v
  test_integration_e2e_recovery.py (전체 구현 완료 후)
  |
  v
Phase 4 (검증)
```

## 5. 병렬 실행 판단

- Agent Team 권장: No
- 근거: recovery.py가 main.py 수정의 전제 조건이므로 순차 구현이 필요함. recovery.py 인터페이스(RecoveryContext, 각 Recovery 클래스 반환값 계약)가 확정된 후에야 main.py 수정과 테스트 작성이 가능. F-07과 F-08은 수정 파일이 겹치지 않으므로 두 기능 간 병렬 개발은 가능하나, 각 기능 내부는 순차 진행.

## 6. 구현 주의사항

- SRT 클래스 생성자 시그니처 변경 없음 (기존 9개 테스트 클래스 호환성 유지 필수)
- check_result()와 run() 메서드 시그니처 변경 없음
- RecoveryError 메시지 형식 정확히 준수:
  - 네트워크 최대 초과: "네트워크 오류 복구 실패: 최대 재시도 횟수(3회) 초과"
  - 세션 복구 실패: "세션 복구 실패: 최대 재시도 초과"
  - 브라우저 복구 실패: "브라우저 복구 실패"
  - 브라우저 복구 후 재시도 실패: "브라우저 복구 후 재시도 실패"
- get_summary() 형식 준수: "[복구 이력] 네트워크 재시도: {n}회, 세션 복구: {m}회, 브라우저 복구: {k}회"
- wait_before_retry에서 time.sleep 사용 (테스트에서 @patch('srt_reservation.recovery.time.sleep')으로 Mock 가능하도록 모듈 레벨 import)
- BrowserRecovery.recover()에서 close_driver() 예외는 반드시 무시하고 run_driver() 진행
- SessionRecovery.is_session_expired()에서 driver가 None이거나 WebDriverException 발생 시 False 반환 (예외 전파 안 함)

## 7. F-07과의 관계

F-07과 F-08은 병렬 그룹 A에 속하며 상호 의존성이 없음:
- F-08은 F-07의 Config 클래스를 사용하지 않음
- F-07은 F-08의 RecoveryError를 사용하지 않음
- 수정 파일 충돌 없음 (F-07: config.py/util.py/quickstart.py/manual_login.py, F-08: recovery.py/main.py/__init__.py)
- 두 기능이 완료된 후 통합 시 main.py에서 Config와 Recovery가 각각 독립적으로 동작함

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-03-12 | 초안 작성 |
