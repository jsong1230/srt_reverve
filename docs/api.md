# SRT API 문서

## SRT 클래스

SRT 자동 예약의 핵심 클래스입니다. 웹드라이버 관리, 로그인, 검색, 예약을 담당합니다.

### 초기화

```python
from srt_reservation.main import SRT

srt = SRT(
    dpt_stn='동탄',              # 출발역
    arr_stn='동대구',            # 도착역
    dpt_dt='20260315',           # 출발 날짜 (YYYYMMDD)
    dpt_tm='08',                 # 출발 시간 (HH, 짝수만)
    num_trains_to_check=2,       # 확인할 기차 수
    want_reserve=False,          # 예약 대기 신청 여부
    anti_bot_method='undetected',# 봇 탐지 우회 방법
    retry_delay_min=60,          # 재시도 최소 대기(초)
    retry_delay_max=120,         # 재시도 최대 대기(초)
    use_profile=True,            # Chrome 프로필 사용
    headless=False               # 헤드리스 모드
)
```

#### 매개변수

| 매개변수 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `dpt_stn` | str | (필수) | 출발역 (17개 역 목록) |
| `arr_stn` | str | (필수) | 도착역 (17개 역 목록) |
| `dpt_dt` | str | (필수) | 출발 날짜 또는 쉼표 구분 목록 |
| `dpt_tm` | str | (필수) | 출발 시간 또는 쉼표 구분 목록 |
| `num_trains_to_check` | int | 2 | 확인할 기차 수 |
| `want_reserve` | bool | False | 예약 대기 신청 여부 |
| `anti_bot_method` | str | 'undetected' | 'undetected', 'stealth', 'enhanced' 중 선택 |
| `retry_delay_min` | int | 60 | 재시도 최소 대기 시간(초) |
| `retry_delay_max` | int | 120 | 재시도 최대 대기 시간(초) |
| `use_profile` | bool | True | Chrome 프로필 사용 여부 |
| `headless` | bool | False | 헤드리스 모드 여부 |

#### 예시

```python
# 기본 설정
srt = SRT('동탄', '동대구', '20260315', '08')

# 다중 검색 조건
srt = SRT(
    '동탄', '동대구',
    dpt_dt='20260315,20260316,20260317',
    dpt_tm='08,10,12',
    num_trains_to_check=3
)

# 봇 탐지 회피 강화
srt = SRT(
    '동탄', '동대구', '20260315', '08',
    anti_bot_method='undetected',
    retry_delay_min=45,
    retry_delay_max=90
)
```

### 메서드

#### set_log_info(login_id, login_psw)

로그인 정보를 설정합니다.

```python
srt.set_log_info('1234567890', 'password123')
```

**매개변수:**
- `login_id` (str): SRT 회원 ID
- `login_psw` (str): SRT 비밀번호

**예외:**
- `ValueError`: login_id 또는 login_psw가 비어있을 때

#### check_input()

입력값을 검증합니다.

```python
srt.check_input()  # 내부적으로 __init__에서 호출됨
```

**검증 항목:**
- 출발역/도착역 (17개 역 목록 확인)
- 날짜 형식 (YYYYMMDD)
- 시간 범위 (0-23)
- 시간은 짝수만 허용

**예외:**
- `InvalidStationNameError`: 잘못된 역명
- `InvalidDateFormatError`: 날짜 형식 오류
- `InvalidDateError`: 유효하지 않은 날짜
- `InvalidTimeFormatError`: 시간 형식 오류

#### run_driver()

WebDriver를 초기화하고 SRT 사이트로 이동합니다.

```python
srt.run_driver()
```

**동작:**
1. Chrome 옵션 설정 (봇 탐지 우회)
2. WebDriver 초기화
3. SRT 로그인 페이지로 이동
4. 드라이버 객체 저장

**예외:**
- `WebDriverException`: WebDriver 초기화 실패
- `TimeoutException`: 페이지 로드 타임아웃

#### login()

SRT 사이트에 로그인합니다.

```python
srt.login()
```

**동작:**
1. 회원 ID 입력
2. 비밀번호 입력
3. 로그인 버튼 클릭
4. Alert 자동 처리
5. 로그인 완료 확인

**예외:**
- `NoAlertPresentException`: Alert 처리 실패
- `TimeoutException`: 로그인 타임아웃

#### go_search()

기차 검색을 실행합니다.

```python
srt.go_search()
```

**동작:**
1. 검색 페이지로 이동
2. 출발역/도착역 선택
3. 날짜 선택
4. 시간 선택
5. 조회 버튼 클릭
6. 검색 결과 페이지 대기

#### check_result()

검색 결과를 모니터링하고 예약을 시도합니다.

```python
srt.check_result()
```

**동작:**
1. 15~30초 간격으로 새로고침
2. 예약 가능 좌석 확인
3. 발견 시 book_ticket() 호출
4. 성공 시 `is_booked = True` 설정
5. 무한 루프 (예약 완료 또는 중단 시까지)

**반환값:** 없음 (루프 탈출 시 `is_booked` 플래그 확인)

#### book_ticket(seat_count, train_index)

일반석 예약을 시도합니다.

```python
srt.book_ticket(4, 0)  # 4개 좌석, 첫 번째 기차
```

**매개변수:**
- `seat_count` (int): 예약할 좌석 수
- `train_index` (int): 기차 목록에서의 인덱스

**동작:**
1. 선택한 기차의 일반석 버튼 클릭
2. 좌석 선택 (자동)
3. 예약 확인
4. 성공 시 `is_booked = True`

#### reserve_ticket(wait_list_index, train_index)

예약 대기를 신청합니다.

```python
srt.reserve_ticket(0, 0)  # 첫 번째 대기, 첫 번째 기차
```

**매개변수:**
- `wait_list_index` (int): 예약 대기 목록에서의 인덱스
- `train_index` (int): 기차 목록에서의 인덱스

**동작:**
1. 선택한 기차의 예약 대기 버튼 클릭
2. 대기 신청 확인
3. 성공 시 `is_booked = True`

#### close_driver()

WebDriver를 종료합니다.

```python
srt.close_driver()
```

**동작:**
1. Chrome 창 종료 (headless 모드 제외)
2. WebDriver 리소스 정리
3. 세션 정리

### 속성

| 속성 | 타입 | 설명 |
|-----|------|------|
| `dpt_stn` | str | 출발역 |
| `arr_stn` | str | 도착역 |
| `dpt_dates` | list | 출발 날짜 목록 |
| `dpt_times` | list | 출발 시간 목록 |
| `search_conditions` | list | 검색 조건 (날짜×시간) |
| `is_booked` | bool | 예약 완료 여부 |
| `cnt_refresh` | int | 새로고침 횟수 |
| `driver` | WebDriver | Selenium WebDriver 객체 |

## 사용 흐름

### 기본 예약

```python
from srt_reservation.main import SRT

# 1. SRT 인스턴스 생성
srt = SRT('동탄', '동대구', '20260315', '08')

# 2. 로그인 정보 설정
srt.set_log_info('1234567890', 'password123')

# 3. 입력값 검증
srt.check_input()

# 4. WebDriver 실행
srt.run_driver()

try:
    # 5. 로그인
    srt.login()
    
    # 6. 검색 페이지 이동
    srt.go_search()
    
    # 7. 결과 모니터링 및 예약
    srt.check_result()
    
    # 8. 예약 완료 확인
    if srt.is_booked:
        print("✅ 예약 완료!")
    else:
        print("❌ 예약 실패")
        
finally:
    # 9. 드라이버 종료
    srt.close_driver()
```

## 설정 클래스

### ConfigManager

환경변수와 .env 파일에서 설정을 로드합니다.

```python
from srt_reservation.config import ConfigManager

config = ConfigManager()
user_id = config.get('SRT_USER_ID')
password = config.get('SRT_PASSWORD')
telegram_token = config.get('TELEGRAM_BOT_TOKEN')
```

## 복구 및 에러 처리

### RecoveryContext

자동 복구를 관리합니다.

```python
from srt_reservation.recovery import RecoveryContext

recovery = RecoveryContext(max_retries=3)
recovery.execute(lambda: srt.go_search())
```

## 알림 기능

### TelegramNotifier

Telegram Bot으로 알림을 발송합니다.

```python
from srt_reservation.notifier import TelegramNotifier

notifier = TelegramNotifier()
notifier.send_notification("예약 성공!", "동탄 → 동대구")
```

## 예외 처리

### 커스텀 예외

```python
from srt_reservation.exceptions import (
    InvalidStationNameError,
    InvalidDateError,
    InvalidTimeFormatError
)

try:
    srt = SRT('잘못된역', '동대구', '20260315', '08')
except InvalidStationNameError as e:
    print(f"역명 오류: {e}")
```

## 로깅

### 로그 설정

```python
import logging

# 로그 레벨 변경
logging.getLogger('srt').setLevel(logging.DEBUG)

# 로그 파일 확인
# ~/.srt_reverve/logs/srt_YYYYMMDD.log
```

---

**마지막 업데이트**: 2026-03-12
