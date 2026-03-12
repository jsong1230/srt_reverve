# 클래스 다이어그램

SRT 자동 예약 프로그램의 주요 클래스 구조와 관계입니다.

---

## 📊 시스템 구조도

```
┌─────────────────────────────────────────────────┐
│          quickstart.py (CLI 진입점)             │
│     argparse 기반 명령어 인터페이스             │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │    SRT (핵심 클래스)        │
        │  main.py의 Main 클래스     │
        └─┬──────┬──────────┬────────┘
          │      │          │
          ↓      ↓          ↓
    ┌──────┐ ┌──────┐ ┌──────────┐
    │Login │ │Search│ │Booking   │
    └──────┘ └──────┘ └──────────┘
          │      │          │
          └──────┴──────────┘
                 │
    ┌────────────┼────────────┐
    ↓            ↓            ↓
Recovery    Notifier   Validation
┌────────┐  ┌────────┐  ┌──────────┐
│Recovery│  │Telegram│  │Station   │
│Context │  │Notifier│  │Validator │
└────────┘  └────────┘  └──────────┘
```

---

## 🏗️ 상세 클래스 구조

### 1️⃣ SRT 클래스 (메인)

```
SRT (srt_reservation/main.py)
├── __init__()
│   ├── 검색 조건 저장
│   ├── anti_bot_method 설정
│   ├── retry_delay 설정
│   └── 입력 검증 (check_input)
│
├── 초기화 메서드
│   ├── run_driver()        → WebDriver 생성
│   ├── _setup_options()    → Chrome 옵션 구성
│   └── _inject_stealth()   → 봇 탐지 우회
│
├── 로그인 메서드
│   ├── login()             → SRT 사이트 로그인
│   └── _human_like_type()  → 자연스러운 타이핑
│
├── 검색 메서드
│   ├── go_search()         → 검색 페이지 이동
│   ├── _select_date()      → 출발 날짜 선택
│   ├── _select_time()      → 출발 시간 선택
│   └── _click_search()     → 검색 버튼 클릭
│
├── 예약 메서드
│   ├── check_result()      → 무한 루프: 결과 확인
│   ├── book_ticket()       → 일반석 예약
│   └── reserve_ticket()    → 예약 대기 신청
│
├── 복구 메서드
│   ├── _recover_network()  → 네트워크 오류 복구
│   ├── _recover_session()  → 세션 재로그인
│   └── _check_connection() → 연결 상태 확인
│
├── 유틸리티 메서드
│   ├── _human_like_delay() → 랜덤 대기
│   ├── _smooth_scroll()    → 부드러운 스크롤
│   ├── _random_movement()  → 마우스 이동
│   └── close_driver()      → WebDriver 정리
│
└── 상태 변수
    ├── driver              → WebDriver 인스턴스
    ├── is_booked           → 예약 성공 여부
    ├── cnt_refresh         → 새로고침 카운트
    └── login_info          → 로그인 정보
```

### 2️⃣ Recovery 클래스 (복구 패턴)

```
RecoveryContext (srt_reservation/main.py)
├── NetworkErrorRecovery
│   ├── detect()     → 네트워크 오류 감지
│   ├── recover()    → 연결 재시도
│   └── rollback()   → 이전 상태 복원
│
├── SessionRecovery
│   ├── detect()     → 세션 만료 감지
│   ├── recover()    → 재로그인
│   └── restore()    → 검색 상태 복구
│
└── BrowserRecovery
    ├── detect()     → 브라우저 연결 끊김 감지
    ├── recover()    → 새 WebDriver 생성
    └── resume()     → 이전 작업 재개
```

### 3️⃣ Notifier 클래스 (알림)

```
TelegramNotifier (srt_reservation/main.py)
├── __init__(token, chat_id)
│   ├── 봇 토큰 저장
│   └── 채팅 ID 저장
│
├── send_notification(message, status)
│   ├── 메시지 형식화
│   ├── API 호출 (requests)
│   └── 에러 처리
│
├── on_success(ticket_info)
│   └── "✅ 예약 성공" 알림
│
├── on_failure(error_message)
│   └── "❌ 예약 실패" 알림
│
└── on_error(exception)
    └── "⚠️ 에러 발생" 알림
```

### 4️⃣ Validation 클래스 (검증)

```
Validation (srt_reservation/validation.py)
├── station_list
│   └── 17개 역명 저장소
│
├── validate_station(name)
│   ├── 역명 존재 확인
│   └── InvalidStationNameError 발생
│
├── validate_date(date_str)
│   ├── YYYYMMDD 형식 확인
│   ├── 날짜 유효성 확인
│   └── InvalidDateError 발생
│
├── validate_time(time_str)
│   ├── HH 형식 확인
│   ├── 짝수만 허용 (00, 02, ..., 22)
│   └── InvalidTimeFormatError 발생
│
└── validate_input(dpt_stn, arr_stn, dpt_dt, dpt_tm)
    └── 모든 입력 종합 검증
```

### 5️⃣ Exception 클래스 (예외)

```
Exception (srt_reservation/exceptions.py)
├── InvalidStationNameError
│   └── "역명 오류" 발생
│
├── InvalidDateFormatError
│   └── "날짜 형식 오류" 발생
│
├── InvalidDateError
│   └── "유효하지 않은 날짜" 발생
│
└── InvalidTimeFormatError
    └── "시간 형식 오류 (짝수만)" 발생
```

---

## 🔄 실행 흐름 (Flow)

```
1. CLI 입력
   quickstart.py → argparse 파싱

2. SRT 인스턴스 생성
   __init__() → 검증 → anti_bot 설정

3. 드라이버 초기화
   run_driver() → Chrome 옵션 → 봇 탐지 우회

4. 로그인
   login() → ID/Password 입력 → SRT 로그인

5. 검색 페이지 이동
   go_search() → 역/날짜/시간 입력 → 검색 클릭

6. 무한 루프: 결과 확인
   check_result()
   ├─ 예약 가능? → book_ticket() / reserve_ticket()
   ├─ 아니면? → 15~30초 대기
   └─ 오류? → recover_*() 복구 시도

7. 성공 또는 실패
   is_booked = True → Telegram 알림 → 종료
```

---

## 🔗 클래스 의존성

```
quickstart.py
    ↓
    SRT
    ├─→ Validation (입력 검증)
    ├─→ RecoveryContext (에러 복구)
    ├─→ TelegramNotifier (알림)
    ├─→ WebDriver (Selenium)
    └─→ Exception (예외 처리)
```

---

## 📋 메서드 호출 순서

### 예약 성공 경로

```
1. SRT.__init__()
   └─ check_input() [검증]

2. set_log_info()
   └─ 로그인 정보 저장

3. run_driver()
   ├─ _setup_options() [Chrome 옵션]
   ├─ _inject_stealth() [봇 탐지 우회]
   └─ driver = webdriver.Chrome()

4. login()
   ├─ driver.get('https://etk.srail.co.kr')
   ├─ find_element('ID 입력')
   ├─ _human_like_type(user_id)
   ├─ find_element('비밀번호 입력')
   ├─ _human_like_type(password)
   ├─ find_element('로그인 버튼').click()
   └─ wait for dashboard

5. go_search()
   ├─ _select_date()
   ├─ _select_time()
   └─ _click_search()

6. check_result() [무한 루프]
   ├─ wait for results
   ├─ for each 기차:
   │   ├─ standard_seat 있음?
   │   │   ├─ YES → book_ticket()
   │   │   │       ├─ click_ticket
   │   │   │       ├─ click_reserve
   │   │   │       ├─ handle_dialog
   │   │   │       └─ is_booked = True
   │   │   │           ↓
   │   │   │       TelegramNotifier.send_notification()
   │   │   │           ↓
   │   │   │       return (예약 성공!)
   │   │   │
   │   │   └─ NO → continue
   │
   └─ 30초 대기 → 새로고침 → 반복
```

### 에러 복구 경로

```
check_result() 중 오류 발생
    ↓
RecoveryContext 감지
    ├─ ConnectionRefusedError
    │   └─ NetworkErrorRecovery.recover()
    │       └─ 10초 대기 → 재시도
    │
    ├─ StaleElementReferenceException
    │   └─ SessionRecovery.recover()
    │       └─ 재로그인 → 다시 search
    │
    └─ WebDriverException
        └─ BrowserRecovery.recover()
            └─ 새 WebDriver → 처음부터
```

---

## 🎯 설계 패턴

### 1️⃣ 싱글톤 패턴 (SRT)
```python
srt = SRT(...)  # 한 번만 생성
srt.run()       # 실행
```

### 2️⃣ 전략 패턴 (봇 탐지)
```python
if anti_bot_method == 'undetected':
    use_undetected_chromedriver()
elif anti_bot_method == 'stealth':
    inject_stealth_script()
else:
    use_enhanced_options()
```

### 3️⃣ 복구 패턴 (Recovery)
```python
try:
    check_result()
except NetworkError:
    NetworkErrorRecovery.recover()
except SessionError:
    SessionRecovery.recover()
```

### 4️⃣ 옵저버 패턴 (Notifier)
```python
# 예약 성공 이벤트
is_booked = True
notifier.send_notification("예약 성공!")
```

---

## 📊 메모리 구조

```
SRT 인스턴스
├── 설정 데이터 (변하지 않음)
│   ├── dpt_stn, arr_stn
│   ├── dpt_dt, dpt_tm
│   └── num_trains_to_check
│
├── 실행 상태 (변함)
│   ├── driver (WebDriver)
│   ├── is_booked (boolean)
│   ├── cnt_refresh (int)
│   └── login_info (dict)
│
└── 외부 연결
    ├── TelegramNotifier
    ├── RecoveryContext
    └── Selenium WebDriver
```

---

## 🚀 확장 가능성

### 현재 구조 (모놀리식)
```
SRT (main.py) - 2000+ 줄
```

### 개선 계획 (모듈화)
```
SRT (추상 클래스)
├── SRTConfig (설정 관리)
├── SRTAuth (로그인)
├── SRTSearch (검색)
├── SRTBooking (예약)
└── SRTRecovery (복구)
```

---

**마지막 업데이트**: 2026-03-12
