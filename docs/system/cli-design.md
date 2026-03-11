# CLI 인터페이스 설계

## 1. 참조

- 시스템 분석: docs/system/system-analysis.md
- 기능 백로그: docs/project/features.md
- 로드맵: docs/project/roadmap.md

## 2. 명령행 인자 정의 (argparse 기반)

### 필수 인자

| 인자 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `--user` | str | SRT 회원 ID | `1234567890` |
| `--psw` | str | 비밀번호 | `abc1234` |
| `--dpt` | str | 출발역 (17개 역 목록 중 선택) | `동탄` |
| `--arr` | str | 도착역 (17개 역 목록 중 선택) | `동대구` |
| `--dt` | str | 출발날짜 (YYYYMMDD 형식) | `20260315` |
| `--tm` | str | 출발시간 (짝수 시간, HH 형식) | `08` |

> `manual_login.py` 진입점에서는 `--user`, `--psw`가 불필요하다.

### 선택 인자 (현재 구현됨)

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--num` | int | `2` | 확인할 기차 개수 (상위 N개) |
| `--reserve` | bool | `False` | 예약 대기 신청 여부 |
| `--anti-bot` | str | `undetected` | 봇 탐지 우회 방법 (`undetected` / `stealth` / `enhanced`) |
| `--delay-min` | int | `60` | 새로고침 최소 대기 시간 (초) |
| `--delay-max` | int | `120` | 새로고침 최대 대기 시간 (초) |
| `--use-profile` | bool | `True` | Chrome 프로필 재사용 여부 |
| `--profile-dir` | str | `None` | Chrome 프로필 디렉토리 경로 |

### 선택 인자 (로드맵 M1~M3 추가 예정)

| 인자 | 타입 | 기본값 | 대상 기능 | 마일스톤 |
|------|------|--------|-----------|----------|
| `--log-level` | str | `INFO` | 로그 레벨 (`DEBUG` / `INFO` / `WARNING` / `ERROR`) | F-10, M2 |
| `--headless` | bool | `False` | 헤드리스 모드 (브라우저 UI 없이 실행) | F-12, M3 |

> `--log-level`과 `--headless`는 각 기능 구현 시 `util.py`의 `parse_cli_args()`에 추가한다.

### 환경변수 폴백 (F-07, M1)

`.env` 파일에서 로드하며, CLI 인자가 우선 적용된다. python-dotenv 패키지 사용.

| 환경변수 | 대응 CLI 인자 | 마일스톤 |
|----------|---------------|----------|
| `SRT_USER` | `--user` | M1 |
| `SRT_PASSWORD` | `--psw` | M1 |
| `SRT_DPT` | `--dpt` | M1 |
| `SRT_ARR` | `--arr` | M1 |
| `SRT_DT` | `--dt` | M1 |
| `SRT_TM` | `--tm` | M1 |
| `ANTI_BOT_METHOD` | `--anti-bot` | M1 |
| `RETRY_DELAY_MIN` | `--delay-min` | M1 |
| `RETRY_DELAY_MAX` | `--delay-max` | M1 |
| `TELEGRAM_TOKEN` | (코드 내 설정) | F-09, M2 |
| `TELEGRAM_CHAT_ID` | (코드 내 설정) | F-09, M2 |
| `LOG_LEVEL` | `--log-level` | F-10, M2 |

우선순위 체인: **CLI 인자 > 환경변수(.env) > 기본값**

`.env.example` 템플릿 파일을 제공하여 사용자가 복사 후 수정할 수 있도록 한다.

## 3. 출력 포맷 컨벤션

### 성공 메시지

```
============================================================
예약 성공!
- 열차: {출발시간} ~ {도착시간}
- 좌석: 일반석
============================================================
```

### 에러 메시지

입력 검증 에러 (프로세스 시작 전 즉시 종료):

```
에러: 필수 인자가 누락되었습니다: user, psw
사용법: python quickstart.py --user USER --psw PASSWORD --dpt 출발역 --arr 도착역 --dt 날짜 --tm 시간
```

커스텀 예외별 에러 메시지:

| 예외 | 메시지 패턴 | 예시 |
|------|-------------|------|
| `InvalidStationNameError` | `{역명}은(는) 유효하지 않은 역명입니다. 가능한 역: {역 목록}` | `"강남은(는) 유효하지 않은 역명입니다..."` |
| `InvalidDateFormatError` | `날짜 형식이 올바르지 않습니다. YYYYMMDD 형식으로 입력하세요: {입력값}` | `"날짜 형식이 올바르지 않습니다... 2026031"` |
| `InvalidDateError` | `유효하지 않은 날짜입니다: {입력값}` | `"유효하지 않은 날짜입니다: 20260230"` |
| `InvalidTimeFormatError` | `시간은 짝수여야 합니다 (00, 02, ..., 22): {입력값}` | `"시간은 짝수여야 합니다... 09"` |

런타임 에러 (예약 프로세스 중):

```
에러 발생: {에러 메시지}
```

### 로그 포맷

현재 `logging` 모듈 기본 포맷 사용. F-10 구현 시 아래 포맷으로 표준화:

```
[{YYYY-MM-DD HH:MM:SS}] [{LEVEL}] {message}
```

레벨별 용도:

| 레벨 | 용도 | 예시 |
|------|------|------|
| DEBUG | 내부 디버그 정보 | CSS Selector 탐색, 요소 상태 |
| INFO | 진행 단계, 검색 상태 | 로그인 성공, 검색 시작, 새로고침 횟수 |
| WARNING | 재시도 가능한 문제 | Alert 발생, 요소 클릭 실패 재시도 |
| ERROR | 치명적 오류 | 로그인 실패, 브라우저 크래시 |

## 4. 진입점 (Entrypoint)

### quickstart.py -- 자동 로그인 모드

```bash
python quickstart.py \
  --user 1234567890 \
  --psw password \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20260315 \
  --tm 08 \
  --num 2 \
  --reserve False \
  --anti-bot undetected \
  --delay-min 60 \
  --delay-max 120
```

실행 흐름:
1. CLI 인자 파싱 (`parse_cli_args`)
2. 필수 인자 누락 확인
3. SRT 인스턴스 생성 (입력 검증 포함)
4. `srt.run(login_id, login_psw)` 호출
5. run() 내부: `run_driver() -> login() -> go_search() -> check_result()`

### manual_login.py -- 수동 로그인 모드

```bash
python manual_login.py \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20260315 \
  --tm 08
```

실행 흐름:
1. CLI 인자 파싱 (user/psw 불필요)
2. SRT 인스턴스 생성
3. `run_driver()` -- Chrome 창 열기
4. SRT 로그인 페이지로 이동
5. 사용자에게 수동 로그인 안내 (stdin 대기)
6. `check_login()` 로그인 확인
7. `go_search() -> check_result()` 자동 예약 시작

특이사항:
- `use_profile = False` (충돌 방지)
- `retry_delay_min/max = 150/300` (더 긴 대기)
- `anti_bot_method = 'stealth'` (수동 모드 기본값)

### srt_playwright.py -- Playwright 기반 (실험적)

```bash
python srt_playwright.py \
  --user 1234567890 \
  --psw password \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20260315 \
  --tm 08
```

특이사항:
- SRT 패키지(`srt_reservation`)를 사용하지 않는 독립 스크립트
- Playwright 기반 별도 구현 (코드 중복 존재)
- `requirements-playwright.txt` 별도 의존성

## 5. 에러 처리 전략

### 5.1 입력 검증 (프로세스 시작 전)

`SRT.__init__()` -> `check_input()`에서 수행. 검증 실패 시 커스텀 예외 발생 후 즉시 종료.

| 검증 대상 | 예외 | 검증 규칙 |
|-----------|------|-----------|
| 출발역/도착역 | `InvalidStationNameError` | `validation.station_list` (17개 역)에 포함 여부 |
| 날짜 형식 | `InvalidDateFormatError` | YYYYMMDD 8자리 숫자 |
| 날짜 유효성 | `InvalidDateError` | `datetime.strptime` 파싱 가능 여부 |
| 시간 형식 | `InvalidTimeFormatError` | 2자리 숫자, 짝수 (00, 02, ..., 22) |

### 5.2 런타임 에러 (현재 구현)

| 예외 | 현재 처리 방법 |
|------|---------------|
| `ElementClickInterceptedException` | JavaScript `click()` 으로 재시도 |
| `StaleElementReferenceException` | 무시하고 계속 진행 |
| `UnexpectedAlertPresentException` | Alert 자동 수락 후 계속 |
| 브라우저 세션 끊김 | `_is_browser_alive()` 헬퍼로 감지, 에러 메시지 출력 후 종료 |

### 5.3 에러 리커버리 (F-08, M1 예정)

| 에러 유형 | 복구 전략 | 최대 재시도 |
|-----------|-----------|-------------|
| `TimeoutException` | 동일 작업 자동 재시도 | 3회 |
| `ConnectionError` | 네트워크 대기 후 재시도 | 3회 |
| 세션 만료 | 자동 재로그인 후 검색 재개 | 2회 |
| 브라우저 크래시 | WebDriver 재초기화 + 전체 프로세스 재시작 | 1회 |
| 최대 재시도 초과 | 명확한 에러 메시지 출력 후 종료 (exit code 1) | - |

복구 이력은 로깅으로 기록하며, F-10 구현 후 로그 파일에도 저장된다.

## 6. 확장 계획 (로드맵 연동)

### M0: 프로젝트 기반 구축 (현재)
- system-analysis.md 완료
- 개발 환경 정비
- CLI/모듈 설계 문서 작성

### M1: 안정성 강화

| 기능 | 주요 변경 | 영향 파일 |
|------|-----------|-----------|
| F-07 설정 관리 | .env 파일 로드, 환경변수 폴백 체인 | `util.py`, `quickstart.py`, `manual_login.py`, 신규 `.env.example` |
| F-08 에러 리커버리 | 재시도 로직, 재로그인, WebDriver 재초기화 | `main.py` (SRT 클래스) |

### M2: 사용자 경험 개선

| 기능 | 주요 변경 | 영향 파일 |
|------|-----------|-----------|
| F-09 Telegram 알림 | Bot API 연동, 알림 발송 | 신규 `srt_reservation/notifier.py`, `main.py` |
| F-10 로깅 개선 | 파일 핸들러, 로그 로테이션, --log-level | `main.py`, `util.py`, 신규 `srt_reservation/logger.py` |

### M3: 기능 확장

| 기능 | 주요 변경 | 영향 파일 |
|------|-----------|-----------|
| F-11 다중 검색 조건 | 복수 날짜/시간 파싱, 순차 검색 루프 | `util.py`, `main.py` |
| F-12 헤드리스 모드 | --headless 옵션, 결과 콘솔 출력 보강 | `util.py`, `main.py` (드라이버 옵션) |

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-11 | 초안 작성 | M0 설계 문서 작성 |
