# SRT 자동 예약 프로그램

## 프로젝트 개요

매진된 SRT 기차표를 자동으로 예약하는 Python 프로그램입니다. Selenium WebDriver를 사용하여 SRT 예약 사이트를 자동화하고, 표가 나올 때까지 반복적으로 새로고침하여 예약을 시도합니다.

### 주요 기능
- SRT 홈페이지 자동 로그인
- 원하는 출발역/도착역/날짜/시간 기준으로 기차 검색
- 예약 가능한 좌석이 나올 때까지 자동 새로고침 (15~30초 간격)
- 일반석 예약 또는 예약 대기 신청
- 봇 탐지 완화 옵션 적용
- Chrome 창 유지 옵션 (예약 결과 확인용)

### 기술 스택
- Python 3.9
- Selenium 4.15.0+
- Chrome WebDriver
- pytest (테스트)

## 프로젝트 구조

```
srt_reverve/
├── srt_reservation/          # 메인 패키지
│   ├── __init__.py
│   ├── main.py              # 핵심 SRT 클래스 및 예약 로직
│   ├── exceptions.py        # 커스텀 예외 정의
│   ├── validation.py        # 역 목록 정의
│   └── util.py              # CLI 인자 파싱 유틸리티
├── tests/                   # 테스트 코드
│   ├── test_validation.py   # 검증 로직 테스트
│   ├── test_exceptions.py   # 예외 테스트
│   └── test_main.py         # 메인 로직 테스트
├── docs/                    # 문서
│   └── mac_setup.md        # macOS 설정 가이드
├── quickstart.py           # CLI 진입점
├── requirements.txt        # 의존성 목록
├── pytest.ini             # pytest 설정
└── pyrightconfig.json     # Python 타입 체커 설정
```

## 핵심 컴포넌트

### 1. SRT 클래스 (`srt_reservation/main.py`)

프로그램의 핵심 클래스로, 예약 프로세스의 모든 단계를 관리합니다.

#### 주요 메서드

- `__init__(dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check, want_reserve)`
  - 예약 조건 초기화 및 입력 검증

- `check_input()`
  - 역명, 날짜, 시간 형식 검증
  - InvalidStationNameError, InvalidDateError, InvalidTimeFormatError 예외 발생

- `run_driver()`
  - Chrome WebDriver 초기화
  - 봇 탐지 완화 옵션 적용
  - detach 모드로 브라우저 창 유지

- `login()`
  - SRT 사이트 로그인
  - Alert 처리 로직 포함
  - ElementClickInterceptedException 대응

- `go_search()`
  - 기차 조회 페이지로 이동
  - 출발역/도착역/날짜/시간 입력
  - 조회 버튼 클릭

- `check_result()`
  - 검색 결과를 반복적으로 확인 (무한 루프)
  - 예약 가능한 좌석 발견 시 예약 시도
  - 15~30초 랜덤 간격으로 새로고침

- `book_ticket(standard_seat, i)`
  - 일반석 예약 시도
  - 성공 시 `is_booked = True` 설정

- `reserve_ticket(reservation, i)`
  - 예약 대기 신청

- `close_driver()`
  - WebDriver 리소스 정리
  - 브라우저 세션 종료 예외 처리

#### 중요한 설계 특징

1. **브라우저 세션 안정성**
   - `detach` 옵션으로 스크립트 종료 후에도 Chrome 창 유지
   - 장시간 실행을 위한 안정성 옵션 적용
   - `--disable-dev-shm-usage`, `--disable-gpu` 등

2. **봇 탐지 완화**
   - `excludeSwitches: ["enable-automation"]`
   - `navigator.webdriver` 숨기기
   - CDP(Chrome DevTools Protocol) 사용

3. **에러 핸들링**
   - `ElementClickInterceptedException`: JavaScript 클릭으로 재시도
   - `StaleElementReferenceException`: 무시하고 계속 진행
   - `UnexpectedAlertPresentException`: Alert 자동 처리
   - 브라우저 연결 끊김 감지 및 안내

4. **재시도 로직**
   - 15~30초 랜덤 간격으로 새로고침
   - 봇 탐지 회피 목적
   - `cnt_refresh`로 시도 횟수 추적

### 2. 예외 처리 (`srt_reservation/exceptions.py`)

커스텀 예외를 통한 명확한 에러 메시징:

```python
InvalidStationNameError   # 잘못된 역명
InvalidDateFormatError    # 날짜 형식 오류
InvalidDateError          # 유효하지 않은 날짜
InvalidTimeFormatError    # 시간 형식 오류 (짝수만 허용)
```

### 3. 검증 (`srt_reservation/validation.py`)

```python
station_list = [
    "수서", "동탄", "평택지제", "천안아산", "오송", "대전",
    "김천(구미)", "동대구", "신경주", "울산(통도사)", "부산",
    "공주", "익산", "정읍", "광주송정", "나주", "목포"
]
```

### 4. CLI 인터페이스 (`quickstart.py`, `util.py`)

argparse 기반 CLI:
```bash
python quickstart.py \
  --user 1234567890 \
  --psw 000000 \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20220117 \
  --tm 08 \
  --num 2 \
  --reserve False
```

## 코딩 스타일 및 패턴

### 1. 로깅
- `logging` 모듈 사용
- INFO 레벨: 정상 진행 상황
- WARNING 레벨: 재시도 가능한 문제
- ERROR 레벨: 치명적 오류

### 2. 대기 전략
- `WebDriverWait`: 명시적 대기 (특정 조건까지 대기)
- `implicitly_wait`: 암묵적 대기 (요소 검색 시 자동 대기)
- `time.sleep`: 고정 대기 (페이지 로딩 등)

### 3. 요소 선택
- CSS Selector 우선 사용
- ID 선택자: 안정적인 요소
- XPath: 복잡한 경로

### 4. 에러 복구
- try-except-finally 패턴
- 특정 예외 타입별 처리
- 브라우저 세션 끊김 여부 확인 헬퍼 함수

## 개발 가이드

### 환경 설정

1. **Python 버전**
   ```bash
   pyenv install 3.9.20
   pyenv local 3.9.20
   ```

2. **가상환경**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   ```

3. **의존성 설치**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **ChromeDriver (macOS)**
   ```bash
   brew install chromedriver
   ```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 특정 테스트
pytest tests/test_validation.py -v

# 커버리지 확인
pytest tests/ --cov=srt_reservation --cov-report=html
```

### 실행

```bash
python quickstart.py \
  --user YOUR_ID \
  --psw YOUR_PASSWORD \
  --dpt 출발역 \
  --arr 도착역 \
  --dt YYYYMMDD \
  --tm HH
```

## 봇 탐지 우회 기능 (2026-02-16 업데이트)

### 문제 상황

SRT 예약 사이트에서 Selenium의 자동화 흔적을 탐지하여 차단하는 경우가 있습니다.

### 해결 방법

세 가지 봇 탐지 우회 방법을 제공합니다:

#### 1. undetected-chromedriver (가장 권장)

ChromeDriver 바이너리를 패치하여 자동화 흔적을 근본적으로 제거합니다.

```python
# 사용법
srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm,
          num_trains_to_check, want_reserve,
          anti_bot_method='undetected')
```

**특징:**
- Cloudflare, DataDome, Imperva 등 주요 봇 차단 시스템 우회
- 가장 높은 성공률
- 자동으로 Chrome 버전에 맞는 ChromeDriver 다운로드

#### 2. selenium-stealth (권장)

JavaScript 레벨에서 자동화 흔적을 숨깁니다.

```python
# 사용법
srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm,
          num_trains_to_check, want_reserve,
          anti_bot_method='stealth')
```

**특징:**
- 일반 ChromeDriver와 함께 사용
- 중급 수준의 봇 탐지 우회
- 설정이 간단함

#### 3. enhanced (기본 제공)

향상된 Chrome 옵션과 JavaScript 주입을 사용합니다.

```python
# 사용법
srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm,
          num_trains_to_check, want_reserve,
          anti_bot_method='enhanced')
```

**특징:**
- 추가 라이브러리 불필요
- 기본 제공
- 기본적인 봇 탐지 우회

### 인간처럼 동작하는 기능

모든 방법에 다음 기능이 적용됩니다:

1. **랜덤 대기** (`_human_like_delay`)
   - 작업 간 0.5~2초 랜덤 대기
   - 봇 탐지 패턴 회피

2. **자연스러운 타이핑** (`_human_like_type`)
   - 글자 하나씩 입력
   - 0.05~0.15초 랜덤 간격

3. **부드러운 스크롤** (`_smooth_scroll`)
   - smooth scroll 애니메이션
   - 요소를 화면 중앙에 배치

4. **마우스 이동 시뮬레이션** (`_random_mouse_movement`)
   - 랜덤 마우스 이벤트 발생
   - 실제 사용자처럼 행동

### JavaScript 스크립트 주입

`_inject_stealth_scripts` 메서드는 다음을 수정합니다:

- `navigator.webdriver` → `undefined`
- `window.chrome` 객체 추가
- `navigator.permissions` 수정
- `navigator.plugins` 수정
- `navigator.languages` 설정

### 강화된 Chrome 옵션

```python
# User-Agent 설정
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ..."

# 자동화 플래그 제거
--disable-blink-features=AutomationControlled
excludeSwitches: ["enable-automation", "enable-logging"]

# 권한 설정
credentials_enable_service: False
profile.password_manager_enabled: False

# 안정성 옵션
--disable-dev-shm-usage
--disable-gpu
--no-sandbox
```

### CLI 사용법

```bash
# undetected-chromedriver 사용
python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --anti-bot undetected

# selenium-stealth 사용
python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --anti-bot stealth

# enhanced 사용
python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --anti-bot enhanced
```

### 환경변수 설정

```bash
export ANTI_BOT_METHOD=undetected
python quickstart.py --user USER --psw PASS ...
```

---

## 주의사항

### 1. 로그인
- **반드시 SRT 회원 ID로 로그인** (휴대폰 번호 등 다른 방식 불가)
- 로그인 정보는 환경변수나 별도 설정 파일로 관리 권장

### 2. Chrome 브라우저
- 실행 중에는 Chrome 창을 닫지 않을 것
- 노트북 사용 시 절전 모드 비활성화 권장
- 예약 완료 후 수동으로 창 닫기

### 3. 재시도 간격
- 15~30초 랜덤 간격 (봇 탐지 완화)
- 너무 짧은 간격은 IP 차단 위험
- 너무 긴 간격은 예약 경쟁에서 불리

### 4. 명절 승차권
- 명절 승차권 예약에는 사용 불가
- 일반 승차권 예약에만 사용

### 5. 법적/윤리적 고려사항
- 개인 사용 목적으로만 사용
- 대량 예약이나 매크로 악용 금지
- SRT 이용약관 준수

## 개선 가능한 영역

### 1. 설정 관리
- 환경변수 기반 설정 (.env 파일)
- YAML/JSON 설정 파일 지원

### 2. 알림 기능
- 예약 성공 시 이메일/SMS 알림
- Slack/Discord 웹훅 통합

### 3. 로깅 개선
- 구조화된 로깅 (JSON 포맷)
- 로그 파일 저장
- 로그 레벨 설정 옵션

### 4. 에러 리커버리
- 네트워크 오류 시 자동 재시도
- 세션 만료 시 재로그인
- 브라우저 크래시 시 복구

### 5. 다중 검색 조건
- 여러 날짜/시간 동시 검색
- 대체 경로 자동 검색
- 우선순위 기반 예약

### 6. 성능 최적화
- 헤드리스 모드 옵션
- 병렬 검색 (멀티 프로세스)
- 메모리 사용량 최적화

## 문제 해결

### ChromeDriver 오류
```bash
# ChromeDriver 재설치
brew reinstall chromedriver

# 환경변수 설정
export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
```

### 로그인 실패
- SRT 회원 ID 확인
- 비밀번호 특수문자 이스케이프 확인
- 로그인 페이지 구조 변경 여부 확인

### 요소를 찾을 수 없음
- SRT 웹사이트 구조 변경 가능성
- CSS Selector 업데이트 필요
- 대기 시간 증가

### 브라우저 연결 끊김
- Chrome 업데이트 확인
- ChromeDriver 버전 호환성 확인
- 시스템 리소스 확인

## Cursor 개발 원칙 (참고)

이 프로젝트는 원래 Cursor로 개발되었으며, 다음 원칙을 따랐습니다:

### TODO 기반 작업 추적
- 새 작업 시작 전 TODO 등록
- 단계별 상태 변화 기록 (pending → in_progress → completed/cancelled)
- 70자 이하 간결한 설명

### 상태 관리
- 동시에 하나의 in_progress 항목만 유지
- 작업 완료 시 즉시 상태 업데이트
- 사용자 지시 변경 시 기존 TODO cancelled 처리

### 기록 유지
- 시간 순서 보존
- 중요 컨텍스트 메모
- 연속성 추적을 위한 ID 참조

## 라이선스

LICENSE 파일 참조

## 참고 문서

- [macOS 설정 가이드](docs/mac_setup.md)
- [SRT 홈페이지](https://etk.srail.co.kr)
- [Selenium 문서](https://www.selenium.dev/documentation/)

---

**최종 업데이트**: 2026-02-16
**Python 버전**: 3.9.20
**Selenium 버전**: 4.15.0+
