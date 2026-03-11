# F-10 로깅 개선 -- 구현 계획서

## 1. 개요

- 기능: F-10 로깅 개선
- 의존성: F-06 완료
- 소요 시간: 3~4시간
- 변경 유형: Brownfield (신규 모듈 추가 + 기존 파일 수정)
- 참조
  - 설계서: docs/specs/F-10-로깅개선/change-design.md
  - 테스트 명세: docs/specs/F-10-로깅개선/test-spec.md
  - 인수조건: docs/project/features.md #F-10

### 인수조건 요약

- [ ] `logs/` 디렉토리에 날짜별 로그 파일 저장 (예: `srt_2026-03-11.log`)
- [ ] 로그 파일 자동 회전 (7일 보관)
- [ ] `--log-level` 옵션으로 로그 레벨 설정 (DEBUG/INFO/WARNING/ERROR)
- [ ] 콘솔 출력과 파일 출력 동시 지원 (듀얼 핸들러)

## 2. 인프라 준비

- [ ] [shared] `.gitignore`에 `logs/` 항목 추가 (로그 파일 버전 관리 제외)
  - 실행 시 `setup_logger()`가 `os.makedirs(log_dir, exist_ok=True)`로 자동 생성하므로 디렉토리 사전 생성 불필요

## 3. 구현

### Phase 1: logger.py 신규 작성

- [ ] [shared] `srt_reservation/logger.py` 신규 작성
  - 모듈 상수:
    - `LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"`
    - `LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"`
    - `DEFAULT_LOG_DIR = "logs"`
    - `LOG_FILE_PREFIX = "srt_"`
  - `_log_namer(default_name: str) -> str` 함수: 회전 파일명을 `srt_.log.YYYY-MM-DD` -> `srt_YYYY-MM-DD.log` 형태로 변환
  - `setup_logger(log_level: str = "INFO", log_dir: str = DEFAULT_LOG_DIR) -> logging.Logger` 함수:
    - `log_level` 문자열을 `logging.getLevelName()`으로 변환, 유효하지 않으면 `logging.INFO` 폴백
    - `log_dir` 없으면 `os.makedirs(log_dir, exist_ok=True)` 생성
    - 루트 로거 기존 핸들러 모두 제거 (`logger.handlers.clear()`) -- 중복 방지
    - `StreamHandler` 생성 (콘솔): 포맷터 + 레벨 설정
    - `TimedRotatingFileHandler` 생성 (파일): `filename={log_dir}/srt_.log`, `when="midnight"`, `interval=1`, `backupCount=7`, `encoding="utf-8"`, `suffix="%Y-%m-%d"`, `namer=_log_namer`
    - 루트 로거 레벨 설정 후 반환

### Phase 2: util.py + config.py 수정

- [ ] [backend] `srt_reservation/util.py` 수정
  - `parse_cli_args()` 함수에 `--log-level` 인자 추가
    - `type=str`, `default=None`, `choices=['DEBUG', 'INFO', 'WARNING', 'ERROR']`, `metavar="INFO"`
    - argparse에서 `args.log_level`로 접근 (하이픈 -> 언더스코어 자동 변환)

- [ ] [backend] `srt_reservation/config.py` 수정
  - `ENV_KEY_MAP`에 `'LOG_LEVEL': 'log_level'` 추가
  - `DEFAULTS`에 `'log_level': 'INFO'` 추가

### Phase 3: 진입점 수정

- [ ] [backend] `quickstart.py` 수정
  - `from srt_reservation.logger import setup_logger` import 추가
  - `Config.merge()` 후, `SRT` 인스턴스 생성 전에 `setup_logger(log_level=config.get('log_level', 'INFO'))` 호출

- [ ] [backend] `manual_login.py` 수정
  - `quickstart.py`와 동일하게 `setup_logger()` import 및 호출 추가

### Phase 4: main.py 수정

- [ ] [backend] `srt_reservation/main.py` 수정
  - 35행의 `logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')` 제거
  - 모듈 레벨 `logger = logging.getLogger(__name__)` 유지 (변경 없음)
  - `setup_logger()`는 진입점에서 호출하므로 main.py에서는 호출하지 않음

## 4. 테스트

- [ ] [shared] `tests/test_logger.py` 신규 작성 (20개 케이스)
  - `setup_logger()` 유닛 테스트 (U-01~U-15, 15개)
    - U-01: 핸들러 수 == 2 (StreamHandler 1 + TimedRotatingFileHandler 1)
    - U-02: StreamHandler 인스턴스 1개 존재
    - U-03: TimedRotatingFileHandler 인스턴스 1개 존재
    - U-04: log_dir 자동 생성 (nonexistent/logs)
    - U-05: `logs/srt_.log` 파일 생성 확인
    - U-06: 콘솔 포맷 정확성 (정규식: `^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[INFO\] ...`)
    - U-07: 파일 포맷 정확성
    - U-08: DEBUG 레벨 설정 확인
    - U-09: WARNING 레벨 설정 확인
    - U-10: ERROR 레벨 설정 확인
    - U-11: 유효하지 않은 레벨("INVALID") -> INFO 폴백
    - U-12: 중복 호출 시 핸들러 수 == 2 유지 (중복 방지)
    - U-13: 파일 핸들러 회전 설정 (when="midnight", backupCount=7, interval=1)
    - U-14: 파일 핸들러 인코딩 == "utf-8"
    - U-15: 한글 메시지 파일 기록 (UTF-8 깨짐 없음)
  - `_log_namer()` 유닛 테스트 (U-16~U-17, 2개)
    - U-16: `"logs/srt_.log.2026-03-11"` -> `"logs/srt_2026-03-11.log"`
    - U-17: `"logs/srt_.log.2026-01-01"` -> `"logs/srt_2026-01-01.log"`
  - 경계 조건 (E-02, E-03) -- 빈 문자열/INFO 폴백 (3개)
  - Mock 전략: 파일 시스템은 pytest `tmp_path` fixture 사용 (실제 임시 디렉토리)

- [ ] [shared] `tests/test_util.py` 기존 파일 확장 또는 신규 작성 (6개 케이스)
  - I-01~I-05: `--log-level DEBUG/INFO/WARNING/ERROR` 파싱 및 미지정 시 None
  - I-06: 잘못된 값("TRACE") 입력 시 SystemExit (argparse choices 검증)

- [ ] [shared] `tests/test_config.py` 기존 파일 확장 또는 신규 작성 (4개 케이스)
  - I-07: `LOG_LEVEL` 환경변수 로드
  - I-08: CLI > ENV 우선순위
  - I-09: ENV > DEFAULTS 우선순위
  - I-10: 미지정 시 기본값 "INFO"

- [ ] [shared] `tests/test_main_logger.py` 신규 작성 (5개 케이스)
  - I-11: `setup_logger()` 미호출 시 basicConfig에 의한 핸들러 미추가 확인
  - I-12: `setup_logger()` 후 SRT 인스턴스 생성 시 로그 파일 기록 확인
  - E2E-01: 정상 실행 후 `logs/srt_.log` 생성, `[INFO]` 행 1개 이상, `봇 탐지 우회 방법:` 포함
  - E2E-02: DEBUG 레벨 실행 시 `[DEBUG]` 행 1개 이상 존재
  - E2E-05: `--log-level` 미지정 시 기본값 INFO 동작 (`[DEBUG]` 행 없음)

## 5. 검증

- [ ] [shared] 기존 F-01~F-08 회귀 테스트 전체 통과 확인
  - R-01: `test_main.py` 기존 테스트 전부 통과 (로그 포맷 의존성 없음 확인)
  - R-02: `test_util.py` 기존 테스트 전부 통과 (기존 CLI 인자 파싱 변경 없음 확인)
  - R-03: `test_config.py` 기존 테스트 전부 통과 (Config 기존 키 영향 없음 확인)
  - R-04: `test_recovery.py` 기존 테스트 전부 통과 (recovery 모듈 로깅 정상 동작 확인)
  - R-05: `setup_logger()` 미호출 상태에서 `SRT()` 인스턴스 생성 시 예외 없이 동작 확인
  - 확인 명령: `pytest tests/ -v`

## 태스크 의존성

```
.gitignore 수정 ─────────────────────────────────────────────────┐
                                                                  ↓
Phase 1 (logger.py) ──▶ Phase 3 (진입점 수정) ──▶ Phase 4 (main.py 수정) ──▶ 테스트 작성 ──▶ 검증
                    ↑
Phase 2 (util.py + config.py) ──────────────────────────────────┘
```

Phase 1과 Phase 2는 서로 독립적이므로 병렬 작업 가능. Phase 3, 4는 Phase 1, 2 완료 후 진행.

## 병렬 실행 판단

- Agent Team 권장: No
- 근거: 이 기능은 백엔드 전용이며 프론트엔드 변경이 없다. logger.py와 util.py/config.py는 독립적으로 작성 가능하나, 진입점 수정(Phase 3)이 두 Phase를 모두 필요로 하므로 단일 Agent로 순차 처리하는 것이 더 효율적이다.
