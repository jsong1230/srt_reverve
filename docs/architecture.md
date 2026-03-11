# 아키텍처 가이드

## 시스템 구조

### 전체 흐름도

```
┌────────────────────────────────────┐
│     quickstart.py (CLI 진입점)      │
│  - 명령행 인자 파싱 (argparse)      │
│  - 환경변수 로드 (.env)             │
└──────────────┬─────────────────────┘
               │
        ┌──────v──────────────┐
        │  SRT 클래스          │
        │  - 핵심 로직         │
        │  - 1004줄           │
        │                     │
        │  주요 메서드:       │
        │  • run_driver()    │
        │  • login()         │
        │  • go_search()     │
        │  • check_result()  │
        │  • book_ticket()   │
        └──┬──────────┬──────┘
           │          │
      ┌────v─────┐   ┌v──────────┐
      │recovery. │   │notifier.  │
      │py        │   │py         │
      │          │   │           │
      │• Network │   │•Telegram  │
      │• Session │   │• Success  │
      │• Browser │   │• Failure  │
      └──────────┘   └───────────┘
           │
      ┌────v─────────────────────┐
      │ Selenium WebDriver        │
      │ Chrome Automation         │
      └──────────────────────────┘
```

## 모듈 설명

### 1. quickstart.py (진입점)

**책임:**
- CLI 인자 파싱
- 사용자 입력 검증
- SRT 인스턴스 생성 및 실행
- 최상위 에러 처리

**주요 함수:**
```python
def main():
    """CLI 진입점"""
    # 1. 명령행 인자 파싱
    # 2. SRT 인스턴스 생성
    # 3. 예약 프로세스 실행
    # 4. 에러 처리
```

**의존성:**
- srt_reservation.main (SRT)
- srt_reservation.util (CLI 유틸)
- srt_reservation.config (설정 관리)

### 2. main.py (핵심 로직)

**책임:**
- 검색 조건 관리
- WebDriver 관리
- 로그인 프로세스
- 검색 및 예약 로직
- 사용자 입력 검증

**클래스 계층:**

```
SRT
├── __init__()
│   ├── 매개변수 검증
│   ├── 검색 조건 생성
│   ├── Recovery 초기화
│   └── Notifier 초기화
│
├── 설정 메서드
│   ├── set_log_info()
│   ├── check_input()
│   └── generate_search_conditions()
│
├── WebDriver 메서드
│   ├── run_driver()
│   ├── _apply_anti_bot_method()
│   └── close_driver()
│
├── 로그인 메서드
│   ├── login()
│   └── _handle_login_alert()
│
├── 검색 메서드
│   ├── go_search()
│   ├── search_with_condition()
│   └── check_result()
│
└── 예약 메서드
    ├── book_ticket()
    └── reserve_ticket()
```

**데이터 흐름:**

```
입력 매개변수
    ↓
검증 (check_input)
    ↓
검색 조건 생성
    ↓
WebDriver 초기화
    ↓
로그인
    ↓
검색 실행
    ↓
결과 모니터링 (무한 루프)
    ├─ 새로고침 (15-30초)
    ├─ 좌석 확인
    ├─ 예약 시도
    └─ 성공 → 종료
```

### 3. recovery.py (에러 복구)

**책임:**
- 네트워크 오류 처리
- 세션 만료 시 재로그인
- 브라우저 크래시 감지
- 자동 재시도 로직

**클래스 계층:**

```
RecoveryContext
├── NetworkErrorRecovery
│   ├── 인터넷 연결 확인
│   └── 재시도 (최대 3회)
│
├── SessionRecovery
│   ├── 세션 유효성 확인
│   └── 필요 시 재로그인
│
└── BrowserRecovery
    ├── 브라우저 상태 확인
    └── 크래시 시 복구
```

**복구 프로세스:**

```
예외 발생
    ↓
복구 전략 선택
    ├─ Network → 재연결 & 재시도
    ├─ Session → 재로그인
    └─ Browser → WebDriver 재초기화
    ↓
최대 재시도 확인 (3회)
    ├─ 성공 → 계속 진행
    └─ 실패 → RecoveryError 발생
```

### 4. notifier.py (알림 기능)

**책임:**
- Telegram Bot 연동
- 예약 성공/실패 알림
- 에러 발생 알림

**클래스:**

```
TelegramNotifier
├── __init__()
│   ├── 토큰 로드
│   └── 채팅 ID 로드
│
├── send_notification()
│   ├── 메시지 포맷팅
│   ├── API 호출
│   └── 결과 로깅
│
└── send_error()
    └── 에러 메시지 발송
```

### 5. config.py (설정 관리)

**책임:**
- 환경변수 관리
- .env 파일 로드
- 설정값 검증
- 기본값 제공

**구조:**

```
ConfigManager
├── load_env()
│   ├── .env 파일 파싱
│   └── 환경변수 로드
│
├── get(key)
│   └── 설정값 조회
│
└── validate()
    └── 필수 설정 검증
```

### 6. logger.py (로깅)

**책임:**
- 로그 설정
- 파일 로깅
- 콘솔 로깅
- 로그 레벨 관리

**구조:**

```
LoggerConfig
├── setup_logger()
│   ├── 파일 핸들러 (RotatingFileHandler)
│   ├── 콘솔 핸들러
│   └── 포맷 설정
│
└── get_logger(name)
    └── 로거 객체 반환
```

### 7. validation.py (검증 데이터)

**책임:**
- 지원하는 역 목록
- 역명 검증

**데이터:**

```python
station_list = [
    "수서", "동탄", "평택지제", "천안아산", "오송",
    "대전", "김천(구미)", "동대구", "신경주",
    "울산(통도사)", "부산", "공주", "익산",
    "정읍", "광주송정", "나주", "목포"
]
```

## 데이터 흐름

### 초기화 단계

```
CLI 인자
    ↓
SRT.__init__()
    ├── 매개변수 검증
    ├── 검색 조건 생성 (날짜 × 시간)
    ├── Recovery 초기화
    └── Notifier 초기화
    ↓
상태: 대기 (is_booked = False)
```

### 예약 단계

```
set_log_info() → 로그인 정보 설정
    ↓
run_driver() → WebDriver 초기화
    ├── Chrome 옵션 설정
    ├── 봇 탐지 우회 적용
    └── SRT 사이트로 이동
    ↓
login() → 로그인
    ├── ID 입력
    ├── 비밀번호 입력
    ├── Alert 처리
    └── 로그인 확인
    ↓
go_search() → 검색 페이지 이동
    ├── 역 선택
    ├── 날짜 선택
    ├── 시간 선택
    └── 조회
    ↓
check_result() → 결과 모니터링 (루프)
    ├── 15-30초 대기
    ├── 새로고침
    ├── 좌석 확인
    └─ 발견 시 book_ticket()
    ↓
book_ticket() → 예약 시도
    ├── 좌석 선택
    ├── 예약 확인
    └── is_booked = True
    ↓
close_driver() → 종료
```

## 검색 조건 관리

### 다중 조건 예시

```python
# 입력
dpt_dates = ["20260315", "20260316"]
dpt_times = ["08", "10"]

# 생성된 검색 조건
search_conditions = [
    {"dpt_dt": "20260315", "dpt_tm": "08"},
    {"dpt_dt": "20260315", "dpt_tm": "10"},
    {"dpt_dt": "20260316", "dpt_tm": "08"},
    {"dpt_dt": "20260316", "dpt_tm": "10"}
]

# 실행 순서: 날짜 우선, 동일 날짜 내에서 시간 순
```

## 봇 탐지 우회 메커니즘

### 3가지 방법

```
1. undetected-chromedriver
   └─ ChromeDriver 바이너리 패치
   └─ 가장 효과적

2. selenium-stealth
   └─ JavaScript 레벨 숨김
   └─ 중간 수준

3. enhanced (기본)
   └─ Chrome 옵션 + JS 주입
   └─ 기본 제공
```

### 적용 순서

```
SRT.__init__() 에서 anti_bot_method 결정
    ↓
run_driver() 에서 WebDriver 초기화 시 적용
    ├─ undetected 선택 시 uc.Chrome() 사용
    ├─ stealth 선택 시 stealth() 적용
    └─ enhanced 선택 시 옵션 + JS 주입
```

## 예외 처리 전략

### 예외 계층

```
BaseException
├── RecoveryError (복구 불가)
│   ├── NetworkErrorRecovery
│   ├── SessionRecovery
│   └── BrowserRecovery
│
├── ValidationError
│   ├── InvalidStationNameError
│   ├── InvalidDateError
│   ├── InvalidDateFormatError
│   └── InvalidTimeFormatError
│
└── SeleniumException
    ├── NoAlertPresentException
    ├── TimeoutException
    └── WebDriverException
```

### 에러 처리 흐름

```
예외 발생
    ↓
예외 타입 확인
    ├─ Recovery 관련 → RecoveryContext 호출
    ├─ Validation 관련 → 사용자 입력 재확인
    ├─ Selenium 관련 → 자동 재시도 또는 로깅
    └─ 기타 → 치명적 오류 처리
```

## 성능 최적화 포인트

### 현재 병목

| 항목 | 시간 | 개선 방향 |
|------|------|---------|
| WebDriver 초기화 | 5-10초 | 세션 재사용 |
| 메모리 누수 | 없음 → 발생 | 주기적 GC |
| 로그 파일 | 무제한 증가 | RotatingFileHandler |
| 네트워크 | 15-30초 폴링 | 적응형 대기 |

## 의존성 그래프

```
quickstart.py
    └── main.py (SRT)
        ├── recovery.py
        ├── notifier.py
        ├── config.py
        ├── logger.py
        ├── validation.py
        └── selenium
            └── chrome driver
```

## 향후 아키텍처 개선

### Phase 1: 구조 분할
- main.py를 3개 모듈로 분할
  - `webdriver_manager.py`
  - `search_engine.py`
  - `reservation_handler.py`

### Phase 2: 구성 패턴
- SRTConfig 클래스 도입
- 의존성 주입 (DI)

### Phase 3: 비동기 처리
- asyncio 기반 병렬 검색
- 다중 세션 관리

---

**마지막 업데이트**: 2026-03-12
