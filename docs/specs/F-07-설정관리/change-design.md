# F-07 설정 관리 -- 변경 설계서

## 1. 참조

- 인수조건: docs/project/features.md #F-07
- 시스템 분석: docs/system/system-analysis.md
- CLI 설계: docs/system/cli-design.md
- 마일스톤: M1 (의존성: F-06 완료)

## 2. 개요

### 기능 목표

`.env` 파일 기반의 환경변수 설정 관리를 도입하여, 매번 긴 CLI 인자를 입력하지 않고도 예약 프로세스를 실행할 수 있도록 한다.

### 인수조건

- [ ] `.env` 파일에서 `SRT_USER`, `SRT_PASSWORD`, `SRT_DPT`, `SRT_ARR` 등 환경변수 로드
- [ ] `.env` 파일이 없으면 CLI 인자로 폴백
- [ ] `.env.example` 템플릿 파일 제공 (이미 생성됨)
- [ ] CLI 인자가 `.env` 값보다 우선 적용

## 3. 현황 분석

### 현재 설정 관리 방식

현재 모든 설정은 CLI 인자(`argparse`)로만 관리된다.

```bash
python quickstart.py \
  --user 1234567890 --psw abc1234 \
  --dpt 동탄 --arr 동대구 --dt 20260315 --tm 08 \
  --num 2 --reserve False --anti-bot undetected \
  --delay-min 60 --delay-max 120
```

**데이터 흐름 (현재)**:

```
CLI (argparse) --> quickstart.py (필수 인자 검증) --> SRT.__init__() (입력 검증)
```

### 문제점

1. **사용성 저하**: 실행할 때마다 12개 인자를 입력해야 함
2. **반복 입력**: 로그인 정보(`--user`, `--psw`)와 자주 사용하는 역(`--dpt`, `--arr`)을 매번 입력
3. **환경변수 폴백 미구현**: `main.py`에서 `ANTI_BOT_METHOD`와 `CHROMEDRIVER_PATH`만 `os.environ.get()`으로 참조하고 있으나, 체계적인 폴백 체인이 없음
4. **보안 우려**: 비밀번호를 CLI 인자로 전달하면 셸 히스토리에 노출됨

### 기존 환경변수 사용 현황 (main.py)

| 변수 | 위치 | 용도 |
|------|------|------|
| `CHROMEDRIVER_PATH` | main.py:32 | ChromeDriver 바이너리 경로 (기본: `/usr/local/bin/chromedriver`) |
| `ANTI_BOT_METHOD` | main.py:36 | 봇 탐지 우회 방법 (기본: `undetected`) |

이 두 변수는 모듈 레벨 전역 변수로 `os.environ.get()`을 직접 호출한다. `config.py` 도입 후에도 하위 호환성을 유지해야 한다.

## 4. 변경 범위

- 변경 유형: 신규 추가 + 기존 수정
- 영향 받는 모듈: `util.py`, `quickstart.py`, `manual_login.py`, `main.py` (최소 변경)

## 5. 아키텍처 결정

### 결정 1: 환경변수 로드 라이브러리

- **선택지**: A) `python-dotenv` / B) 직접 `.env` 파서 구현
- **결정**: A) `python-dotenv`
- **근거**: 업계 표준 라이브러리, `.env` 파일 포맷 호환성 보장 (주석, 따옴표, 빈 줄 등), 유지보수 비용 없음. `requirements.txt`에 `python-dotenv>=1.0.0` 추가.

### 결정 2: Config 모듈 위치

- **선택지**: A) `srt_reservation/config.py` 신규 모듈 / B) `util.py`에 추가
- **결정**: A) `srt_reservation/config.py` 신규 모듈
- **근거**: 관심사 분리. `util.py`는 CLI 파싱만 담당하고, `config.py`는 환경변수 로드 및 병합만 담당. SRT 클래스는 변경 불필요.

### 결정 3: SRT 클래스 변경 범위

- **선택지**: A) SRT 클래스가 직접 Config를 읽음 / B) 엔트리포인트가 Config를 읽어서 SRT에 전달
- **결정**: B) 엔트리포인트가 Config를 읽어서 SRT에 전달
- **근거**: SRT 클래스의 생성자 시그니처를 변경하지 않아 기존 테스트 전면 수정 불필요. 설정 로드 책임을 엔트리포인트에 위임.

### 결정 4: main.py 모듈 레벨 환경변수 처리

- **선택지**: A) `main.py`의 `ANTI_BOT_METHOD`, `chromedriver_path` 전역 변수 유지 / B) Config 경유로 변경
- **결정**: A) 유지
- **근거**: main.py의 전역 변수는 SRT 클래스 생성자에서 `anti_bot_method` 파라미터가 `None`일 때 폴백으로만 사용됨. Config가 엔트리포인트에서 이미 환경변수를 읽어 CLI 인자로 전달하므로, 전역 변수는 직접 SRT 인스턴스를 생성하는 외부 코드를 위한 하위 호환성으로 유지.

## 6. 상세 설계

### 6.1 신규 모듈: `srt_reservation/config.py`

#### Config 클래스

```python
class Config:
    """환경변수(.env) + CLI 인자 병합 설정 관리자"""
```

#### 환경변수 매핑 테이블

| 환경변수 | CLI 인자 | Config 속성 | 타입 | 기본값 | 필수 여부 |
|----------|----------|-------------|------|--------|-----------|
| `SRT_USER` | `--user` | `user` | str | None | 필수 (quickstart) |
| `SRT_PASSWORD` | `--psw` | `password` | str | None | 필수 (quickstart) |
| `SRT_DPT` | `--dpt` | `dpt` | str | None | 필수 |
| `SRT_ARR` | `--arr` | `arr` | str | None | 필수 |
| `SRT_DT` | `--dt` | `dt` | str | None | 필수 |
| `SRT_TM` | `--tm` | `tm` | str | None | 필수 |
| `SRT_NUM` | `--num` | `num` | int | 2 | 선택 |
| `SRT_RESERVE` | `--reserve` | `reserve` | bool | False | 선택 |
| `ANTI_BOT_METHOD` | `--anti-bot` | `anti_bot` | str | "undetected" | 선택 |
| `RETRY_DELAY_MIN` | `--delay-min` | `delay_min` | int | 60 | 선택 |
| `RETRY_DELAY_MAX` | `--delay-max` | `delay_max` | int | 120 | 선택 |

> `--use-profile`, `--profile-dir`은 환경변수에 대응하지 않음 (CLI 전용).

#### 메서드 설계

**`load_from_env(env_path: str = ".env") -> dict`** (정적 메서드)

- `python-dotenv`의 `dotenv_values(env_path)`로 `.env` 파일 로드
- `.env` 파일이 존재하지 않으면 빈 dict 반환 (에러 아님)
- 반환값: `{"SRT_USER": "1234567890", "SRT_PASSWORD": "abc1234", ...}` (원시 환경변수 dict)

**`load_from_cli(args: argparse.Namespace) -> dict`** (정적 메서드)

- argparse Namespace에서 값이 `None`이 아닌 인자만 추출
- CLI 인자명을 Config 속성명으로 매핑
- 반환값: `{"user": "1234567890", "dpt": "동탄", ...}` (정규화된 dict)

**`merge(cli_values: dict, env_values: dict) -> dict`** (정적 메서드)

- 우선순위: CLI 인자 > 환경변수(.env) > 기본값
- 환경변수명을 Config 속성명으로 매핑 (`SRT_USER` -> `user`)
- 타입 변환 수행: `SRT_NUM` -> int, `SRT_RESERVE` -> bool
- 반환값: 병합된 설정 dict

  ```python
  {
      "user": "1234567890",
      "password": "abc1234",
      "dpt": "동탄",
      "arr": "동대구",
      "dt": "20260315",
      "tm": "08",
      "num": 2,
      "reserve": False,
      "anti_bot": "undetected",
      "delay_min": 60,
      "delay_max": 120,
  }
  ```

**`validate_required(config: dict, required_keys: list[str]) -> None`**

- 필수 키 중 값이 `None`인 항목을 검사
- 누락 시 `ValueError` 발생
- 에러 메시지 형식: `"필수 설정이 누락되었습니다: user, password. CLI 인자 또는 .env 파일에서 설정하세요."`

#### 타입 변환 규칙

| 환경변수 | 변환 방법 | 무효값 처리 |
|----------|-----------|-------------|
| `SRT_NUM` | `int()` | `ValueError` -> 기본값 2 사용 + 경고 로그 |
| `SRT_RESERVE` | `str_to_bool()` (util.py 재사용) | `ArgumentTypeError` -> 기본값 False 사용 + 경고 로그 |
| `RETRY_DELAY_MIN` | `int()` | `ValueError` -> 기본값 60 사용 + 경고 로그 |
| `RETRY_DELAY_MAX` | `int()` | `ValueError` -> 기본값 120 사용 + 경고 로그 |

> 타입 변환 실패 시 프로세스를 중단하지 않고 기본값으로 폴백한다. 필수 문자열 값(`user`, `password` 등)은 타입 변환이 불필요하므로 이 규칙의 대상이 아니다.

#### 환경변수명 -> Config 속성명 매핑 상수

```python
ENV_KEY_MAP = {
    "SRT_USER": "user",
    "SRT_PASSWORD": "password",
    "SRT_DPT": "dpt",
    "SRT_ARR": "arr",
    "SRT_DT": "dt",
    "SRT_TM": "tm",
    "SRT_NUM": "num",
    "SRT_RESERVE": "reserve",
    "ANTI_BOT_METHOD": "anti_bot",
    "RETRY_DELAY_MIN": "delay_min",
    "RETRY_DELAY_MAX": "delay_max",
}

DEFAULTS = {
    "num": 2,
    "reserve": False,
    "anti_bot": "undetected",
    "delay_min": 60,
    "delay_max": 120,
}
```

### 6.2 기존 파일 수정: `srt_reservation/util.py`

#### 변경 내용

현재 `parse_cli_args()`에서 `--user`, `--psw`, `--dpt`, `--arr`, `--dt`, `--tm`은 `required` 미설정이지만 `default=None`으로 선택적이다. 이 동작은 **변경하지 않는다**. argparse는 그대로 유지하고, 필수 인자 검증은 `Config.validate_required()`에서 수행한다.

변경 없음 (현재 구현이 이미 선택적 인자로 되어 있어 .env 폴백과 호환됨).

### 6.3 기존 파일 수정: `quickstart.py`

#### 변경 내용

```
[변경 전]
CLI 파싱 -> 필수 인자 검증 (수동) -> SRT 생성 -> run()

[변경 후]
CLI 파싱 -> .env 로드 -> 병합 -> 필수 인자 검증 (Config) -> SRT 생성 -> run()
```

주요 변경:

1. `from srt_reservation.config import Config` 추가
2. 기존 수동 필수 인자 검증 (`missing_args` 로직) 제거
3. `Config.load_from_env()`, `Config.load_from_cli()`, `Config.merge()` 호출
4. `Config.validate_required()` 호출 (quickstart용 필수 키: `["user", "password", "dpt", "arr", "dt", "tm"]`)
5. 병합된 config dict에서 SRT 생성자 인자 추출

`validate_required()` 실패 시 에러 메시지:

```
에러: 필수 설정이 누락되었습니다: user, password
CLI 인자 또는 .env 파일에서 설정하세요.
사용법: python quickstart.py --user USER --psw PASSWORD --dpt 출발역 --arr 도착역 --dt 날짜 --tm 시간
```

### 6.4 기존 파일 수정: `manual_login.py`

#### 변경 내용

quickstart.py와 동일한 패턴 적용. 단, 필수 키에서 `user`, `password` 제외:

```python
Config.validate_required(config, ["dpt", "arr", "dt", "tm"])
```

수동 로그인 모드의 기존 하드코딩 기본값 유지:
- `use_profile = False`
- `retry_delay_min = 150`, `retry_delay_max = 300`
- `anti_bot_method = 'stealth'`

이 값들은 CLI 인자나 .env보다 manual_login.py의 하드코딩이 우선한다 (수동 모드 전용 동작).

### 6.5 기존 파일 수정: `requirements.txt`

```
python-dotenv>=1.0.0
```

추가.

### 6.6 기존 파일 수정: `main.py`

**변경 없음.** SRT 클래스의 생성자 시그니처, 메서드, 전역 변수 모두 유지.

## 7. 설정값 우선순위 (폴백 체인)

```
CLI 인자 > 환경변수(.env) > 기본값
```

### 폴백 흐름 예시

```
사용자가 `python quickstart.py --user OVERRIDE_USER` 실행

1. CLI: {"user": "OVERRIDE_USER"} (나머지 None)
2. .env: {"SRT_USER": "ENV_USER", "SRT_PASSWORD": "ENV_PASS", "SRT_DPT": "동탄", ...}
3. merge():
   - user: "OVERRIDE_USER" (CLI 우선)
   - password: "ENV_PASS" (.env 폴백)
   - dpt: "동탄" (.env 폴백)
   - num: 2 (기본값 폴백)
```

### 주의: argparse 기본값과 환경변수 구분

`argparse`의 `default=2` (예: `--num`)는 사용자가 CLI에서 `--num`을 지정하지 않아도 값이 `2`로 설정된다. 이 경우 CLI 값(`2`)이 환경변수의 `SRT_NUM`보다 우선하게 되어 환경변수가 무시되는 문제가 발생한다.

**해결 방법**: `Config.load_from_cli()`에서 argparse의 기본값과 실제 사용자 입력을 구분한다.

- 선택 인자 (`--num`, `--reserve`, `--anti-bot`, `--delay-min`, `--delay-max`)의 argparse `default`를 `None`으로 변경
- `load_from_cli()`에서 값이 `None`인 인자는 dict에 포함하지 않음
- 기본값은 `Config.DEFAULTS`에서만 관리

이를 위해 `util.py`의 선택 인자 기본값을 `None`으로 변경해야 한다:

```python
# 변경 전
parser.add_argument("--num", ..., default=2)
parser.add_argument("--reserve", ..., default=False)
parser.add_argument("--anti-bot", ..., default="undetected")
parser.add_argument("--delay-min", ..., default=60)
parser.add_argument("--delay-max", ..., default=120)
parser.add_argument("--use-profile", ..., default=True)

# 변경 후
parser.add_argument("--num", ..., default=None)
parser.add_argument("--reserve", ..., default=None)
parser.add_argument("--anti-bot", ..., default=None, choices=['undetected', 'stealth', 'enhanced'])
parser.add_argument("--delay-min", ..., default=None)
parser.add_argument("--delay-max", ..., default=None)
parser.add_argument("--use-profile", ..., default=None)
```

> `--reserve`와 `--use-profile`은 `type=str_to_bool`이므로 `default=None`에서 `None` 값은 argparse가 전달하지 않는다 (사용자가 인자를 생략하면 `None`).

## 8. 시퀀스 흐름

### quickstart.py 실행 흐름 (변경 후)

```
사용자 --> quickstart.py
              |
              +--> parse_cli_args()           # argparse (기존)
              |
              +--> Config.load_from_env()     # .env 파일 로드 (신규)
              |        |
              |        +--> dotenv_values(".env")
              |        +--> 파일 없으면 {} 반환
              |
              +--> Config.load_from_cli(args) # CLI 인자 추출 (신규)
              |        |
              |        +--> None이 아닌 값만 추출
              |
              +--> Config.merge(cli, env)     # 병합 (신규)
              |        |
              |        +--> CLI > env > defaults
              |
              +--> Config.validate_required() # 필수값 검증 (신규)
              |        |
              |        +--> 누락 시 ValueError
              |
              +--> SRT(config["dpt"], ...)    # 기존과 동일
              +--> srt.run(config["user"], config["password"])
```

## 9. 영향 분석

### 기존 API 변경

| 대상 | 현재 | 변경 후 | 하위 호환성 |
|------|------|---------|-------------|
| `SRT.__init__()` | 10개 파라미터 | 변경 없음 | 완전 호환 |
| `SRT.run()` | `login_id, login_psw` | 변경 없음 | 완전 호환 |
| `parse_cli_args()` | 선택 인자 기본값 설정됨 | 선택 인자 기본값 `None`으로 변경 | **비호환**: 직접 `parse_cli_args()` 호출 후 `args.num` 등을 사용하는 외부 코드가 있으면 `None` 처리 필요 |
| `str_to_bool()` | util.py 내 함수 | 변경 없음 (config.py에서 import하여 재사용) | 완전 호환 |

### 사이드 이펙트

1. **`parse_cli_args()` 기본값 변경**: 선택 인자 기본값이 `None`으로 바뀌므로, `quickstart.py`와 `manual_login.py` 외에 `parse_cli_args()`를 직접 호출하는 코드가 있다면 영향받음. 현재 코드베이스에서는 이 두 파일만 사용하므로 문제 없음.

2. **`srt_playwright.py`**: SRT 패키지를 사용하지 않는 독립 스크립트이므로 영향 없음.

3. **기존 테스트**: `test_main.py`에서 SRT 클래스를 직접 생성하므로 config.py 변경에 영향받지 않음. 단, `parse_cli_args()` 관련 테스트가 있다면 기본값 변경에 영향받을 수 있음 (현재 `parse_cli_args()` 테스트는 없음).

## 10. 영향 범위

### 수정 필요 파일

| 파일 | 변경 내용 | 위험도 |
|------|-----------|--------|
| `srt_reservation/util.py` | 선택 인자 기본값 `None`으로 변경 | 낮음 |
| `quickstart.py` | Config 로드 + 병합 로직 추가, 기존 수동 검증 로직 대체 | 중간 |
| `manual_login.py` | Config 로드 + 병합 로직 추가, 기존 수동 검증 로직 대체 | 중간 |
| `requirements.txt` | `python-dotenv>=1.0.0` 추가 | 낮음 |

### 신규 생성 파일

| 파일 | 내용 |
|------|------|
| `srt_reservation/config.py` | Config 클래스 (환경변수 로드, 병합, 검증) |
| `tests/test_config.py` | Config 클래스 유닛 테스트 |

### 변경 없는 파일

| 파일 | 이유 |
|------|------|
| `srt_reservation/main.py` | SRT 클래스 시그니처 유지, Config 의존성 없음 |
| `srt_reservation/exceptions.py` | 변경 불필요 |
| `srt_reservation/validation.py` | 변경 불필요 |
| `.env.example` | 이미 생성됨 |

## 11. 공유 유틸리티 반환값 계약

### `Config.load_from_env(env_path: str = ".env") -> dict`

- 반환: `dict[str, str]` -- 환경변수명(대문자)을 키로, 원시 문자열 값을 값으로 가지는 dict
- `.env` 파일 미존재: 빈 dict `{}` 반환 (에러 아님)
- `.env` 파일 파싱 오류: 빈 dict `{}` 반환 + WARNING 로그

### `Config.load_from_cli(args: argparse.Namespace) -> dict`

- 반환: `dict[str, Any]` -- Config 속성명(소문자)을 키로, 파싱된 값을 값으로 가지는 dict
- `None` 값인 인자는 dict에 포함하지 않음
- 예: `args.user="1234"`, `args.psw=None` -> `{"user": "1234"}`

### `Config.merge(cli_values: dict, env_values: dict) -> dict`

- 반환: `dict[str, Any]` -- 병합된 설정값 dict. 모든 설정 키가 포함됨 (값이 없으면 `None`).
- 타입 변환 실패: 기본값으로 폴백 + WARNING 로그
- 필수 키라도 값이 없으면 `None`으로 포함 (검증은 `validate_required()`에서 수행)

### `Config.validate_required(config: dict, required_keys: list[str]) -> None`

- 반환: `None` (성공 시)
- 실패: `ValueError("필수 설정이 누락되었습니다: {누락된 키 목록}. CLI 인자 또는 .env 파일에서 설정하세요.")`

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-07 설정 관리 기능 변경 설계 |
