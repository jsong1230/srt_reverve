# F-09 Telegram 알림 -- 테스트 명세

## 참조

- 설계서: docs/specs/F-09-Telegram알림/change-design.md
- 인수조건: docs/project/features.md #F-09

## 테스트 전략

- **유닛 테스트**: `TelegramNotifier` 클래스의 설정 확인, 메시지 포맷팅, API 호출 (mock)
- **통합 테스트**: `main.py`의 `run()` 메서드에서 알림 발송 (mock notifier)
- **Mock 대상**: `urllib.request.urlopen` (Telegram Bot API 호출)

## 단위 테스트: TelegramNotifier

### 테스트 파일: `tests/test_notifier.py`

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `__init__` | token과 chat_id를 인자로 전달 | `token="abc", chat_id="123"` | `self.token == "abc"`, `self.chat_id == "123"` |
| `__init__` | 인자 없이 환경변수에서 로드 | 환경변수 `TELEGRAM_TOKEN=abc`, `TELEGRAM_CHAT_ID=123` | `self.token == "abc"`, `self.chat_id == "123"` |
| `__init__` | 환경변수 미설정 시 | 환경변수 없음 | `self.token is None`, `self.chat_id is None` |
| `is_configured` | 둘 다 설정된 경우 | `token="abc", chat_id="123"` | `True` |
| `is_configured` | token만 설정된 경우 | `token="abc", chat_id=None` | `False` |
| `is_configured` | chat_id만 설정된 경우 | `token=None, chat_id="123"` | `False` |
| `is_configured` | 둘 다 미설정 | `token=None, chat_id=None` | `False` |
| `is_configured` | token이 빈 문자열 | `token="", chat_id="123"` | `False` |
| `is_configured` | chat_id가 빈 문자열 | `token="abc", chat_id=""` | `False` |
| `send_message` | 정상 발송 (HTTP 200) | `text="테스트"`, mock urlopen 200 응답 | `True`, urlopen 1회 호출 |
| `send_message` | 미설정 시 silent skip | `token=None`, `text="테스트"` | `False`, urlopen 호출 없음 |
| `send_message` | 네트워크 오류 (URLError) | mock urlopen이 `URLError` 발생 | `False`, WARNING 로그 출력, 예외 전파 없음 |
| `send_message` | HTTP 에러 (HTTPError 400) | mock urlopen이 `HTTPError(400)` 발생 | `False`, WARNING 로그 출력, 예외 전파 없음 |
| `send_message` | 타임아웃 | mock urlopen이 `socket.timeout` 발생 | `False`, WARNING 로그 출력, 예외 전파 없음 |
| `send_message` | 예상치 못한 예외 (RuntimeError 등) | mock urlopen이 `RuntimeError` 발생 | `False`, WARNING 로그 출력, 예외 전파 없음 |
| `send_message` | 요청 본문 검증 | `text="테스트 메시지"` | urlopen에 전달된 Request 본문에 `chat_id`, `text`, `parse_mode` 포함 |
| `send_message` | API URL 검증 | `token="mytoken"`, `text="테스트"` | urlopen에 전달된 URL이 `https://api.telegram.org/botmytoken/sendMessage` |
| `notify_success` | 성공 메시지 포맷 검증 | `train_info="08시 이후 동탄 -> 동대구 (20260315)"` | `send_message` 호출 인자가 `"[SRT 예약 성공]\n열차: 08시 이후 동탄 -> 동대구 (20260315)"` |
| `notify_failure` | 실패 메시지 포맷 검증 | `reason="최대 재시도 횟수 초과"` | `send_message` 호출 인자가 `"[SRT 예약 실패]\n사유: 최대 재시도 횟수 초과"` |
| `notify_success` | 미설정 시 | `token=None` | `False` 반환, 예외 없음 |
| `notify_failure` | 미설정 시 | `token=None` | `False` 반환, 예외 없음 |

## 통합 테스트: main.py 알림 연동

### 테스트 파일: `tests/test_main.py` (기존 파일에 클래스 추가)

| API | 시나리오 | 입력 | 예상 결과 |
|-----|----------|------|-----------|
| `SRT.run()` | 예약 성공 시 성공 알림 발송 | mock driver (예약 성공 시뮬레이션) | `notifier.notify_success()` 1회 호출, 인자에 출발역/도착역/날짜 포함 |
| `SRT.run()` | 예약 실패(예외) 시 실패 알림 발송 | mock driver (RecoveryError 발생) | `notifier.notify_failure()` 1회 호출, 인자에 에러 메시지 포함 |
| `SRT.run()` | 브라우저 복구 실패 시 실패 알림 발송 | mock driver (세션 끊김 + 복구 실패) | `notifier.notify_failure()` 1회 호출 |
| `SRT.run()` | 알림 미설정 시 예약 성공 정상 동작 | TELEGRAM_TOKEN 미설정, mock driver (예약 성공) | 예약 성공, `notifier.send_message()` 호출되지만 `False` 반환, 예외 없음 |
| `SRT.run()` | 알림 발송 실패 시 예약 프로세스 영향 없음 | mock notifier가 내부에서 예외 발생하도록 설정 | 예약 성공 정상 반환, 알림 실패가 예외를 전파하지 않음 |
| `SRT.__init__` | notifier 속성이 TelegramNotifier 인스턴스인지 확인 | 일반 SRT 생성 | `isinstance(srt.notifier, TelegramNotifier) == True` |

## 경계 조건 / 에러 케이스

### TelegramNotifier 설정

- `TELEGRAM_TOKEN`만 설정, `TELEGRAM_CHAT_ID` 미설정: `is_configured() == False`, `send_message()` 호출 시 `False` 반환, 로그 없음
- `TELEGRAM_TOKEN` 빈 문자열 (`""`): `is_configured() == False`
- `TELEGRAM_TOKEN` 공백 문자열 (`"  "`): `is_configured()`는 `True` (공백은 비어있지 않은 문자열). 실제 API 호출 시 Telegram이 401 에러 반환 -> `send_message()`가 `False` 반환 + WARNING 로그 `"Telegram 알림 발송 실패: HTTP Error 401: Unauthorized"`

### send_message 에러 처리

- Telegram API 응답이 JSON이 아닌 경우: `json.JSONDecodeError` 내부 catch, `False` 반환 + WARNING 로그 `"Telegram 알림 발송 실패: Expecting value: ..."`
- 매우 긴 메시지 (4096자 초과, Telegram 제한): Telegram API가 에러 반환 -> `False` 반환 + WARNING 로그
- 잘못된 chat_id (숫자가 아닌 문자열): Telegram API가 400 에러 반환 -> `False` 반환 + WARNING 로그 `"Telegram 알림 발송 실패: HTTP Error 400: Bad Request"`

### main.py 통합

- `SRT.__init__`에서 `TelegramNotifier()` 생성 시 환경변수 접근 실패: 표준 라이브러리 `os.environ.get()`은 실패하지 않으므로 해당 없음
- `run()` 메서드에서 `self.notifier.notify_success()` 호출 시 `notifier`가 `None`: 발생하지 않음 (`__init__`에서 항상 생성). 단, 외부에서 `srt.notifier = None`으로 설정한 경우를 대비한 방어 코드는 불필요 (사용자 오류)

## E2E 시나리오

### E2E-1: 예약 성공 시 Telegram 알림 발송

1. 환경변수 `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` 설정
2. SRT 인스턴스 생성 및 `run()` 실행 (mock driver, 예약 성공 시뮬레이션)
3. 예약 성공 (`is_booked == True`)
4. Telegram API 호출 검증 (mock): POST 요청 1회, 본문에 `"[SRT 예약 성공]"` 포함
5. `run()` 정상 반환 (예외 없음)

### E2E-2: 예약 실패 시 Telegram 알림 발송 후 예외 전파

1. 환경변수 `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` 설정
2. SRT 인스턴스 생성 및 `run()` 실행 (mock driver, RecoveryError 발생 시뮬레이션)
3. `check_result()`에서 `RecoveryError` 발생
4. Telegram API 호출 검증 (mock): POST 요청 1회, 본문에 `"[SRT 예약 실패]"` 포함
5. `run()`이 예외를 재전파 (`RecoveryError` 또는 래핑된 예외)

### E2E-3: 알림 미설정 시 예약 성공 정상 동작

1. 환경변수 `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` **미설정**
2. SRT 인스턴스 생성 (`notifier.is_configured() == False`)
3. `run()` 실행 (mock driver, 예약 성공 시뮬레이션)
4. 예약 성공 (`is_booked == True`)
5. Telegram API 호출 없음 (urlopen mock 호출 횟수 0)
6. `run()` 정상 반환, 에러 로그 없음

### E2E-4: 알림 발송 실패 시 예약 프로세스 영향 없음

1. 환경변수 `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` 설정
2. SRT 인스턴스 생성
3. mock urlopen이 `URLError("네트워크 연결 실패")` 발생하도록 설정
4. `run()` 실행 (mock driver, 예약 성공 시뮬레이션)
5. 예약 성공 (`is_booked == True`)
6. Telegram 알림 발송 시도 -> 실패 -> WARNING 로그 `"Telegram 알림 발송 실패: 네트워크 연결 실패"`
7. `run()` 정상 반환 (예외 없음, 예약 성공 상태 유지)

### E2E-5: 재실행 시 알림 상태 독립성

1. 환경변수 설정 상태에서 첫 번째 `run()` 실행 -> 예약 실패 -> 실패 알림 발송
2. 새 SRT 인스턴스 생성 후 두 번째 `run()` 실행 -> 예약 성공 -> 성공 알림 발송
3. 각 실행의 알림이 독립적으로 동작 (이전 실행 상태에 영향받지 않음)

## 회귀 테스트

| 기존 기능 | 영향 여부 | 검증 방법 |
|-----------|-----------|-----------|
| `SRT.__init__` (입력 검증) | 낮음 -- `self.notifier` 속성 추가만 | 기존 `TestSRTInputValidation` 전체 통과 확인 |
| `SRT.run()` (예약 프로세스) | 중간 -- 성공/실패 분기에 알림 호출 추가 | 기존 `TestSRTCheckResult` 통과 확인. `run()` 테스트는 기존에 없으므로 신규 통합 테스트로 커버 |
| `SRT.book_ticket()` | 없음 -- 수정하지 않음 | 기존 `TestSRTBookTicket` 전체 통과 확인 |
| `SRT.reserve_ticket()` | 없음 -- 수정하지 않음 | 기존 `TestSRTReserveTicket` 전체 통과 확인 |
| `SRT.check_result()` | 없음 -- 수정하지 않음 | 기존 `TestSRTCheckResult` 전체 통과 확인 |
| `SRT.refresh_result()` | 없음 -- 수정하지 않음 | 기존 `TestSRTRefreshResult` 전체 통과 확인 |
| `SRT.handle_alert()` | 없음 -- 수정하지 않음 | 기존 `TestSRTAlertHandling` 전체 통과 확인 |
| `SRT.login()` | 없음 -- 수정하지 않음 | 기존 `TestSRTLogin` 전체 통과 확인 |
| `SRT.set_log_info()` | 없음 -- 수정하지 않음 | 기존 `TestSRTLoginInfo` 전체 통과 확인 |

### 기존 테스트 파일 영향

| 테스트 파일 | 수정 필요 | 이유 |
|-------------|-----------|------|
| `tests/test_main.py` | 아니오 | SRT 생성자 시그니처 변경 없음. `self.notifier` 추가는 기존 테스트에 영향 없음 (환경변수 미설정 시 `is_configured() == False`로 silent skip) |
| `tests/test_validation.py` | 아니오 | 변경 없음 |
| `tests/test_exceptions.py` | 아니오 | 변경 없음 |

## Mock 전략

### urllib.request.urlopen Mock

```python
# 성공 응답
mock_response = Mock()
mock_response.read.return_value = b'{"ok": true, "result": {}}'
mock_response.__enter__ = Mock(return_value=mock_response)
mock_response.__exit__ = Mock(return_value=False)

with patch("urllib.request.urlopen", return_value=mock_response):
    result = notifier.send_message("테스트")
    assert result is True

# 실패 응답 (네트워크 오류)
from urllib.error import URLError
with patch("urllib.request.urlopen", side_effect=URLError("연결 실패")):
    result = notifier.send_message("테스트")
    assert result is False

# 실패 응답 (HTTP 에러)
from urllib.error import HTTPError
with patch("urllib.request.urlopen", side_effect=HTTPError(None, 400, "Bad Request", {}, None)):
    result = notifier.send_message("테스트")
    assert result is False
```

### 환경변수 Mock

```python
# 환경변수 설정
with patch.dict(os.environ, {"TELEGRAM_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "12345"}):
    notifier = TelegramNotifier()
    assert notifier.is_configured() is True

# 환경변수 미설정
with patch.dict(os.environ, {}, clear=True):
    notifier = TelegramNotifier()
    assert notifier.is_configured() is False
```

### SRT.run() 통합 테스트 Mock

```python
# 예약 성공 + 알림 검증
srt = SRT("동탄", "동대구", "20240115", "08")
srt.notifier = Mock(spec=TelegramNotifier)
srt.notifier.notify_success.return_value = True

# mock driver 및 메서드 설정...
with patch.object(srt, 'run_driver'), \
     patch.object(srt, 'login'), \
     patch.object(srt, 'check_login', return_value=True), \
     patch.object(srt, 'go_search'), \
     patch.object(srt, 'check_result'):
    srt.is_booked = True
    srt.run("test_id", "test_pw")

srt.notifier.notify_success.assert_called_once()
```
