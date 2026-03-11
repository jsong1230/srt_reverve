# F-10 로깅 개선 -- 테스트 명세

## 참조

- 설계서: docs/specs/F-10-로깅개선/change-design.md
- 인수조건: docs/project/features.md #F-10

## 테스트 전략

- **유닛 테스트**: `setup_logger()` 함수의 핸들러 구성, 포맷, 레벨 설정
- **통합 테스트**: CLI `--log-level` 옵션 파싱 + Config 폴백 체인 동작
- **E2E 시나리오**: 실행 후 로그 파일 생성 및 내용 검증
- **Mock 전략**: 파일 시스템은 실제 임시 디렉토리(`tmp_path` fixture) 사용, WebDriver는 mock

## 테스트 파일

- `tests/test_logger.py` -- setup_logger() 유닛 테스트
- `tests/test_util.py` (기존 파일 확장) -- --log-level 파싱 테스트
- `tests/test_config.py` (기존 파일 확장) -- LOG_LEVEL 환경변수 테스트

---

## 단위 테스트: `setup_logger()`

| # | 대상 | 시나리오 | 입력 | 예상 결과 |
|---|------|----------|------|-----------|
| U-01 | `setup_logger()` | 기본 호출 시 루트 로거에 핸들러 2개 설정 | `log_level="INFO", log_dir=tmp_path/"logs"` | 루트 로거의 핸들러 수 == 2 (StreamHandler 1개 + TimedRotatingFileHandler 1개) |
| U-02 | `setup_logger()` | 콘솔 핸들러 존재 확인 | `log_level="INFO", log_dir=tmp_path/"logs"` | 핸들러 중 `StreamHandler` 인스턴스 1개 존재 |
| U-03 | `setup_logger()` | 파일 핸들러 존재 확인 | `log_level="INFO", log_dir=tmp_path/"logs"` | 핸들러 중 `TimedRotatingFileHandler` 인스턴스 1개 존재 |
| U-04 | `setup_logger()` | 로그 디렉토리 자동 생성 | `log_dir=tmp_path/"nonexistent/logs"` | 디렉토리가 생성되고, 파일 핸들러가 정상 동작 |
| U-05 | `setup_logger()` | 로그 파일 생성 확인 | `log_dir=tmp_path/"logs"` 후 `logger.info("테스트")` | `tmp_path/logs/srt_.log` 파일 존재 |
| U-06 | `setup_logger()` | 로그 포맷 정확성 -- 콘솔 | `log_level="INFO"` 후 `logger.info("테스트 메시지")` | 출력이 `[YYYY-MM-DD HH:MM:SS] [INFO] 테스트 메시지` 패턴과 일치 (정규식: `^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[INFO\] 테스트 메시지$`) |
| U-07 | `setup_logger()` | 로그 포맷 정확성 -- 파일 | `log_dir=tmp_path/"logs"` 후 `logger.info("파일 테스트")` | 로그 파일 내용이 `[YYYY-MM-DD HH:MM:SS] [INFO] 파일 테스트` 패턴과 일치 |
| U-08 | `setup_logger()` | DEBUG 레벨 설정 | `log_level="DEBUG"` | 루트 로거의 `level == logging.DEBUG` |
| U-09 | `setup_logger()` | WARNING 레벨 설정 | `log_level="WARNING"` | 루트 로거의 `level == logging.WARNING` |
| U-10 | `setup_logger()` | ERROR 레벨 설정 | `log_level="ERROR"` | 루트 로거의 `level == logging.ERROR` |
| U-11 | `setup_logger()` | 유효하지 않은 레벨 시 INFO 폴백 | `log_level="INVALID"` | 루트 로거의 `level == logging.INFO` |
| U-12 | `setup_logger()` | 중복 호출 시 핸들러 중복 방지 | `setup_logger()` 2회 연속 호출 | 루트 로거의 핸들러 수 == 2 (중복 없음) |
| U-13 | `setup_logger()` | 파일 핸들러 회전 설정 확인 | `log_dir=tmp_path/"logs"` | `TimedRotatingFileHandler.when == "midnight"`, `backupCount == 7`, `interval == 1` |
| U-14 | `setup_logger()` | 파일 핸들러 인코딩 확인 | `log_dir=tmp_path/"logs"` | `TimedRotatingFileHandler.encoding == "utf-8"` |
| U-15 | `setup_logger()` | 한글 로그 메시지 파일 기록 | `logger.info("SRT 로그인 성공")` | 파일 내용에 `SRT 로그인 성공` 포함 (UTF-8 깨짐 없음) |

## 단위 테스트: `_log_namer()` (파일명 커스텀)

| # | 대상 | 시나리오 | 입력 | 예상 결과 |
|---|------|----------|------|-----------|
| U-16 | `_log_namer()` | 회전 파일명 변환 | `"logs/srt_.log.2026-03-11"` | `"logs/srt_2026-03-11.log"` |
| U-17 | `_log_namer()` | 다른 날짜 파일명 변환 | `"logs/srt_.log.2026-01-01"` | `"logs/srt_2026-01-01.log"` |

## 통합 테스트: CLI `--log-level` 옵션

| # | API / 함수 | 시나리오 | 입력 | 예상 결과 |
|---|------------|----------|------|-----------|
| I-01 | `parse_cli_args()` | `--log-level DEBUG` 파싱 | `sys.argv = [..., "--log-level", "DEBUG"]` | `args.log_level == "DEBUG"` |
| I-02 | `parse_cli_args()` | `--log-level INFO` 파싱 | `sys.argv = [..., "--log-level", "INFO"]` | `args.log_level == "INFO"` |
| I-03 | `parse_cli_args()` | `--log-level WARNING` 파싱 | `sys.argv = [..., "--log-level", "WARNING"]` | `args.log_level == "WARNING"` |
| I-04 | `parse_cli_args()` | `--log-level ERROR` 파싱 | `sys.argv = [..., "--log-level", "ERROR"]` | `args.log_level == "ERROR"` |
| I-05 | `parse_cli_args()` | `--log-level` 미지정 시 None | 기본 인자만 | `args.log_level is None` |
| I-06 | `parse_cli_args()` | 잘못된 값 거부 | `sys.argv = [..., "--log-level", "TRACE"]` | `SystemExit` (argparse choices 검증) |
| I-07 | `Config.load_from_env()` | `LOG_LEVEL` 환경변수 로드 | `os.environ["LOG_LEVEL"] = "DEBUG"` | `env_config["log_level"] == "DEBUG"` |
| I-08 | `Config.merge()` | CLI > ENV 우선순위 | `cli={"log_level": "ERROR"}, env={"log_level": "DEBUG"}` | `merged["log_level"] == "ERROR"` |
| I-09 | `Config.merge()` | ENV > DEFAULTS 우선순위 | `cli={}, env={"log_level": "WARNING"}` | `merged["log_level"] == "WARNING"` |
| I-10 | `Config.merge()` | 미지정 시 기본값 | `cli={}, env={}` | `merged["log_level"] == "INFO"` |

## 통합 테스트: 로거 + main.py 연동

| # | 시나리오 | 입력 | 예상 결과 |
|---|----------|------|-----------|
| I-11 | main.py의 `logging.basicConfig()` 제거 확인 | `setup_logger()` 미호출 시 `import srt_reservation.main` | 루트 로거에 `basicConfig`에 의한 핸들러가 추가되지 않음 |
| I-12 | `setup_logger()` 후 SRT 인스턴스 생성 시 로그 파일 기록 | `setup_logger(log_dir=tmp_path/"logs")` 후 `SRT("동탄", "동대구", "20240115", "08")` | 로그 파일에 `봇 탐지 우회 방법:` 메시지 포함 |

## 경계 조건 / 에러 케이스

| # | 시나리오 | 예상 동작 |
|---|----------|-----------|
| E-01 | `logs/` 디렉토리에 쓰기 권한 없음 | `setup_logger()`가 `PermissionError` 발생. 콘솔 핸들러만으로 폴백하지 않고 예외를 그대로 전파 (프로세스 시작 전 실패 -- 빠른 실패 원칙). |
| E-02 | `log_level` 빈 문자열 | `setup_logger(log_level="")` -> INFO로 폴백 |
| E-03 | `log_level` 소문자 입력 | argparse `choices`가 대문자만 허용하므로 `--log-level debug` 시 `SystemExit`. `setup_logger()` 직접 호출 시 `log_level="debug"` -> `logging.getLevelName("debug")`이 숫자를 반환하지 않으므로 INFO로 폴백. |
| E-04 | 디스크 용량 부족 시 로그 파일 쓰기 | Python logging이 내부적으로 `handleError()`를 호출하여 stderr에 에러 출력. 프로세스는 계속 실행. |
| E-05 | `setup_logger()` 호출 없이 `logger.info()` 호출 | Python 기본 동작: WARNING 이상만 stderr로 출력. 파일 기록 없음. |

## E2E 시나리오

### E2E-01: 정상 실행 후 로그 파일 생성 확인

**전제**: WebDriver는 mock, 로그인/검색/예약 과정 mock 처리.

1. `quickstart.py`를 `--log-level INFO`로 실행 (subprocess).
2. 프로세스 종료 후 `logs/` 디렉토리 존재 확인.
3. `logs/srt_.log` 파일 존재 확인.
4. 파일 내용에 `[INFO]` 패턴의 로그 행이 1개 이상 존재.
5. 파일 내용에 `봇 탐지 우회 방법:` 메시지 포함.
6. 콘솔 출력(stdout/stderr)에도 동일 메시지 포함.

### E2E-02: DEBUG 레벨로 실행 시 상세 로그 확인

1. `quickstart.py`를 `--log-level DEBUG`로 실행.
2. 로그 파일에 `[DEBUG]` 패턴의 행이 1개 이상 존재.
3. `[INFO]`, `[WARNING]` 행도 함께 존재 (하위 레벨 포함).

### E2E-03: WARNING 레벨로 실행 시 필터링 확인

1. `quickstart.py`를 `--log-level WARNING`로 실행.
2. 로그 파일에 `[INFO]` 행이 없음.
3. `[WARNING]` 또는 `[ERROR]` 행만 존재 (해당 로그가 발생하는 경우).

### E2E-04: 재실행 시 기존 로그 파일 append 동작

1. `quickstart.py`를 1회 실행 -> 로그 파일 생성, 행 수 기록 (N).
2. 동일 명령으로 2회 실행.
3. 로그 파일의 행 수 > N (append 동작 확인, 덮어쓰기가 아님).

### E2E-05: `--log-level` 미지정 시 기본값 INFO 동작

1. `quickstart.py`를 `--log-level` 없이 실행.
2. 로그 파일에 `[INFO]` 행 존재.
3. `[DEBUG]` 행 없음.

## 회귀 테스트

| # | 기존 기능 | 영향 여부 | 검증 방법 |
|---|-----------|-----------|-----------|
| R-01 | F-01 SRT 로그인 | 간접 영향 -- 로그 포맷 변경 | `test_main.py`의 기존 테스트가 로그 포맷에 의존하지 않는지 확인. 기존 테스트 전부 통과 확인. |
| R-02 | F-06 CLI 인터페이스 | 직접 영향 -- `parse_cli_args()`에 인자 추가 | 기존 `test_util.py` (존재 시) 테스트 전부 통과 확인. 기존 인자 파싱이 변경 없이 동작하는지 검증. |
| R-03 | F-07 설정 관리 | 직접 영향 -- Config에 키 추가 | 기존 `test_config.py` (존재 시) 테스트 전부 통과. `Config.merge()` 기존 키에 영향 없음 검증. |
| R-04 | F-08 에러 리커버리 | 간접 영향 -- 로거 설정 변경 | `test_recovery.py` (존재 시) 테스트 전부 통과. recovery 모듈의 로깅이 새 포맷으로 출력되는지 확인. |
| R-05 | `main.py` `logging.basicConfig()` 제거 | 직접 영향 | `setup_logger()` 미호출 상태에서 `SRT()` 인스턴스 생성 시 예외 없이 동작하는지 확인 (로그가 stderr로 폴백). `test_main.py` 기존 테스트 전부 통과. |

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-10 로깅 개선 테스트 명세 |
