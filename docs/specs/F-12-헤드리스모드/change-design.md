# F-12 헤드리스 모드 -- 변경 설계서

## 1. 참조

- 인수조건: docs/project/features.md #F-12
- 시스템 분석: docs/system/system-analysis.md
- CLI 설계: docs/system/cli-design.md
- 의존성: F-05 (봇 탐지 우회) 완료
- 마일스톤: M3

## 2. 개요

### 기능 목표

`--headless` 옵션을 추가하여 브라우저 UI 없이 백그라운드에서 예약 프로세스를 실행할 수 있도록 한다. 서버 환경, SSH 원격 실행, 리소스 절약이 필요한 상황에서 유용하다.

### 인수조건

- [ ] `--headless` 옵션으로 브라우저 UI 없이 실행
- [ ] 헤드리스 모드에서도 봇 탐지 우회 기능 정상 동작
- [ ] 예약 성공 시 결과를 콘솔 로그로 출력 (브라우저 창 확인 불가하므로)

## 3. 현황 분석

### 현재 브라우저 실행 방식

현재 SRT 클래스는 항상 브라우저 UI를 표시하며, `detach=True` 옵션으로 스크립트 종료 후에도 Chrome 창을 유지한다. 사용자는 예약 성공 후 Chrome 창에서 결과를 직접 확인한다.

**관련 코드 위치**:

| 파일 | 위치 | 내용 |
|------|------|------|
| `main.py` `_chrome_options()` | 207-208행 | `options.add_experimental_option("detach", True)` -- for_undetected가 아닐 때만 |
| `main.py` `_run_driver_undetected()` | 285-335행 | undetected-chromedriver 초기화 -- detach 미사용, headless 미지원 |
| `main.py` `_run_driver_stealth()` | 340-368행 | stealth 모드 -- `_chrome_options()` 호출 |
| `main.py` `_run_driver_enhanced()` | 371-389행 | enhanced 모드 -- `_chrome_options()` 호출 |
| `main.py` `run()` | 873-874행 | 예약 성공 시 `logger.info("예약 성공!")` + Telegram 알림만 발송, 상세 결과 미출력 |

### 문제점

1. **UI 필수**: 서버 환경이나 SSH 원격 접속 시 브라우저 UI를 표시할 수 없음
2. **리소스 낭비**: 백그라운드 작업 시에도 렌더링 리소스 소모
3. **결과 확인 한계**: headless 모드에서는 브라우저 창으로 결과를 확인할 수 없으므로, 콘솔 로그에 예약 결과 상세 정보를 출력해야 함

## 4. 변경 범위

- 변경 유형: 신규 옵션 추가 + 기존 로직 수정
- 영향 받는 모듈: `util.py`, `config.py`, `main.py`, `quickstart.py`

## 5. 아키텍처 결정

### 결정 1: Chrome 헤드리스 모드 버전

- **선택지**: A) `--headless` (레거시) / B) `--headless=new` (Chrome 112+)
- **결정**: B) `--headless=new`
- **근거**: Chrome 112+의 새 헤드리스 모드는 실제 Chrome과 동일한 엔진을 사용하여 봇 탐지 회피율이 높다. 기존 `--headless`(Chrome Headless Shell)는 fingerprint가 다르고 봇 탐지에 취약하다. 현재 프로젝트가 Chrome 131+ 기준이므로 `--headless=new` 사용이 적합하다.

### 결정 2: detach 옵션과의 관계

- **선택지**: A) headless=true일 때 detach 유지 / B) headless=true일 때 detach 무시
- **결정**: B) headless=true일 때 detach 무시
- **근거**: 헤드리스 모드에서는 브라우저 창이 없으므로 detach(스크립트 종료 후 창 유지)가 의미 없다. 오히려 프로세스가 종료되지 않는 좀비 프로세스 문제를 일으킬 수 있다. headless=true이면 `detach` 옵션을 설정하지 않고, `run()` 종료 시 `close_driver()`를 호출하여 리소스를 정리한다.

### 결정 3: undetected-chromedriver의 headless 지원

- **선택지**: A) uc.Chrome의 `headless` 파라미터 사용 / B) Chrome options에 `--headless=new` 직접 추가
- **결정**: A) uc.Chrome의 `headless` 파라미터 사용
- **근거**: undetected-chromedriver v3.5+는 `uc.Chrome(headless=True)` 파라미터를 지원하며, 내부적으로 `--headless=new`를 추가한다. 직접 options에 추가하면 undetected-chromedriver의 패치 로직과 충돌할 수 있다.

### 결정 4: SRT 클래스 생성자 변경

- **선택지**: A) `headless` 파라미터를 SRT.__init__()에 추가 / B) 엔트리포인트에서 처리
- **결정**: A) `headless` 파라미터를 SRT.__init__()에 추가
- **근거**: headless 옵션은 WebDriver 초기화(`run_driver()`)에 직접 영향을 미치므로 SRT 인스턴스가 알아야 한다. Config에서 읽어 생성자로 전달하는 기존 패턴(anti_bot_method, use_profile 등)과 동일한 방식으로 처리한다.

### 결정 5: 예약 성공 시 결과 출력 보강

- **선택지**: A) 별도 메서드 추가 / B) 기존 `run()` 메서드의 성공 로그 보강
- **결정**: B) 기존 `run()` 메서드의 성공 로그 보강
- **근거**: headless 모드 여부와 관계없이 예약 성공 시 상세 정보를 로그로 출력하는 것이 좋다. 기존 `run()` 메서드에서 `is_booked` 확인 후 예약 결과 상세 정보(출발역, 도착역, 날짜, 시간)를 INFO 레벨로 출력하도록 보강한다. headless 모드에서는 추가로 명시적인 구분선과 함께 콘솔에 출력한다.

## 6. 상세 설계

### 6.1 SRT 클래스 변경: `srt_reservation/main.py`

#### 생성자 시그니처 변경

```python
def __init__(self, dpt_stn, arr_stn, dpt_dt, dpt_tm,
             num_trains_to_check=2, want_reserve=False,
             anti_bot_method=None, retry_delay_min=60,
             retry_delay_max=120, use_profile=True,
             profile_dir=None, headless=False):
```

- `headless` 파라미터 추가 (기본값: `False`)
- `self.headless = headless` 인스턴스 변수 저장
- headless=True일 때 로그 출력: `logger.info("헤드리스 모드로 실행합니다")`

#### `_chrome_options()` 메서드 변경

```python
def _chrome_options(self, for_undetected=False):
    # ... 기존 로직 ...

    # headless 모드 처리
    if self.headless:
        options.add_argument("--headless=new")
        # headless에서는 detach 불필요
        # --start-maximized 대신 윈도우 크기 지정 (headless에서는 최대화가 동작하지 않음)
        options.add_argument("--window-size=1920,1080")
        logger.info("Chrome 헤드리스 모드 활성화 (--headless=new)")
    else:
        # 기존: detach 모드 (for_undetected가 아닐 때만)
        if not for_undetected:
            options.add_experimental_option("detach", True)

    # ... 나머지 기존 로직 ...
```

변경 포인트:
1. `headless=True`일 때 `--headless=new` 옵션 추가
2. `headless=True`일 때 `detach` 옵션 설정하지 않음 (기존 조건에 `and not self.headless` 추가)
3. `headless=True`일 때 `--window-size=1920,1080` 추가 (headless 모드에서 `--start-maximized`가 동작하지 않으므로)

#### `_run_driver_undetected()` 메서드 변경

```python
def _run_driver_undetected(self):
    # ... 기존 로직 ...

    self.driver = uc.Chrome(
        options=options,
        version_main=chrome_version,
        driver_executable_path=None,
        use_subprocess=False,
        headless=self.headless,  # headless 파라미터 전달
    )
```

변경 포인트:
1. `uc.Chrome()` 호출 시 `headless=self.headless` 파라미터 추가
2. undetected-chromedriver가 내부적으로 `--headless=new` 처리

> 주의: undetected-chromedriver의 headless 파라미터는 `bool` 타입이다. `True`이면 `--headless=new`를 자동으로 추가한다. options에 별도로 `--headless=new`를 추가하면 중복되므로, `_run_driver_undetected()`에서는 `_chrome_options()`를 호출하지 않고 직접 options를 구성하는 기존 패턴을 유지한다. 대신 headless일 때 `--window-size=1920,1080`만 추가한다.

#### `run()` 메서드 변경: 예약 성공 결과 출력 보강

```python
def run(self, login_id, login_psw):
    try:
        # ... 기존 로직 ...

        if self.is_booked:
            # 예약 결과 상세 출력 (headless 모드에서는 콘솔이 유일한 확인 수단)
            logger.info("=" * 60)
            logger.info("예약 성공!")
            logger.info(f"  출발역: {self.dpt_stn}")
            logger.info(f"  도착역: {self.arr_stn}")
            logger.info(f"  날짜: {self.dpt_dt}")
            logger.info(f"  시간: {self.dpt_tm}시 이후")
            logger.info(f"  새로고침 횟수: {self.cnt_refresh}")
            logger.info("=" * 60)

            self.notifier.notify_success({...})  # 기존 Telegram 알림
    # ... 기존 에러 처리 ...
    finally:
        if self.headless:
            # headless 모드에서는 프로세스 종료 시 드라이버 정리
            self.close_driver()
```

변경 포인트:
1. 예약 성공 시 상세 정보를 구분선과 함께 INFO 레벨로 출력
2. `finally` 블록에서 headless=True이면 `close_driver()` 호출

### 6.2 CLI 인자 추가: `srt_reservation/util.py`

```python
parser.add_argument(
    "--headless",
    help="헤드리스 모드 (브라우저 UI 없이 실행)",
    type=str_to_bool,
    metavar="True/False",
    default=None,
)
```

`parse_cli_args()`에 `--headless` 인자 추가. `default=None`으로 설정하여 Config 폴백 체인과 호환.

### 6.3 환경변수 매핑: `srt_reservation/config.py`

#### ENV_KEY_MAP 추가

```python
ENV_KEY_MAP = {
    # ... 기존 매핑 ...
    'HEADLESS': 'headless',
}
```

#### DEFAULTS 추가

```python
DEFAULTS = {
    # ... 기존 기본값 ...
    'headless': False,
}
```

#### _BOOL_KEYS 추가

```python
_BOOL_KEYS = {'reserve', 'use_profile', 'headless'}
```

### 6.4 엔트리포인트 수정: `quickstart.py`

```python
srt = SRT(
    config['dpt'],
    config['arr'],
    config['dt'],
    config['tm'],
    config['num'],
    config['reserve'],
    config['anti_bot'],
    config['delay_min'],
    config['delay_max'],
    config['use_profile'],
    config['profile_dir'],
    config.get('headless', False),  # headless 파라미터 추가
)
```

## 7. 시퀀스 흐름

### 헤드리스 모드 실행 흐름

```
사용자 --> quickstart.py --headless True
              |
              +--> parse_cli_args()              # --headless True 파싱
              +--> Config.load_from_env()         # HEADLESS 환경변수 확인
              +--> Config.merge()                 # headless=True 병합
              |
              +--> SRT(..., headless=True)
              |        |
              |        +--> self.headless = True
              |        +--> logger.info("헤드리스 모드로 실행합니다")
              |
              +--> srt.run()
                     |
                     +--> run_driver()
                     |        |
                     |        +--> [undetected] uc.Chrome(headless=True)
                     |        +--> [stealth]    _chrome_options() + "--headless=new"
                     |        +--> [enhanced]   _chrome_options() + "--headless=new"
                     |        (detach 옵션 설정 안 함)
                     |
                     +--> login() -> go_search() -> check_result()
                     |
                     +--> [예약 성공]
                     |        +--> 콘솔 로그 상세 출력 (구분선 + 역/날짜/시간)
                     |        +--> Telegram 알림
                     |
                     +--> [finally]
                              +--> close_driver()  (headless=True이므로 드라이버 정리)
```

### headless=False (기존 동작) 흐름

```
사용자 --> quickstart.py (--headless 미지정)
              |
              +--> SRT(..., headless=False)
              |
              +--> run_driver()
              |        +--> detach=True 설정 (기존과 동일)
              |
              +--> [예약 성공]
              |        +--> 콘솔 로그 상세 출력 (보강됨)
              |        +--> Chrome 창 유지 (detach)
              |
              +--> [finally]
                       +--> pass (headless=False이므로 드라이버 유지, 기존 동작)
```

## 8. 영향 분석

### 기존 API 변경

| 대상 | 현재 | 변경 후 | 하위 호환성 |
|------|------|---------|-------------|
| `SRT.__init__()` | 11개 파라미터 | 12개 파라미터 (`headless` 추가) | **호환**: `headless=False` 기본값으로 기존 호출 영향 없음 |
| `_chrome_options()` | detach 항상 설정 (for_undetected 제외) | headless=True일 때 detach 미설정 | **호환**: headless=False일 때 기존 동작 동일 |
| `_run_driver_undetected()` | `uc.Chrome(headless 미지정)` | `uc.Chrome(headless=self.headless)` | **호환**: headless=False가 기본값 |
| `run()` finally 블록 | pass (드라이버 유지) | headless=True일 때 close_driver() | **호환**: headless=False일 때 기존 동작 동일 |
| `parse_cli_args()` | headless 인자 없음 | `--headless` 인자 추가 | **호환**: 기존 CLI 호출에 영향 없음 |
| `Config.ENV_KEY_MAP` | headless 미포함 | `HEADLESS` 매핑 추가 | **호환**: 기존 .env에 영향 없음 |
| `Config.DEFAULTS` | headless 미포함 | `headless: False` 추가 | **호환**: 기본값 False |

### 사이드 이펙트

1. **`--start-maximized` 옵션**: headless 모드에서는 `--start-maximized`가 동작하지 않으므로 `--window-size=1920,1080`으로 대체해야 한다. 이미 `_chrome_options()`에서 `--start-maximized`를 추가하고 있으므로, headless일 때 이 옵션을 건너뛰고 `--window-size`를 추가하는 조건 분기가 필요하다.

2. **`_inject_stealth_scripts()`**: CDP 명령(`Page.addScriptToEvaluateOnNewDocument`)은 headless 모드에서도 정상 동작한다. headless=new 모드는 실제 Chrome 엔진을 사용하므로 CDP 호환성 문제 없음.

3. **`_human_like_delay()`, `_smooth_scroll()` 등**: headless 모드에서도 동일하게 동작한다. 스크롤, 마우스 이동 등은 DOM 이벤트 기반이므로 UI 유무와 무관하다.

4. **`check_login()` 메서드**: 환영 메시지, URL 변경, 로그인 폼 사라짐 확인 -- 모두 DOM 기반이므로 headless에서도 정상 동작.

5. **`manual_login.py`**: 수동 로그인 진입점에서는 headless를 사용할 수 없다 (사용자가 UI를 통해 직접 로그인해야 하므로). 이 진입점에서는 headless 옵션을 무시하거나, headless=True 지정 시 경고 로그를 출력하고 headless=False로 강제 전환한다.

6. **기존 테스트 (`test_main.py`)**: SRT 클래스 생성자에 `headless` 파라미터가 추가되지만 기본값이 `False`이므로 기존 테스트에 영향 없음. `TestSRTDriver.test_run_driver_success`는 enhanced 모드를 테스트하며, headless=False(기본값)에서 기존과 동일하게 동작.

## 9. 영향 범위

### 수정 필요 파일

| 파일 | 변경 내용 | 위험도 |
|------|-----------|--------|
| `srt_reservation/main.py` | `__init__`에 headless 파라미터 추가, `_chrome_options()` headless 분기, `_run_driver_undetected()` headless 전달, `run()` 결과 출력 보강 + finally close_driver | 중간 |
| `srt_reservation/util.py` | `--headless` 인자 추가 | 낮음 |
| `srt_reservation/config.py` | ENV_KEY_MAP, DEFAULTS, _BOOL_KEYS에 headless 추가 | 낮음 |
| `quickstart.py` | SRT 생성자에 headless 전달 | 낮음 |

### 신규 생성 파일

없음.

### 변경 없는 파일

| 파일 | 이유 |
|------|------|
| `srt_reservation/exceptions.py` | 변경 불필요 |
| `srt_reservation/validation.py` | 변경 불필요 |
| `srt_reservation/notifier.py` | 변경 불필요 |
| `srt_reservation/recovery.py` | 변경 불필요 |
| `srt_reservation/logger.py` | 변경 불필요 |
| `manual_login.py` | headless 옵션 전달하지 않음 (수동 로그인은 UI 필수) |

## 10. 공유 유틸리티 반환값 계약

### `SRT.__init__()` -- headless 파라미터

- 타입: `bool`
- 기본값: `False`
- `True`: 브라우저 UI 없이 백그라운드 실행, detach 비활성화, 프로세스 종료 시 드라이버 자동 정리
- `False`: 기존 동작 (브라우저 UI 표시, detach=True로 창 유지)

### `_chrome_options()` -- headless 모드 옵션 동작

- `self.headless == True` and `for_undetected == False`:
  - `--headless=new` 추가
  - `--window-size=1920,1080` 추가
  - `--start-maximized` 대신 window-size 사용
  - `detach` 옵션 설정하지 않음
- `self.headless == True` and `for_undetected == True`:
  - 이 메서드가 호출되지 않음 (`_run_driver_undetected()`가 직접 options 구성)
  - `uc.Chrome(headless=True)` 파라미터로 처리
- `self.headless == False`: 기존 동작 그대로

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-12 헤드리스 모드 변경 설계 |
