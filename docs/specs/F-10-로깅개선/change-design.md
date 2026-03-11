# F-10 로깅 개선 -- 변경 설계서

## 1. 참조

- 인수조건: docs/project/features.md #F-10
- 시스템 분석: docs/system/cli-design.md (로그 포맷, 로그 레벨 섹션)
- CLI 출력 스타일: docs/system/design-system.md (로그 포맷 표준, 파일 로그 섹션)

## 2. 개요

### 기능 목표

기존 콘솔 전용 로깅을 **파일 저장 (날짜별 회전) + `--log-level` CLI 옵션**으로 확장한다.

### 인수조건 (features.md #F-10)

| # | 인수조건 | 현재 상태 |
|---|----------|-----------|
| AC-1 | `logs/` 디렉토리에 날짜별 로그 파일 저장 (예: `srt_2026-03-11.log`) | 미구현 |
| AC-2 | 로그 파일 자동 회전 (7일 보관) | 미구현 |
| AC-3 | `--log-level` 옵션으로 로그 레벨 설정 (DEBUG/INFO/WARNING/ERROR) | 미구현 |
| AC-4 | 콘솔 출력과 파일 출력 동시 지원 (듀얼 핸들러) | 미구현 |

### 의존성

- F-06 (CLI 인터페이스): 완료 -- `util.py`의 `parse_cli_args()` 확장 필요
- F-07 (설정 관리): 완료 -- `Config` 클래스의 ENV_KEY_MAP에 `LOG_LEVEL` 추가 필요

## 3. 현황 분석

### 기존 로깅 구현

`srt_reservation/main.py` 35-36행:

```python
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
```

**문제점:**
1. `logging.basicConfig()`은 모듈 로드 시점에 루트 로거를 설정한다. 한 번 호출되면 이후 재설정이 어렵다.
2. 콘솔(`StreamHandler`)만 사용하며 파일 출력(`FileHandler`)이 없다.
3. 로그 레벨이 `INFO`로 하드코딩되어 있다.
4. 로그 포맷이 design-system.md 표준(`[{YYYY-MM-DD HH:MM:SS}] [{LEVEL}] {message}`)과 다르다.

### 기존 로그 포맷 vs 표준 포맷

| 항목 | 현재 | 표준 (F-10 이후) |
|------|------|------------------|
| 포맷 | `%(asctime)s - %(levelname)s - %(message)s` | `[%(asctime)s] [%(levelname)s] %(message)s` |
| 날짜 형식 | `2026-03-11 14:30:46,123` (밀리초 포함) | `2026-03-11 14:30:46` (초 단위) |
| 출력 대상 | 콘솔만 | 콘솔 + 파일 |
| 레벨 제어 | 하드코딩 INFO | CLI `--log-level` 옵션 |

## 4. 변경 범위

- **변경 유형**: 신규 모듈 추가 + 기존 파일 수정
- **영향 받는 모듈**: `srt_reservation` 패키지, CLI 진입점 2개

### 4.1 영향 분석

#### 기존 파일 변경

| 파일 | 변경 내용 | 하위 호환성 |
|------|-----------|-------------|
| `srt_reservation/main.py` | `logging.basicConfig()` 제거, `setup_logger()` 호출로 대체 | 호환 -- 로그 출력 내용 동일, 포맷만 변경 |
| `srt_reservation/util.py` | `--log-level` 인자 추가 | 호환 -- 기존 인자에 영향 없음 |
| `srt_reservation/config.py` | `LOG_LEVEL` 환경변수 매핑 추가, DEFAULTS에 `log_level` 추가 | 호환 -- 기존 키에 영향 없음 |
| `quickstart.py` | `setup_logger()` 호출 추가 | 호환 |
| `manual_login.py` | `setup_logger()` 호출 추가 | 호환 |

#### 사이드 이펙트

- **F-08 에러 리커버리**: `srt_reservation/recovery.py`에서 `logging.getLogger(__name__)`으로 로거를 가져오는 경우, 루트 로거 설정이 변경되므로 자동으로 새 포맷/핸들러가 적용된다. 추가 수정 불필요.
- **F-09 Telegram 알림**: `srt_reservation/notifier.py`가 존재한다면 동일하게 자동 적용. 추가 수정 불필요.
- **srt_playwright.py**: 독립 스크립트로 `srt_reservation` 패키지를 사용하지 않으므로 영향 없음.

## 5. 아키텍처 결정

### 결정 1: 로거 초기화 위치

- **선택지**: A) 모듈 레벨 `logging.basicConfig()` 유지 + 핸들러 추가 / B) 전용 `setup_logger()` 함수로 일원화
- **결정**: B) `setup_logger()` 함수
- **근거**: `basicConfig()`은 루트 로거에 중복 핸들러가 추가되는 문제가 있다. 전용 함수에서 핸들러를 명시적으로 관리하면 테스트도 용이하다.

### 결정 2: 파일 핸들러 종류

- **선택지**: A) `RotatingFileHandler` (크기 기반) / B) `TimedRotatingFileHandler` (시간 기반)
- **결정**: B) `TimedRotatingFileHandler`
- **근거**: 인수조건 AC-1이 "날짜별 로그 파일"을 요구한다. `TimedRotatingFileHandler`의 `when='midnight'`가 정확히 일치한다.

### 결정 3: 로그 디렉토리 관리

- **선택지**: A) 프로젝트 루트 기준 `logs/` / B) 사용자 홈 디렉토리 하위
- **결정**: A) 프로젝트 루트 기준 `logs/`
- **근거**: CLI 도구이므로 실행 디렉토리 기준이 직관적이다. `logs/`는 `.gitignore`에 추가한다.

### 결정 4: 콘솔과 파일의 로그 레벨 독립성

- **선택지**: A) 콘솔/파일 동일 레벨 / B) 콘솔/파일 별도 레벨
- **결정**: A) 동일 레벨
- **근거**: design-system.md 6절 "로그 레벨 기본 출력" 표에서 콘솔과 파일을 동일 레벨로 정의한다. 별도 제어가 필요하면 이후 확장한다.

## 6. 상세 설계

### 6.1 신규 모듈: `srt_reservation/logger.py`

```python
"""로깅 설정 모듈 -- 콘솔 + 파일 듀얼 핸들러"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler

# 표준 로그 포맷 (design-system.md 2절)
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 기본 로그 디렉토리
DEFAULT_LOG_DIR = "logs"

# 로그 파일 접두어
LOG_FILE_PREFIX = "srt_"


def setup_logger(
    log_level: str = "INFO",
    log_dir: str = DEFAULT_LOG_DIR,
) -> logging.Logger:
    """루트 로거에 콘솔 + 파일 핸들러를 설정한다.

    Args:
        log_level: 로그 레벨 문자열 ("DEBUG", "INFO", "WARNING", "ERROR").
                   유효하지 않은 값이면 INFO로 폴백.
        log_dir: 로그 파일 저장 디렉토리. 존재하지 않으면 자동 생성.

    Returns:
        설정된 루트 로거.

    동작:
        - 기존 핸들러를 모두 제거한 후 새로 설정 (중복 방지).
        - 콘솔 핸들러: StreamHandler → stdout.
        - 파일 핸들러: TimedRotatingFileHandler → logs/srt_YYYY-MM-DD.log.
        - 회전: 자정(midnight) 기준, 7일 보관 (backupCount=7).
        - 파일명 suffix: %Y-%m-%d (회전 시 srt_.log.2026-03-11 형태).
    """
```

**반환값 계약**: `setup_logger()` -> `logging.Logger` (루트 로거). 이후 모든 모듈에서 `logging.getLogger(__name__)`으로 자식 로거를 가져오면 루트 로거의 핸들러가 자동 전파된다.

**핵심 구현 로직**:

1. `log_level` 문자열을 `logging.getLevelName()`으로 변환. 유효하지 않으면 `logging.INFO`로 폴백.
2. `log_dir` 디렉토리가 없으면 `os.makedirs(log_dir, exist_ok=True)`로 생성.
3. 루트 로거의 기존 핸들러를 모두 제거 (`logger.handlers.clear()`).
4. `StreamHandler` 생성: 포맷터 적용, 레벨 설정.
5. `TimedRotatingFileHandler` 생성:
   - `filename`: `{log_dir}/srt_.log` (suffix로 날짜가 붙는 구조)
   - `when`: `"midnight"`
   - `interval`: `1`
   - `backupCount`: `7`
   - `encoding`: `"utf-8"`
   - `suffix`: `"%Y-%m-%d"` (회전 시 `srt_.log.2026-03-11` 생성)
   - 현재 로그 파일: `srt_.log` (항상 최신)
6. 루트 로거 레벨 설정.

**파일명 패턴 참고**: `TimedRotatingFileHandler`는 기본 파일(`srt_.log`)에 쓰고, 회전 시 `srt_.log.YYYY-MM-DD`로 이름을 변경한다. 인수조건의 `srt_2026-03-11.log` 패턴과 다소 차이가 있으나, 내용은 동일하다. 인수조건의 패턴에 정확히 맞추려면 `namer` 콜백을 커스텀해야 한다:

```python
def _log_namer(default_name: str) -> str:
    """회전된 로그 파일명을 srt_YYYY-MM-DD.log 형태로 변환한다.

    TimedRotatingFileHandler 기본 동작: srt_.log.2026-03-11
    커스텀 후: srt_2026-03-11.log
    """
```

### 6.2 기존 파일 수정: `srt_reservation/util.py`

`parse_cli_args()` 함수에 `--log-level` 인자 추가:

```python
parser.add_argument(
    "--log-level",
    help="Log level (DEBUG/INFO/WARNING/ERROR)",
    type=str,
    metavar="INFO",
    default=None,
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
)
```

- `default=None`: Config 폴백 체인이 동작하도록 None 유지.
- `choices`: 유효한 레벨만 허용. 잘못된 값 입력 시 argparse가 자동 에러 출력.
- argparse에서 `--log-level`은 `args.log_level`로 접근 (하이픈 → 언더스코어 자동 변환).

### 6.3 기존 파일 수정: `srt_reservation/config.py`

**ENV_KEY_MAP 추가**:

```python
'LOG_LEVEL': 'log_level',
```

**DEFAULTS 추가**:

```python
'log_level': 'INFO',
```

### 6.4 기존 파일 수정: `srt_reservation/main.py`

**제거**: 35행의 `logging.basicConfig(...)` 호출.

**변경**: 모듈 레벨 로거는 `logger = logging.getLogger(__name__)` 유지. `setup_logger()`는 진입점(`quickstart.py`, `manual_login.py`)에서 호출하므로 main.py에서는 호출하지 않는다.

**이유**: `setup_logger()`는 프로세스당 1회만 호출해야 한다. main.py는 라이브러리 모듈이므로 진입점에서 호출하는 것이 적절하다.

### 6.5 기존 파일 수정: `quickstart.py`

Config merge 후, SRT 인스턴스 생성 전에 `setup_logger()` 호출:

```python
from srt_reservation.logger import setup_logger

# Config merge 후
setup_logger(log_level=config.get('log_level', 'INFO'))
```

### 6.6 기존 파일 수정: `manual_login.py`

quickstart.py와 동일하게 `setup_logger()` 호출 추가.

### 6.7 `.gitignore` 추가

```
logs/
```

## 7. 시퀀스 흐름

### 정상 실행 흐름

```
사용자 → quickstart.py (CLI 인자 파싱)
       → Config.merge() (log_level 결정)
       → setup_logger(log_level)
           → logs/ 디렉토리 생성 (없으면)
           → 루트 로거 핸들러 초기화
           → StreamHandler(콘솔) 추가
           → TimedRotatingFileHandler(파일) 추가
       → SRT.__init__()
           → logger.info("봇 탐지 우회 방법: ...")  ← 콘솔 + 파일 동시 출력
       → srt.run()
           → (모든 로그가 콘솔 + 파일로 출력)
```

### 로그 회전 흐름

```
자정(00:00) → TimedRotatingFileHandler.doRollover()
            → 현재 srt_.log → srt_2026-03-11.log (namer 커스텀)
            → 새 srt_.log 생성
            → 7일 이전 파일 자동 삭제
```

## 8. 영향 범위 요약

### 수정 필요 파일

| 파일 | 변경 내용 |
|------|-----------|
| `srt_reservation/util.py` | `--log-level` 인자 추가 (2행) |
| `srt_reservation/config.py` | `LOG_LEVEL` 환경변수 매핑 + 기본값 추가 (2행) |
| `srt_reservation/main.py` | `logging.basicConfig()` 제거 (1행) |
| `quickstart.py` | `setup_logger()` import + 호출 (2행) |
| `manual_login.py` | `setup_logger()` import + 호출 (2행) |
| `.gitignore` | `logs/` 추가 (1행) |

### 신규 생성 파일

| 파일 | 설명 |
|------|------|
| `srt_reservation/logger.py` | 로깅 설정 모듈 (`setup_logger()` 함수) |

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-10 로깅 개선 기능 설계 |
