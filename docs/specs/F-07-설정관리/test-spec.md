# F-07 설정 관리 -- 테스트 명세

## 참조

- 설계서: docs/specs/F-07-설정관리/change-design.md
- 인수조건: docs/project/features.md #F-07

## 테스트 전략

### 테스트 파일 구조

| 파일 | 대상 | 유형 |
|------|------|------|
| `tests/test_config.py` | `srt_reservation/config.py` | 단위 테스트 |
| `tests/test_main.py` | 기존 SRT 클래스 | 회귀 테스트 (기존 테스트 유지) |

### 테스트 패턴

- `unittest.mock.patch.dict`으로 환경변수 모킹
- `tmp_path` fixture로 임시 `.env` 파일 생성
- 기존 `test_main.py` 패턴과 동일하게 `pytest` + `unittest.mock` 사용

## 단위 테스트

### Config.load_from_env()

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `load_from_env` | .env 파일 정상 로드 | 유효한 .env 파일 경로 | `{"SRT_USER": "1234567890", "SRT_PASSWORD": "abc1234", ...}` dict 반환 |
| `load_from_env` | .env 파일 미존재 | 존재하지 않는 경로 | 빈 dict `{}` 반환, 에러 없음 |
| `load_from_env` | .env 파일 빈 파일 | 빈 .env 파일 경로 | 빈 dict `{}` 반환 |
| `load_from_env` | .env 파일 주석만 있는 경우 | 주석만 포함된 .env 파일 | 빈 dict `{}` 반환 |
| `load_from_env` | 일부 변수만 설정된 .env | `SRT_USER`와 `SRT_PASSWORD`만 있는 .env | `{"SRT_USER": "1234567890", "SRT_PASSWORD": "abc1234"}` 반환 |
| `load_from_env` | 따옴표로 감싼 값 | `SRT_USER="1234567890"` | `{"SRT_USER": "1234567890"}` (따옴표 제거됨) |

### Config.load_from_cli()

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `load_from_cli` | 모든 CLI 인자 제공 | `Namespace(user="1234", psw="pass", dpt="동탄", arr="동대구", dt="20260315", tm="08", num=3, ...)` | `{"user": "1234", "password": "pass", "dpt": "동탄", "arr": "동대구", "dt": "20260315", "tm": "08", "num": 3, ...}` |
| `load_from_cli` | 필수 인자만 제공 | `Namespace(user="1234", psw="pass", dpt="동탄", arr="동대구", dt="20260315", tm="08", num=None, ...)` | `{"user": "1234", "password": "pass", "dpt": "동탄", "arr": "동대구", "dt": "20260315", "tm": "08"}` (None 값 제외) |
| `load_from_cli` | 인자 없음 (모두 None) | `Namespace(user=None, psw=None, ...)` | 빈 dict `{}` |
| `load_from_cli` | 일부 인자만 제공 | `Namespace(user="1234", psw=None, dpt="동탄", ...)` | `{"user": "1234", "dpt": "동탄"}` (None 제외) |

### Config.merge()

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `merge` | CLI만 있을 때 | cli=`{"user": "CLI_USER"}`, env=`{}` | `{"user": "CLI_USER", "password": None, "dpt": None, ...}` |
| `merge` | .env만 있을 때 | cli=`{}`, env=`{"SRT_USER": "ENV_USER", "SRT_PASSWORD": "ENV_PASS"}` | `{"user": "ENV_USER", "password": "ENV_PASS", "dpt": None, ...}` |
| `merge` | CLI가 .env보다 우선 | cli=`{"user": "CLI_USER"}`, env=`{"SRT_USER": "ENV_USER"}` | `{"user": "CLI_USER", ...}` (CLI 우선) |
| `merge` | 기본값 폴백 | cli=`{}`, env=`{}` | `{"num": 2, "reserve": False, "anti_bot": "undetected", "delay_min": 60, "delay_max": 120, ...}` |
| `merge` | .env + 기본값 혼합 | cli=`{}`, env=`{"SRT_NUM": "5"}` | `{"num": 5, ...}` (env 값이 기본값보다 우선) |
| `merge` | 타입 변환: SRT_NUM | cli=`{}`, env=`{"SRT_NUM": "3"}` | `{"num": 3, ...}` (int 변환 성공) |
| `merge` | 타입 변환: SRT_RESERVE (True) | cli=`{}`, env=`{"SRT_RESERVE": "True"}` | `{"reserve": True, ...}` (bool 변환 성공) |
| `merge` | 타입 변환: SRT_RESERVE (False) | cli=`{}`, env=`{"SRT_RESERVE": "False"}` | `{"reserve": False, ...}` |
| `merge` | 타입 변환 실패: SRT_NUM | cli=`{}`, env=`{"SRT_NUM": "abc"}` | `{"num": 2, ...}` (기본값 폴백) + WARNING 로그 |
| `merge` | 타입 변환 실패: SRT_RESERVE | cli=`{}`, env=`{"SRT_RESERVE": "maybe"}` | `{"reserve": False, ...}` (기본값 폴백) + WARNING 로그 |

### Config.validate_required()

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `validate_required` | 모든 필수값 존재 | config=`{"user": "1234", "password": "pass", "dpt": "동탄", "arr": "동대구", "dt": "20260315", "tm": "08"}`, keys=`["user", "password", "dpt", "arr", "dt", "tm"]` | None (성공, 예외 없음) |
| `validate_required` | 단일 필수값 누락 | config=`{"user": None, "password": "pass", ...}`, keys=`["user", "password", ...]` | `ValueError("필수 설정이 누락되었습니다: user. CLI 인자 또는 .env 파일에서 설정하세요.")` |
| `validate_required` | 다수 필수값 누락 | config=`{"user": None, "password": None, ...}`, keys=`["user", "password", ...]` | `ValueError("필수 설정이 누락되었습니다: user, password. CLI 인자 또는 .env 파일에서 설정하세요.")` |
| `validate_required` | 빈 문자열은 유효 | config=`{"user": "", ...}`, keys=`["user"]` | None (빈 문자열은 None이 아니므로 통과. 실제 검증은 SRT.check_input()에서 수행) |
| `validate_required` | manual_login 모드 (user/password 불필요) | config=`{"user": None, "password": None, "dpt": "동탄", ...}`, keys=`["dpt", "arr", "dt", "tm"]` | None (user/password는 검증 대상이 아님) |

## 통합 테스트

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| Config 전체 플로우 | .env만으로 실행 | .env에 모든 필수값 설정, CLI 인자 없음 | 병합 결과에 .env 값 반영, validate_required 통과 |
| Config 전체 플로우 | CLI 인자가 .env 덮어쓰기 | .env에 `SRT_USER=ENV_USER`, CLI에 `--user CLI_USER` | 병합 결과 `user == "CLI_USER"` |
| Config 전체 플로우 | .env 미존재 + CLI만 | .env 파일 없음, CLI에 모든 필수값 | 병합 결과에 CLI 값 반영, validate_required 통과 |
| Config 전체 플로우 | .env 미존재 + CLI 부분적 | .env 파일 없음, CLI에 필수값 일부 누락 | validate_required에서 ValueError 발생 |
| util.py 호환성 | 선택 인자 기본값 None | `parse_cli_args()` 호출 (인자 없이) | `args.num is None`, `args.reserve is None`, `args.anti_bot is None` |

## 경계 조건 / 에러 케이스

- .env 파일에 잘못된 형식의 줄이 있을 때 (예: `=value`, `KEY_ONLY`): `python-dotenv`가 무시하므로 에러 없이 건너뜀
- .env 파일 인코딩이 UTF-8이 아닐 때: `python-dotenv`가 처리. 한글 역명(`동탄`) 포함 시 UTF-8 필수.
- `SRT_NUM=0`: 유효한 int 변환이지만, SRT 클래스에서 0개 기차를 확인하게 되어 무의미. 이 검증은 Config의 책임이 아니라 SRT.check_input()의 책임.
- `SRT_NUM=-1`: int 변환 성공하지만 음수. Config에서는 타입 변환만 수행하고 범위 검증은 하지 않음.
- `RETRY_DELAY_MIN > RETRY_DELAY_MAX`: Config에서 검증하지 않음 (SRT 클래스의 책임).
- `ANTI_BOT_METHOD=invalid_method`: Config에서 허용. SRT 클래스의 `run_driver()`에서 `enhanced`로 폴백됨 (기존 동작).
- `.env` 파일 권한 없음 (읽기 불가): 빈 dict 반환 + WARNING 로그 `".env 파일을 읽을 수 없습니다: {경로}"`
- `validate_required()` 에러 메시지: `"필수 설정이 누락되었습니다: user, password. CLI 인자 또는 .env 파일에서 설정하세요."` (누락된 키를 쉼표로 구분, 정확한 문자열)
- 타입 변환 실패 WARNING 로그: `"환경변수 SRT_NUM의 값 'abc'를 int로 변환할 수 없습니다. 기본값 2를 사용합니다."` (정확한 문자열)
- SRT_RESERVE 타입 변환 실패 WARNING 로그: `"환경변수 SRT_RESERVE의 값 'maybe'를 bool로 변환할 수 없습니다. 기본값 False를 사용합니다."` (정확한 문자열)

## E2E 시나리오

### E2E-01: .env 파일만으로 실행 (핵심 사용자 흐름)

**전제 조건**: `.env` 파일에 모든 필수값이 설정됨

```
1. .env 파일 생성:
   SRT_USER=1234567890
   SRT_PASSWORD=testpass
   SRT_DPT=동탄
   SRT_ARR=동대구
   SRT_DT=20260315
   SRT_TM=08

2. CLI 인자 없이 실행: python quickstart.py

3. 검증:
   - Config.load_from_env()가 .env 값을 로드
   - Config.validate_required()가 통과
   - SRT 인스턴스가 .env 값으로 생성됨
   - (WebDriver 관련 동작은 모킹)
```

### E2E-02: CLI 인자가 .env 값을 덮어쓰기

**전제 조건**: `.env` 파일에 `SRT_USER=ENV_USER` 설정됨

```
1. 실행: python quickstart.py --user CLI_USER

2. 검증:
   - 병합 결과에서 user == "CLI_USER" (CLI 우선)
   - password는 .env에서 로드
   - SRT.set_log_info()에 "CLI_USER" 전달됨
```

### E2E-03: .env 미존재 + CLI 인자만으로 실행 (상태 갱신 시나리오)

**전제 조건**: `.env` 파일 없음

```
1. 실행: python quickstart.py --user 1234 --psw pass --dpt 동탄 --arr 동대구 --dt 20260315 --tm 08

2. 검증:
   - Config.load_from_env()가 빈 dict 반환
   - CLI 인자만으로 SRT 인스턴스 생성 성공
   - 기존 동작과 완전히 동일
```

### E2E-04: 필수값 누락 시 에러 메시지 (에러 CTA)

**전제 조건**: `.env` 파일 없음, CLI에 `--user`와 `--psw` 누락

```
1. 실행: python quickstart.py --dpt 동탄 --arr 동대구 --dt 20260315 --tm 08

2. 검증:
   - stderr 또는 stdout에 에러 메시지 출력:
     "에러: 필수 설정이 누락되었습니다: user, password"
     "CLI 인자 또는 .env 파일에서 설정하세요."
   - exit code 1로 종료
   - SRT 인스턴스 생성되지 않음
```

### E2E-05: manual_login.py에서 .env 로드

**전제 조건**: `.env` 파일에 `SRT_DPT=동탄`, `SRT_ARR=동대구`, `SRT_DT=20260315`, `SRT_TM=08` 설정됨

```
1. 실행: python manual_login.py (인자 없이)

2. 검증:
   - .env에서 dpt, arr, dt, tm 로드
   - user/password 누락이어도 validate_required 통과 (manual_login은 user/password 불필요)
   - SRT 인스턴스 생성 성공
```

## 회귀 테스트

| 기존 기능 | 영향 여부 | 검증 방법 |
|-----------|-----------|-----------|
| F-01 SRT 로그인 | 영향 없음 | SRT 클래스 변경 없음. `test_main.py::TestSRTLogin` 통과 확인 |
| F-02 기차 검색 | 영향 없음 | SRT 클래스 변경 없음. `test_main.py::TestSRTInputValidation` 통과 확인 |
| F-03 자동 새로고침/예약 | 영향 없음 | SRT 클래스 변경 없음. `test_main.py::TestBookTicket`, `TestRefreshResult` 통과 확인 |
| F-04 예약 대기 | 영향 없음 | SRT 클래스 변경 없음. `test_main.py::TestReserveTicket` 통과 확인 |
| F-05 봇 탐지 우회 | 영향 없음 | SRT 클래스 변경 없음. `test_main.py::TestRunDriver` 통과 확인 |
| F-06 CLI 인터페이스 | **영향 있음** | `util.py` 선택 인자 기본값 `None`으로 변경. `parse_cli_args()` 직접 호출하는 코드가 있으면 `None` 처리 필요. 현재 테스트에서 `parse_cli_args()`를 직접 테스트하는 케이스 없으므로 영향 없음. |
| 기존 test_main.py 전체 | 영향 없음 | SRT 클래스 생성자를 직접 호출하므로 config.py 변경과 무관. `pytest tests/test_main.py -v` 전체 통과 확인 |
| 기존 test_validation.py | 영향 없음 | validation.py 변경 없음. `pytest tests/test_validation.py -v` 통과 확인 |
| 기존 test_exceptions.py | 영향 없음 | exceptions.py 변경 없음. `pytest tests/test_exceptions.py -v` 통과 확인 |

### 회귀 테스트 실행 명령

```bash
# 전체 기존 테스트 실행 (F-07 구현 후)
pytest tests/ -v

# 특정 회귀 확인
pytest tests/test_main.py -v          # SRT 클래스 호환성
pytest tests/test_validation.py -v    # 역 목록 무결성
pytest tests/test_exceptions.py -v    # 예외 클래스 호환성
```

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-07 설정 관리 기능 테스트 명세 |
