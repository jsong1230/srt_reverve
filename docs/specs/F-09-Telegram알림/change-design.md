# F-09 Telegram 알림 -- 변경 설계서

## 1. 참조

- 인수조건: docs/project/features.md #F-09
- 시스템 분석: docs/system/system-analysis.md
- CLI 설계: docs/system/cli-design.md (환경변수 폴백 섹션)
- F-07 설정 관리: docs/specs/F-07-설정관리/change-design.md (Config 클래스)
- 마일스톤: M2 (의존성: F-03 완료)

## 2. 개요

### 기능 목표

예약 성공 또는 실패(최대 재시도 초과) 시 Telegram Bot API를 통해 사용자에게 메시지를 발송한다. 알림 설정이 없으면 기능이 비활성화되며, 알림 발송 실패가 예약 프로세스에 영향을 주지 않는다.

### 인수조건 (features.md #F-09)

- [ ] Telegram Bot Token + Chat ID를 .env 또는 CLI로 설정
- [ ] 예약 성공 시 열차 정보 포함 Telegram 메시지 발송
- [ ] 예약 실패(최대 재시도 초과) 시 실패 알림 발송
- [ ] Telegram 설정이 없으면 알림 기능 비활성화 (에러 없이 무시)
- [ ] 네트워크 오류로 알림 발송 실패 시 예약 프로세스에 영향 없음

### 의존성

- F-03 (자동 새로고침 및 예약): 예약 성공/실패 시점에 알림 호출
- F-07 (설정 관리): 환경변수(`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`) 로드. F-07의 Config 클래스는 이미 cli-design.md에서 이 두 환경변수를 M2 대상으로 정의함

## 3. 현황 분석

### 현재 알림 체계

현재 예약 결과는 **콘솔 로그에만 출력**된다.

- 예약 성공 시: `logger.info("예약 성공!")` (main.py:731)
- 예약 프로세스 완료 시: `logger.info("예약 프로세스 완료")` (main.py:874)
- 예약 실패 시: `logger.warning("예약을 완료하지 못했습니다.")` (main.py:876)
- 에러 리커버리 실패 시: `RecoveryError` 예외 발생 (recovery.py:108~110)

외부 알림 채널(Telegram, Slack, Email 등)은 미구현 상태이다.

### 관련 코드 분석

#### 예약 성공 경로

```
check_result() -> _check_result_once() -> book_ticket() -> is_booked = True
                                       -> reserve_ticket() -> is_booked = True
```

- `book_ticket()` (main.py:703~737): 일반석 예약 성공 시 `self.is_booked = True` 설정 후 `self.driver` 반환
- `reserve_ticket()` (main.py:755~768): 예약 대기 성공 시 `self.is_booked = True` 설정 후 `True` 반환
- `run()` (main.py:839~901): `check_result()` 반환 후 `self.is_booked` 확인하여 완료 로그 출력

#### 예약 실패 경로

- `check_result()` (main.py:800~837): `RecoveryError` 예외 발생 시 상위로 전파
- `run()` (main.py:878~896): 예외 catch 후 브라우저 복구 시도, 실패 시 `RuntimeError` 발생

### 외부 API 접속 정보

- **Telegram Bot API**: `https://api.telegram.org/bot{TOKEN}/sendMessage`
- HTTP 라이브러리: Python 표준 라이브러리 `urllib.request` 사용 (추가 의존성 불필요)
- 인증: Bot Token을 URL 경로에 포함 (Bearer Token 방식 아님)

## 4. 변경 범위

- 변경 유형: 신규 추가 + 기존 수정
- 영향 받는 모듈: `main.py` (SRT 클래스), `__init__.py` (re-export)

## 5. 아키텍처 결정

### 결정 1: HTTP 클라이언트 라이브러리

- **선택지**: A) `requests` 라이브러리 / B) `urllib.request` (표준 라이브러리)
- **결정**: B) `urllib.request`
- **근거**: Telegram Bot API의 `sendMessage` 엔드포인트 호출은 단순한 POST 요청 1건이다. 이를 위해 `requests` 의존성을 추가하는 것은 과도하다. 표준 라이브러리로 충분히 구현 가능하며, `requirements.txt` 변경이 불필요하다.

### 결정 2: 알림 모듈 위치

- **선택지**: A) `srt_reservation/notifier.py` 신규 모듈 / B) `main.py`에 메서드 추가
- **결정**: A) `srt_reservation/notifier.py` 신규 모듈
- **근거**: 관심사 분리. SRT 클래스는 이미 ~900줄의 God Object이므로 알림 책임을 별도 모듈로 분리한다. 향후 Slack, Discord 등 다른 알림 채널 추가 시 확장 용이.

### 결정 3: SRT 클래스와 Notifier 연결 방식

- **선택지**: A) SRT 클래스 `__init__`에서 TelegramNotifier 인스턴스 생성 / B) 엔트리포인트에서 주입
- **결정**: A) SRT 클래스 `__init__`에서 생성
- **근거**: 알림은 SRT 클래스 내부의 `book_ticket()`, `reserve_ticket()`, `check_result()` 등 여러 메서드에서 호출된다. 외부 주입 시 SRT 생성자 시그니처 변경이 필요하며, 기존 테스트 전면 수정이 발생한다. 대신 환경변수 기반으로 자동 구성하여 기존 시그니처를 유지한다.

### 결정 4: 환경변수 로드 방식

- **선택지**: A) `os.environ.get()` 직접 사용 / B) F-07 Config 클래스 경유
- **결정**: A) `os.environ.get()` 직접 사용
- **근거**: F-07의 Config 클래스는 엔트리포인트(`quickstart.py`)에서 CLI 인자와 .env를 병합하는 역할이다. `TELEGRAM_TOKEN`과 `TELEGRAM_CHAT_ID`는 CLI 인자 대응 없이 환경변수 전용이므로(cli-design.md 참조: "(코드 내 설정)"), TelegramNotifier가 직접 `os.environ.get()`으로 읽는 것이 자연스럽다. F-07의 `.env` 파일 로드(`python-dotenv`)가 이미 프로세스 시작 시 환경변수를 설정하므로 호환성 문제 없음.

### 결정 5: 알림 발송 타이밍

- **선택지**: A) `book_ticket()`/`reserve_ticket()` 성공 직후 / B) `run()` 메서드 최종 단계
- **결정**: B) `run()` 메서드 최종 단계
- **근거**: `run()` 메서드가 전체 프로세스를 오케스트레이션하며, 성공/실패의 최종 판단 지점이다. `book_ticket()`은 잔여석 없으면 `None`을 반환하고 재시도하므로 중간 단계에서 알림을 보내면 잘못된 타이밍에 발송될 수 있다. `run()`에서 `self.is_booked` 확인 후 성공 알림, 예외 catch 블록에서 실패 알림을 보내면 정확한 타이밍이 보장된다.

## 6. 상세 설계

### 6.1 신규 모듈: `srt_reservation/notifier.py`

#### TelegramNotifier 클래스

```python
class TelegramNotifier:
    """Telegram Bot API를 통한 알림 발송"""

    TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token: str | None = None, chat_id: str | None = None):
        """
        :param token: Telegram Bot Token (None이면 환경변수 TELEGRAM_TOKEN 참조)
        :param chat_id: Telegram Chat ID (None이면 환경변수 TELEGRAM_CHAT_ID 참조)
        """
```

#### 메서드 설계

**`__init__(self, token=None, chat_id=None)`**

- `token`이 `None`이면 `os.environ.get("TELEGRAM_TOKEN")` 참조
- `chat_id`가 `None`이면 `os.environ.get("TELEGRAM_CHAT_ID")` 참조
- 둘 다 설정되어야 `is_configured() == True`

**`is_configured(self) -> bool`**

- 반환: `self.token`과 `self.chat_id`가 모두 비어있지 않은 문자열인 경우 `True`
- `None`, 빈 문자열(`""`) 모두 `False`로 처리

**`send_message(self, text: str) -> bool`**

- `is_configured()`가 `False`이면 즉시 `False` 반환 (로그 없음, silent skip)
- Telegram Bot API에 POST 요청 발송
- 요청 본문: `{"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}`
- 성공 시 `True` 반환
- 실패 시 (네트워크 오류, HTTP 에러, JSON 파싱 오류 등 모든 예외) `False` 반환 + WARNING 로그
- 타임아웃: 10초 (알림 발송이 예약 프로세스를 지연시키지 않도록)

**`notify_success(self, train_info: str) -> bool`**

- 성공 메시지 포맷팅 후 `send_message()` 호출
- 메시지 포맷:

```
[SRT 예약 성공]
열차: {train_info}
```

- `train_info`는 호출자가 제공하는 문자열 (예: `"08:30 동탄 -> 동대구"`)
- 반환: `send_message()`의 반환값

**`notify_failure(self, reason: str) -> bool`**

- 실패 메시지 포맷팅 후 `send_message()` 호출
- 메시지 포맷:

```
[SRT 예약 실패]
사유: {reason}
```

- `reason`은 호출자가 제공하는 문자열 (예: `"최대 재시도 횟수 초과"`)
- 반환: `send_message()`의 반환값

#### 에러 처리 원칙

모든 예외는 `send_message()` 내부에서 catch하여 `False`를 반환한다. 예약 프로세스에 예외가 전파되지 않는다.

```python
def send_message(self, text: str) -> bool:
    if not self.is_configured():
        return False
    try:
        # urllib.request로 POST 요청
        ...
        return True
    except Exception as e:
        logger.warning(f"Telegram 알림 발송 실패: {e}")
        return False
```

### 6.2 기존 파일 수정: `srt_reservation/main.py`

#### 변경 1: import 추가

```python
from srt_reservation.notifier import TelegramNotifier
```

#### 변경 2: `__init__` 메서드

기존 시그니처 **변경 없음**. 메서드 본문 마지막에 TelegramNotifier 인스턴스 생성 추가:

```python
# 기존 코드 끝 (self.check_input() 직전)
self.notifier = TelegramNotifier()

self.check_input()
```

`TelegramNotifier()`는 인자 없이 호출되어 환경변수에서 자동으로 설정을 읽는다. 환경변수가 없으면 `notifier.is_configured() == False`가 되어 모든 알림 호출이 무시된다.

#### 변경 3: `run()` 메서드

예약 성공 알림 추가:

```python
# 기존 코드 (main.py:872~876)
if self.is_booked:
    logger.info("예약 프로세스 완료")
    # 신규: 성공 알림
    train_info = f"{self.dpt_tm}시 이후 {self.dpt_stn} -> {self.arr_stn} ({self.dpt_dt})"
    self.notifier.notify_success(train_info)
else:
    logger.warning("예약을 완료하지 못했습니다.")
```

예약 실패 알림 추가 (예외 처리 블록):

```python
# 기존 코드 (main.py:878~896) 예외 처리 영역
except Exception as e:
    if _is_browser_session_lost(e):
        # ... 기존 브라우저 복구 로직 ...
        try:
            BrowserRecovery.recover(...)
            self.check_result()
            return
        except RecoveryError as recovery_err:
            logger.error(f"브라우저 복구 실패: {recovery_err}")
            # 신규: 실패 알림
            self.notifier.notify_failure(f"브라우저 복구 실패: {recovery_err}")
            raise RuntimeError(...) from e
    else:
        logger.error(f"예약 프로세스 중 오류 발생: {e}")
        # 신규: 실패 알림
        self.notifier.notify_failure(str(e))
    raise
```

`check_result()` 내부의 `RecoveryError` 전파 시에도 `run()`의 except 블록에서 처리되므로, `check_result()` 자체는 수정하지 않는다.

#### 변경 요약

| 위치 | 변경 내용 | 줄 수 변경 |
|------|-----------|------------|
| import 영역 | `from srt_reservation.notifier import TelegramNotifier` 추가 | +1 |
| `__init__` | `self.notifier = TelegramNotifier()` 추가 | +1 |
| `run()` 성공 분기 | `self.notifier.notify_success(train_info)` 추가 | +2 |
| `run()` 실패 분기 | `self.notifier.notify_failure(reason)` 추가 (2곳) | +4 |

### 6.3 기존 파일 수정: `srt_reservation/__init__.py`

```python
from .main import SRT
from .notifier import TelegramNotifier
```

### 6.4 .env.example 업데이트

기존 `.env.example`에 다음 항목 추가:

```bash
# Telegram 알림 설정 (선택사항)
# BotFather에서 봇을 생성하여 토큰을 획득하세요: https://t.me/BotFather
# Chat ID 확인: https://t.me/userinfobot
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
```

### 6.5 requirements.txt

**변경 없음.** `urllib.request`는 Python 표준 라이브러리이므로 추가 의존성 불필요.

## 7. 설정값

### 환경변수

| 환경변수 | 필수 여부 | 설명 | 예시 |
|----------|-----------|------|------|
| `TELEGRAM_TOKEN` | 선택 | Telegram Bot Token (BotFather에서 획득) | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID` | 선택 | Telegram Chat ID (@userinfobot으로 확인) | `123456789` |

### 비활성화 동작

- `TELEGRAM_TOKEN` 또는 `TELEGRAM_CHAT_ID` 중 하나라도 미설정이면 알림 기능 비활성화
- 비활성화 시 로그 메시지 없음 (silent skip)
- 예약 프로세스는 정상 진행

## 8. 메시지 포맷

### 예약 성공

```
[SRT 예약 성공]
열차: 08시 이후 동탄 -> 동대구 (20260315)
```

### 예약 실패 -- 에러 리커버리 초과

```
[SRT 예약 실패]
사유: 네트워크 오류: 최대 재시도(3회) 초과
```

### 예약 실패 -- 브라우저 복구 실패

```
[SRT 예약 실패]
사유: 브라우저 복구 실패: WebDriver 재초기화 오류
```

### 예약 실패 -- 기타 예외

```
[SRT 예약 실패]
사유: 로그인에 실패했습니다.
```

## 9. 시퀀스 흐름

### 예약 성공 시 알림 발송

```
사용자 --> quickstart.py
              |
              +--> SRT.__init__()
              |        |
              |        +--> TelegramNotifier()     # 환경변수에서 token/chat_id 로드
              |
              +--> srt.run(login_id, login_psw)
                     |
                     +--> run_driver() -> login() -> go_search()
                     |
                     +--> check_result()
                     |        |
                     |        +--> _check_result_once() -> book_ticket()
                     |        |        |
                     |        |        +--> is_booked = True
                     |        |
                     |        +--> return self.driver
                     |
                     +--> self.is_booked == True
                     |
                     +--> notifier.notify_success("08시 이후 동탄 -> 동대구 (20260315)")
                              |
                              +--> send_message() -> Telegram Bot API POST
                              |
                              +--> 성공: True / 실패: False + WARNING 로그
```

### 예약 실패 시 알림 발송

```
사용자 --> quickstart.py
              |
              +--> srt.run(login_id, login_psw)
                     |
                     +--> check_result()
                     |        |
                     |        +--> RecoveryError("네트워크 오류: 최대 재시도(3회) 초과")
                     |
                     +--> except Exception as e:
                     |        |
                     |        +--> notifier.notify_failure("네트워크 오류: 최대 재시도(3회) 초과")
                     |                 |
                     |                 +--> send_message() -> Telegram Bot API POST
                     |
                     +--> raise  (예외 재전파)
```

### 알림 미설정 시

```
TelegramNotifier()
    |
    +--> os.environ.get("TELEGRAM_TOKEN") == None
    +--> is_configured() == False
    |
notify_success("...")
    |
    +--> send_message() -> is_configured() == False -> return False (silent)
```

## 10. 영향 분석

### 기존 API 변경

| 대상 | 현재 | 변경 후 | 하위 호환성 |
|------|------|---------|-------------|
| `SRT.__init__()` | 11개 파라미터 | 시그니처 변경 없음. 내부에 `self.notifier` 속성 추가 | 완전 호환 |
| `SRT.run()` | 성공/실패 로그만 출력 | 성공/실패 시 Telegram 알림 추가 | 완전 호환 (알림은 부가 기능) |
| `book_ticket()` | 변경 없음 | 변경 없음 | 완전 호환 |
| `reserve_ticket()` | 변경 없음 | 변경 없음 | 완전 호환 |
| `check_result()` | 변경 없음 | 변경 없음 | 완전 호환 |

### 사이드 이펙트

1. **SRT 인스턴스 생성 시 환경변수 참조**: `TelegramNotifier()` 생성 시 `os.environ.get()`이 호출된다. 테스트 환경에서 `TELEGRAM_TOKEN` 환경변수가 설정되어 있지 않으면 `is_configured() == False`가 되어 알림이 비활성화된다. 기존 테스트에 영향 없음.

2. **`self.notifier` 속성 추가**: 기존 테스트에서 SRT 인스턴스의 속성을 직접 검사하는 코드는 없으므로 영향 없음.

3. **`run()` 메서드 동작 변경**: 성공/실패 분기에 `notifier.notify_*()` 호출이 추가된다. 이 메서드들은 내부에서 모든 예외를 catch하므로 기존 예외 흐름에 영향 없음.

4. **기존 `test_main.py` 영향**: `TestSRTCheckResult.test_check_result_with_booking_success`에서 `check_result()`를 직접 호출하고 있으나, `check_result()` 자체는 수정하지 않으므로 영향 없음. `run()` 메서드를 테스트하는 케이스는 없으므로 기존 테스트 수정 불필요.

## 11. 영향 범위

### 수정 필요 파일

| 파일 | 변경 내용 | 위험도 |
|------|-----------|--------|
| `srt_reservation/main.py` | import 추가, `__init__`에 notifier 생성, `run()`에 알림 호출 | 낮음 |
| `srt_reservation/__init__.py` | TelegramNotifier re-export | 낮음 |
| `.env.example` | TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 항목 추가 | 낮음 |

### 신규 생성 파일

| 파일 | 내용 |
|------|------|
| `srt_reservation/notifier.py` | TelegramNotifier 클래스 |
| `tests/test_notifier.py` | TelegramNotifier 유닛 테스트 |

### 변경 없는 파일

| 파일 | 이유 |
|------|------|
| `srt_reservation/exceptions.py` | 알림 관련 커스텀 예외 불필요 (모든 예외를 내부 catch) |
| `srt_reservation/validation.py` | 변경 불필요 |
| `srt_reservation/util.py` | CLI 인자 추가 없음 (환경변수 전용) |
| `srt_reservation/config.py` | F-07 Config 경유하지 않음 |
| `srt_reservation/recovery.py` | 변경 불필요 |
| `quickstart.py` | 변경 불필요 (SRT 클래스 내부에서 자동 구성) |
| `manual_login.py` | 변경 불필요 |
| `requirements.txt` | urllib.request는 표준 라이브러리 |

## 12. 공유 유틸리티 반환값 계약

### `TelegramNotifier.is_configured() -> bool`

- `True`: token과 chat_id 모두 비어있지 않은 문자열로 설정됨. 알림 발송 가능 상태.
- `False`: token 또는 chat_id 중 하나 이상이 `None`이거나 빈 문자열. 알림 비활성화 상태.

### `TelegramNotifier.send_message(text: str) -> bool`

- `True`: Telegram API 호출 성공 (HTTP 200 + JSON 응답의 `ok` 필드가 `true`)
- `False`: 알림 미설정(`is_configured() == False`), 네트워크 오류, HTTP 에러, 타임아웃, JSON 파싱 오류 등 모든 실패 케이스
- **예외 전파 없음**: 어떤 상황에서도 예외를 발생시키지 않음

### `TelegramNotifier.notify_success(train_info: str) -> bool`

- `train_info`: 열차 정보 문자열 (예: `"08시 이후 동탄 -> 동대구 (20260315)"`)
- 반환: `send_message()`의 반환값과 동일

### `TelegramNotifier.notify_failure(reason: str) -> bool`

- `reason`: 실패 사유 문자열 (예: `"네트워크 오류: 최대 재시도(3회) 초과"`)
- 반환: `send_message()`의 반환값과 동일

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-09 Telegram 알림 기능 변경 설계 |
