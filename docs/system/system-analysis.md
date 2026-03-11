# SRT 자동 예약 프로그램 -- 시스템 분석서

## 1. 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.9.20 |
| 브라우저 자동화 (주) | Selenium | >= 4.15.0 |
| 브라우저 자동화 (실험) | Playwright | >= 1.40.0 |
| WebDriver 관리 | webdriver-manager | >= 4.0.0 |
| 봇 탐지 우회 | undetected-chromedriver | >= 3.5.0 |
| 봇 탐지 우회 | selenium-stealth | >= 1.0.6 |
| 테스트 | pytest | >= 7.4.0 |
| 테스트 모킹 | pytest-mock | >= 3.11.0 |
| 타입 체커 | Pyright | (pyrightconfig.json) |

## 2. 아키텍처 패턴

**단일 프로세스 CLI 애플리케이션** -- 모노리식 스크립트 구조.

계층 다이어그램:

```
[CLI 진입점]
  quickstart.py / manual_login.py / srt_playwright.py
        |
[인자 파싱 계층]
  util.py (argparse)
        |
[핵심 비즈니스 로직]
  SRT 클래스 (main.py)
    ├── 입력 검증 (check_input)
    ├── WebDriver 초기화 (run_driver)
    ├── 로그인 (login, check_login)
    ├── 검색 (go_search)
    ├── 예약 루프 (check_result, book_ticket, reserve_ticket)
    └── 리소스 정리 (close_driver)
        |
[지원 모듈]
  exceptions.py  -- 커스텀 예외 4종
  validation.py  -- 역 목록 데이터
        |
[외부 의존성]
  Selenium WebDriver / undetected-chromedriver / selenium-stealth
        |
[외부 시스템]
  SRT 예약 웹사이트 (https://etk.srail.co.kr)
```

설계 특성:
- **God Object 패턴**: SRT 클래스가 드라이버 관리, 로그인, 검색, 예약, 봇 탐지 우회 등 모든 책임을 담당 (약 850줄)
- **절차적 흐름**: `run()` 메서드가 순차적으로 `run_driver() -> login() -> go_search() -> check_result()` 호출
- **Strategy 패턴 (부분적)**: 봇 탐지 우회 방법을 `anti_bot_method` 파라미터로 선택하여 `_run_driver_undetected()`, `_run_driver_stealth()`, `_run_driver_enhanced()` 중 하나 실행

## 3. 디렉토리 구조

```
srt_reverve/
├── srt_reservation/              # 메인 패키지
│   ├── __init__.py               # SRT 클래스 re-export
│   ├── main.py                   # SRT 클래스 (핵심 로직 전체, ~850줄)
│   ├── exceptions.py             # 커스텀 예외 4종
│   ├── validation.py             # station_list (17개 역)
│   └── util.py                   # CLI 인자 파싱 (argparse)
├── tests/                        # 테스트 코드
│   ├── __init__.py
│   ├── test_main.py              # SRT 클래스 단위 테스트 (9개 클래스)
│   ├── test_validation.py        # 역 목록 검증 테스트
│   └── test_exceptions.py        # 예외 클래스 테스트
├── docs/                         # 문서
│   ├── system/                   # 시스템 분석 (본 문서)
│   ├── project/                  # 프로젝트 기획 (비어 있음)
│   ├── specs/                    # 기능 사양 (비어 있음)
│   ├── api/                      # API 문서 (비어 있음)
│   ├── db/                       # DB 문서 (비어 있음)
│   ├── components/               # 컴포넌트 문서 (비어 있음)
│   ├── tests/                    # 테스트 결과 (비어 있음)
│   ├── infra/                    # 인프라 문서 (비어 있음)
│   ├── plans/                    # 계획 문서 (비어 있음)
│   ├── anti_bot_guide.md         # 봇 탐지 우회 가이드
│   └── mac_setup.md              # macOS 설정 가이드
├── quickstart.py                 # CLI 진입점 (자동 로그인)
├── manual_login.py               # CLI 진입점 (수동 로그인)
├── srt_playwright.py             # Playwright 기반 독립 스크립트 (실험적)
├── test_browser.py               # 브라우저 동작 수동 테스트 스크립트
├── requirements.txt              # Selenium 기반 의존성
├── requirements-playwright.txt   # Playwright 기반 의존성
├── pytest.ini                    # pytest 설정
├── pyrightconfig.json            # Pyright 설정
├── CLAUDE.md                     # 프로젝트 컨텍스트 문서
├── .gitignore
├── LICENSE
└── README.md
```

## 4. 주요 모듈 분석

| 모듈 | 위치 | 역할 | 의존성 |
|------|------|------|--------|
| SRT 클래스 | `srt_reservation/main.py` | 예약 프로세스 전체 관리 (드라이버 초기화, 로그인, 검색, 예약, 봇 우회) | selenium, undetected-chromedriver, selenium-stealth, webdriver-manager, exceptions, validation |
| 예외 모듈 | `srt_reservation/exceptions.py` | 입력 검증용 커스텀 예외 4종 정의 | 없음 |
| 검증 모듈 | `srt_reservation/validation.py` | SRT 역 목록 데이터 (17개 역) | 없음 |
| CLI 유틸 | `srt_reservation/util.py` | argparse 기반 CLI 인자 파싱 (12개 인자) | argparse (표준 라이브러리) |
| 자동 진입점 | `quickstart.py` | 자동 로그인 + 예약 실행 | SRT, util |
| 수동 진입점 | `manual_login.py` | 수동 로그인 후 자동 예약 실행 | SRT, util |
| Playwright 스크립트 | `srt_playwright.py` | Playwright 기반 독립 예약 스크립트 (SRT 패키지 미사용) | playwright |

### SRT 클래스 주요 메서드 분석

| 메서드 | 줄 수 (대략) | 책임 |
|--------|-------------|------|
| `__init__` | 50줄 | 예약 조건 초기화, 입력 검증 호출 |
| `check_input` | 25줄 | 역명, 날짜, 시간 형식 검증 |
| `_chrome_options` | 65줄 | Chrome 옵션 구성 (프로필, 봇 탐지 완화, 안정성) |
| `_run_driver_undetected` | 50줄 | undetected-chromedriver 기반 드라이버 초기화 |
| `_run_driver_stealth` | 30줄 | selenium-stealth 기반 드라이버 초기화 |
| `_run_driver_enhanced` | 20줄 | 기본 Selenium + 강화 옵션 드라이버 초기화 |
| `_inject_stealth_scripts` | 65줄 | CDP로 JavaScript 주입 (navigator 속성 조작) |
| `run_driver` | 15줄 | anti_bot_method에 따라 드라이버 초기화 분기 |
| `login` | 55줄 | SRT 로그인 (인간 행동 시뮬레이션 포함) |
| `check_login` | 35줄 | 로그인 성공 여부 3가지 방법으로 확인 |
| `go_search` | 40줄 | 검색 조건 입력 및 조회 실행 |
| `check_result` | 30줄 | 무한 루프로 예약 가능 여부 확인 + 새로고침 |
| `book_ticket` | 30줄 | 일반석 예약 시도 |
| `reserve_ticket` | 15줄 | 예약 대기 신청 |
| `run` | 50줄 | 전체 프로세스 오케스트레이션 |

### 인간 행동 시뮬레이션 메서드

| 메서드 | 역할 |
|--------|------|
| `_human_like_delay(min, max)` | 랜덤 시간 대기 (0.5~2.0초) |
| `_human_like_type(element, text)` | 글자 단위 타이핑 (0.05~0.15초 간격) |
| `_smooth_scroll(element)` | 부드러운 스크롤 애니메이션 |
| `_random_mouse_movement()` | JavaScript 기반 마우스 이동 이벤트 |

## 5. 데이터 흐름

### 입력

```
CLI 인자 (argparse)
  ├── 필수: --user, --psw, --dpt, --arr, --dt, --tm
  └── 선택: --num(2), --reserve(False), --anti-bot(undetected),
            --delay-min(60), --delay-max(120),
            --use-profile(True), --profile-dir(None)
```

### 처리 파이프라인

```
1. 입력 검증 (check_input)
   └── station_list 대조, 날짜/시간 포맷 확인

2. WebDriver 초기화 (run_driver)
   ├── undetected-chromedriver (권장)
   ├── selenium-stealth (대안)
   └── enhanced (기본)

3. 로그인 (login -> check_login)
   ├── 로그인 페이지 이동
   ├── ID/PW 입력 (인간 타이핑 시뮬레이션)
   ├── 로그인 버튼 클릭
   └── 로그인 확인 (3회 재시도)

4. 검색 (go_search)
   ├── 검색 페이지 이동
   ├── 출발역/도착역/날짜/시간 입력
   └── 조회 버튼 클릭

5. 예약 루프 (check_result, 무한 반복)
   ├── 상위 N개 기차 확인
   ├── "예약하기" 발견 시 -> book_ticket
   ├── "신청하기" 발견 시 (want_reserve=True) -> reserve_ticket
   ├── 예약 성공 시 종료
   └── 실패 시 -> 60~120초 대기 -> 새로고침 -> 반복
```

### 출력

- 콘솔 로그 (logging 모듈, INFO/WARNING/ERROR 레벨)
- 예약 성공 시: Chrome 창 유지 (사용자가 결과 확인)
- 예약 실패 시: 에러 메시지 출력

### 상태 관리

- `is_booked` (bool): 예약 완료 플래그
- `cnt_refresh` (int): 새로고침 횟수 카운터
- `driver` (WebDriver): 브라우저 세션 참조

## 6. 현재 설계 특징

### 강점

1. **봇 탐지 우회 다층 전략**: 3가지 방법 (undetected, stealth, enhanced) + Chrome 프로필 재사용 + 인간 행동 시뮬레이션으로 봇 탐지 회피율 향상
2. **브라우저 세션 안정성**: detach 모드로 스크립트 종료 후에도 Chrome 유지, 장시간 실행 안정성 옵션 다수 적용
3. **에러 복구**: Alert 자동 처리, ElementClickInterceptedException 시 JavaScript 클릭 fallback, StaleElementReference 무시, 브라우저 세션 끊김 감지
4. **입력 검증 철저**: 역명, 날짜 형식, 날짜 유효성, 시간 형식 (짝수만) 모두 검증
5. **테스트 기반 검증**: 입력 검증, 로그인, 예약, Alert 처리 등 주요 경로에 대한 단위 테스트 존재
6. **다중 진입점**: 자동 로그인 (quickstart.py), 수동 로그인 (manual_login.py), Playwright (srt_playwright.py)

### 약점

1. **God Object**: SRT 클래스가 드라이버 관리, 봇 우회, 로그인, 검색, 예약 등 모든 책임을 단일 클래스에 담당 (~850줄)
2. **코드 중복**: `_run_driver_undetected()`와 `_chrome_options()` 사이에 Chrome 프로필 설정 로직 중복, `srt_playwright.py`가 SRT 패키지를 전혀 재사용하지 않고 독립적으로 구현
3. **설정 하드코딩**: User-Agent 문자열, SRT URL, CSS Selector 등이 코드에 직접 삽입
4. **로그만 콘솔 출력**: 파일 로깅, 구조화 로깅(JSON) 미지원
5. **무한 루프 탈출 조건 부족**: `check_result()`가 예약 성공 또는 예외 발생 시에만 종료 (최대 시도 횟수, 타임아웃 없음)

## 7. 변경 영향도 분석

### 고변경 위험 영역

| 영역 | 이유 |
|------|------|
| `main.py` SRT 클래스 | 모든 로직이 집중되어 있어 어떤 변경이든 부수 효과 위험 |
| CSS Selector 상수 | SRT 웹사이트 UI 변경 시 즉시 파손 (하드코딩) |
| 봇 탐지 우회 로직 | SRT 측 탐지 정책 변경 시 전체 기능 무력화 가능 |
| `login()` 메서드 | 로그인 페이지 구조 변경 시 전체 프로세스 차단 |

### 안정 영역

| 영역 | 이유 |
|------|------|
| `exceptions.py` | 단순 예외 클래스, 의존성 없음 |
| `validation.py` | 역 목록 데이터만 포함, SRT 노선 변경 시에만 수정 필요 |
| `util.py` | argparse 기반 CLI 파싱, 안정적 |
| `tests/` | 모킹 기반 단위 테스트, 외부 의존성 없음 |

## 8. 테스트 현황

### 테스트 구조

- **pytest.ini**: `tests/` 디렉토리, `unit`/`integration` 마커 정의
- **test_main.py**: 9개 테스트 클래스, SRT 클래스의 주요 메서드 단위 테스트
- **test_validation.py**: 역 목록 무결성 테스트 (4개)
- **test_exceptions.py**: 예외 클래스 인스턴스화 및 상속 테스트 (5개)

### 테스트 범위

| 테스트 대상 | 커버리지 수준 | 비고 |
|-------------|-------------|------|
| 입력 검증 (check_input) | 높음 | 유효/무효 입력 전체 검증 |
| 로그인 정보 (set_log_info) | 높음 | 빈 값, None 케이스 포함 |
| WebDriver 초기화 | 중간 | enhanced 모드만 테스트, undetected/stealth 미테스트 |
| Alert 처리 | 중간 | 성공/실패 케이스 |
| 로그인 | 중간 | 성공, Alert 발생 케이스 (Mock 기반) |
| 예약 (book_ticket) | 높음 | 성공/실패/매진 케이스 |
| 예약 대기 (reserve_ticket) | 높음 | 성공/불가 케이스 |
| 새로고침 (refresh_result) | 중간 | 정상 케이스만 |
| 결과 확인 (check_result) | 낮음 | 성공 + 에러 시 탈출만 검증 |
| 인간 행동 시뮬레이션 | 없음 | _human_like_delay, _human_like_type 등 미테스트 |
| Playwright 스크립트 | 없음 | 독립 스크립트, 테스트 없음 |
| 통합/E2E | 없음 | 실제 SRT 사이트 접속 필요하여 자동화 어려움 |

### 테스트 패턴

- `unittest.mock`의 `Mock`, `MagicMock`, `patch` 사용
- Selenium WebDriver를 Mock으로 대체하여 외부 의존성 제거
- 각 테스트 클래스가 SRT 인스턴스를 개별 생성 (setup/teardown 패턴 미사용)

## 9. 기술 부채 / 주의사항

### 기술 부채

1. **SRT 클래스 분리 필요**: 드라이버 관리, 봇 탐지 우회, 페이지 조작, 예약 로직을 별도 클래스/모듈로 분리하면 유지보수성 향상
2. **CSS Selector 외부화**: SRT 웹사이트 UI 변경에 대응하기 위해 Selector를 설정 파일이나 상수 모듈로 분리 필요
3. **Playwright 스크립트 통합**: `srt_playwright.py`가 SRT 패키지와 완전히 분리되어 있어 로직 중복 발생. 공통 인터페이스로 추상화 가능
4. **환경 설정 관리**: User-Agent, URL, 대기 시간 등이 코드에 하드코딩. `.env` 또는 설정 파일 도입 권장
5. **로그인 테스트 한계**: `test_login_success`에서 `_human_like_type` 호출로 인해 `send_keys`가 글자 단위로 호출되지만, 테스트에서는 `send_keys`가 1회 호출되는지만 검증 (실제 동작과 테스트 간 불일치 가능)

### 운영 주의사항

1. **Chrome 프로필 충돌**: `--use-profile` 사용 시 Chrome이 실행 중이면 프로필 잠금으로 실패
2. **재시도 간격**: 기본 60~120초. CLAUDE.md에는 15~30초로 기술되어 있으나 실제 코드 기본값은 60~120초 (문서와 코드 불일치)
3. **무한 루프**: `check_result()`에 종료 조건이 예약 성공 또는 예외뿐이므로, 장시간 실행 시 리소스 소모 주의
4. **SRT 웹사이트 의존성**: SRT 측 HTML 구조 변경 시 CSS Selector 전면 수정 필요
5. **Chrome/ChromeDriver 버전 호환**: undetected-chromedriver가 Chrome 버전을 자동 감지하지만, 메이저 업데이트 시 호환 문제 발생 가능
