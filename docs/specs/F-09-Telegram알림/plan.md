# F-09 Telegram 알림 -- 구현 계획서

## 1. 개요

- 기능: F-09 Telegram 알림
- 의존성: F-03 완료
- 소요 시간: 2~3시간
- 변경 유형: Brownfield (신규 모듈 추가 + 기존 파일 수정)
- 참조
  - 설계서: docs/specs/F-09-Telegram알림/change-design.md
  - 테스트 명세: docs/specs/F-09-Telegram알림/test-spec.md
  - 인수조건: docs/project/features.md #F-09

### 인수조건 요약

- [ ] Telegram Bot Token + Chat ID를 .env 또는 CLI로 설정
- [ ] 예약 성공 시 열차 정보 포함 Telegram 메시지 발송
- [ ] 예약 실패(최대 재시도 초과) 시 실패 알림 발송
- [ ] Telegram 설정이 없으면 알림 기능 비활성화 (에러 없이 무시)
- [ ] 네트워크 오류로 알림 발송 실패 시 예약 프로세스에 영향 없음

## 2. 인프라 준비

추가 의존성 없음. `urllib.request`는 Python 표준 라이브러리이므로 `requirements.txt` 변경 불필요.

- [ ] [shared] `.env.example`에 `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` 항목 추가

## 3. 구현

### Phase 1: notifier.py 신규 작성

- [ ] [shared] `srt_reservation/notifier.py` 신규 작성
  - `TelegramNotifier` 클래스 구현
    - 클래스 상수: `TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"`
    - `__init__(self, token=None, chat_id=None)`: token/chat_id 없으면 `os.environ.get("TELEGRAM_TOKEN"/"TELEGRAM_CHAT_ID")` 참조
    - `is_configured(self) -> bool`: token과 chat_id 모두 비어있지 않은 문자열일 때 True
    - `send_message(self, text: str) -> bool`: urllib.request로 POST 요청, 10초 타임아웃, 모든 예외 내부 catch 후 False 반환 + WARNING 로그
    - `notify_success(self, train_info: str) -> bool`: `"[SRT 예약 성공]\n열차: {train_info}"` 포맷 후 `send_message()` 호출
    - `notify_failure(self, reason: str) -> bool`: `"[SRT 예약 실패]\n사유: {reason}"` 포맷 후 `send_message()` 호출

### Phase 2: main.py 수정

- [ ] [backend] `srt_reservation/main.py` 수정 (4곳, 총 +8행)
  - import 추가: `from srt_reservation.notifier import TelegramNotifier`
  - `__init__` 메서드 본문 끝(check_input() 직전)에 `self.notifier = TelegramNotifier()` 추가
  - `run()` 성공 분기: `if self.is_booked:` 블록에 `train_info` 구성 후 `self.notifier.notify_success(train_info)` 추가
  - `run()` 실패 분기: except 블록의 두 종료 경로(브라우저 복구 실패, 기타 예외)에 각각 `self.notifier.notify_failure(...)` 추가

- [ ] [shared] `srt_reservation/__init__.py` 수정
  - `from .notifier import TelegramNotifier` re-export 추가

## 4. 테스트

- [ ] [shared] `tests/test_notifier.py` 신규 작성 (25개 케이스)
  - `TelegramNotifier.__init__`: 직접 인자 전달 / 환경변수 로드 / 환경변수 미설정 (3개)
  - `is_configured()`: token+chat_id 모두 설정 / token만 / chat_id만 / 둘 다 미설정 / 빈 문자열 token / 빈 문자열 chat_id (6개)
  - `send_message()`: 정상 발송(HTTP 200) / 미설정 silent skip / URLError / HTTPError 400 / socket.timeout / RuntimeError / 요청 본문 검증(chat_id+text+parse_mode) / API URL 검증 (8개)
  - `notify_success()`: 메시지 포맷 검증 / 미설정 시 False 반환 (2개)
  - `notify_failure()`: 메시지 포맷 검증 / 미설정 시 False 반환 (2개)
  - Mock 전략: `unittest.mock.patch("urllib.request.urlopen")`, `patch.dict(os.environ, ...)`

- [ ] [shared] `tests/test_main.py` 기존 파일에 `TestSRTNotifierIntegration` 클래스 추가 (10개 케이스)
  - `SRT.run()` 예약 성공 시 `notify_success()` 1회 호출 확인 (인자에 출발역/도착역/날짜 포함)
  - `SRT.run()` 예약 실패(RecoveryError) 시 `notify_failure()` 1회 호출 확인
  - `SRT.run()` 브라우저 복구 실패 시 `notify_failure()` 1회 호출 확인
  - `SRT.run()` 알림 미설정 시 예약 성공 정상 동작 (urlopen 호출 횟수 0)
  - `SRT.run()` 알림 발송 실패 시 예약 프로세스 영향 없음 (예외 전파 없음)
  - `SRT.__init__` notifier 속성이 TelegramNotifier 인스턴스인지 확인
  - E2E-1: 예약 성공 시 POST 요청 1회, 본문에 "[SRT 예약 성공]" 포함
  - E2E-2: 예약 실패 시 POST 요청 1회, 본문에 "[SRT 예약 실패]" 포함
  - E2E-3: 알림 미설정 시 예약 성공 정상 동작, urlopen 호출 없음
  - E2E-4: urlopen URLError 시 예약 성공 유지, WARNING 로그 출력

## 5. 검증

- [ ] [shared] 기존 F-01~F-08 회귀 테스트 전체 통과 확인
  - `TestSRTInputValidation` 전체 통과 (SRT 생성자 시그니처 변경 없음 확인)
  - `TestSRTBookTicket`, `TestSRTReserveTicket`, `TestSRTCheckResult`, `TestSRTRefreshResult`, `TestSRTAlertHandling`, `TestSRTLogin`, `TestSRTLoginInfo` 전체 통과
  - 확인 명령: `pytest tests/ -v`

## 태스크 의존성

```
Phase 1 (notifier.py) ──▶ Phase 2 (main.py 수정) ──▶ 테스트 작성 ──▶ 검증
                                                    ↑
                         .env.example 수정 ─────────┘
```

## 병렬 실행 판단

- Agent Team 권장: No
- 근거: 이 기능은 백엔드 전용이며 프론트엔드 변경이 없다. notifier.py 완성 후 main.py를 수정해야 하므로 순차 실행이 적합하다. 테스트는 구현과 같은 Agent가 함께 작성한다.
