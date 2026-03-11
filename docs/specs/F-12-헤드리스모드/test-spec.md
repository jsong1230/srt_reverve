# F-12 헤드리스 모드 -- 테스트 명세

## 참조

- 설계서: docs/specs/F-12-헤드리스모드/change-design.md
- 인수조건: docs/project/features.md #F-12

## 단위 테스트

### 1. CLI 파싱 (`tests/test_util.py` 또는 기존 테스트 파일에 추가)

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `parse_cli_args()` | --headless True 파싱 | `["--headless", "True", "--dpt", "동탄", "--arr", "동대구", "--dt", "20260315", "--tm", "08"]` | `args.headless == True` |
| `parse_cli_args()` | --headless False 파싱 | `["--headless", "False", "--dpt", "동탄", "--arr", "동대구", "--dt", "20260315", "--tm", "08"]` | `args.headless == False` |
| `parse_cli_args()` | --headless 미지정 | `["--dpt", "동탄", "--arr", "동대구", "--dt", "20260315", "--tm", "08"]` | `args.headless is None` |
| `parse_cli_args()` | --headless 대소문자 변환 | `["--headless", "true"]` | `args.headless == True` |
| `parse_cli_args()` | --headless 잘못된 값 | `["--headless", "maybe"]` | `SystemExit` (argparse 에러) |

### 2. Config 통합 (`tests/test_config.py`에 추가)

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `Config.load_from_env()` | HEADLESS=true 환경변수 | `.env`에 `HEADLESS=true` | `config['headless'] == True` |
| `Config.load_from_env()` | HEADLESS=false 환경변수 | `.env`에 `HEADLESS=false` | `config['headless'] == False` |
| `Config.load_from_env()` | HEADLESS 미설정 | `.env`에 HEADLESS 없음 | `'headless' not in config` |
| `Config.merge()` | CLI headless=True, ENV 미설정 | cli=`{"headless": True}`, env=`{}` | `merged['headless'] == True` |
| `Config.merge()` | CLI 미설정, ENV headless=true | cli=`{}`, env=`{"headless": True}` | `merged['headless'] == True` |
| `Config.merge()` | CLI headless=False, ENV headless=true | cli=`{"headless": False}`, env=`{"headless": True}` | `merged['headless'] == False` (CLI 우선) |
| `Config.merge()` | 둘 다 미설정 | cli=`{}`, env=`{}` | `merged['headless'] == False` (DEFAULTS 폴백) |
| `Config.DEFAULTS` | headless 기본값 존재 확인 | - | `Config.DEFAULTS['headless'] == False` |
| `Config._BOOL_KEYS` | headless가 불리언 키에 포함 | - | `'headless' in Config._BOOL_KEYS` |

### 3. SRT 생성자 (`tests/test_main.py`에 추가)

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `SRT.__init__()` | headless=True 생성 | `SRT("동탄", "동대구", "20260315", "08", headless=True)` | `srt.headless == True` |
| `SRT.__init__()` | headless=False 생성 (기본값) | `SRT("동탄", "동대구", "20260315", "08")` | `srt.headless == False` |
| `SRT.__init__()` | headless 미지정 (기존 호환) | `SRT("동탄", "동대구", "20260315", "08", 2, False)` | `srt.headless == False` |

### 4. Chrome 옵션 빌드 (`tests/test_main.py`에 추가)

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `_chrome_options()` | headless=True, for_undetected=False | `srt.headless = True` | options에 `"--headless=new"` 포함, `"--window-size=1920,1080"` 포함, `detach` 미설정 |
| `_chrome_options()` | headless=False, for_undetected=False | `srt.headless = False` | options에 `"--headless=new"` 미포함, `detach=True` 설정 |
| `_chrome_options()` | headless=True, for_undetected=True | `srt.headless = True` | options에 `"--headless=new"` 포함, `"--window-size=1920,1080"` 포함, `detach` 미설정 |
| `_chrome_options()` | headless=False, for_undetected=True | `srt.headless = False` | options에 `"--headless=new"` 미포함, `detach` 미설정 (undetected는 detach 미사용) |

> 테스트 방법: `_chrome_options()` 호출 후 반환된 ChromeOptions 객체의 `arguments` 속성과 `experimental_options` 속성을 검사한다. Mock 없이 실제 ChromeOptions 객체를 사용하되, `uc.ChromeOptions()`가 필요한 경우는 Mock으로 대체한다.

### 5. undetected-chromedriver headless 전달 (`tests/test_main.py`에 추가)

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `_run_driver_undetected()` | headless=True | `srt.headless = True` | `uc.Chrome()` 호출 시 `headless=True` 파라미터 전달 |
| `_run_driver_undetected()` | headless=False | `srt.headless = False` | `uc.Chrome()` 호출 시 `headless=False` 파라미터 전달 |

> 테스트 방법: `uc.Chrome`을 Mock으로 패치하고, 호출 시 `headless` 키워드 인자 값을 검증한다.

### 6. run() 메서드: 결과 출력 및 드라이버 정리 (`tests/test_main.py`에 추가)

| 대상 | 시나리오 | 입력 | 예상 결과 |
|------|----------|------|-----------|
| `run()` | headless=True, 예약 성공 | `srt.headless = True`, `is_booked = True` | `close_driver()` 호출됨, 로그에 구분선("=" * 60)과 예약 상세 정보 포함 |
| `run()` | headless=False, 예약 성공 | `srt.headless = False`, `is_booked = True` | `close_driver()` 호출되지 않음, 로그에 예약 상세 정보 포함 |
| `run()` | headless=True, 예약 실패 (예외) | `srt.headless = True`, 예외 발생 | `close_driver()` 호출됨 (finally 블록) |
| `run()` | headless=False, 예약 실패 (예외) | `srt.headless = False`, 예외 발생 | `close_driver()` 호출되지 않음 |

## 통합 테스트

### 1. Config + CLI + SRT 통합

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| CLI --headless True가 Config를 거쳐 SRT에 전달 | CLI: `--headless True` | `Config.merge()` 결과 `headless=True`, SRT 인스턴스 `self.headless == True` |
| ENV HEADLESS=true가 Config를 거쳐 SRT에 전달 (CLI 미지정) | ENV: `HEADLESS=true`, CLI: headless 미지정 | `Config.merge()` 결과 `headless=True`, SRT 인스턴스 `self.headless == True` |
| CLI --headless False가 ENV HEADLESS=true를 오버라이드 | ENV: `HEADLESS=true`, CLI: `--headless False` | `Config.merge()` 결과 `headless=False` |

### 2. anti-bot 메서드별 headless 동작

| 시나리오 | 입력 | 예상 결과 |
|----------|------|-----------|
| enhanced + headless | `anti_bot_method='enhanced'`, `headless=True` | `_run_driver_enhanced()` 호출, `_chrome_options()`에서 `--headless=new` 추가, WebDriver 정상 초기화 |
| stealth + headless | `anti_bot_method='stealth'`, `headless=True` | `_run_driver_stealth()` 호출, `_chrome_options()`에서 `--headless=new` 추가, stealth 설정 정상 적용 |
| undetected + headless | `anti_bot_method='undetected'`, `headless=True` | `_run_driver_undetected()` 호출, `uc.Chrome(headless=True)` 전달, WebDriver 정상 초기화 |

## 경계 조건 / 에러 케이스

- **headless + manual_login.py**: 수동 로그인 진입점에서 headless=True를 전달하면 사용자가 로그인할 수 없다. `manual_login.py`에서 headless 옵션을 무시하거나, 경고 후 False로 강제해야 한다. (현재 설계: `manual_login.py`에서 headless 전달하지 않음)
- **headless + detach 동시 지정**: 사용자가 명시적으로 headless=True를 지정하면 detach는 무시된다. 별도 에러나 경고를 발생시키지 않고, headless가 우선 적용된다.
- **headless 모드에서 브라우저 크래시**: `BrowserRecovery.recover()`가 드라이버를 재초기화할 때 headless 옵션이 유지되어야 한다. `RecoveryContext`에 headless 상태가 전달되는지 확인 필요. (현재 설계: BrowserRecovery가 `srt_instance`를 참조하므로 `srt_instance.headless`에서 읽을 수 있음)
- **undetected-chromedriver 미설치 + headless**: undetected 모드가 unavailable이면 enhanced 모드로 폴백하며, enhanced의 `_chrome_options()`에서 headless 옵션이 정상 적용되어야 한다.

## E2E 시나리오

### E2E-1: 헤드리스 모드에서 전체 예약 흐름 (핵심 사용자 흐름)

**전제 조건**: 유효한 SRT 계정, 예약 가능한 열차 존재

**흐름**:
1. `python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt YYYYMMDD --tm 08 --headless True` 실행
2. Chrome이 UI 없이 백그라운드에서 시작됨을 확인 (프로세스 목록에서 `--headless=new` 인자 포함 확인)
3. 로그인 성공 로그 출력: `"로그인 확인: ..."` 메시지 확인
4. 검색 실행: `"기차를 조회합니다"` 로그 확인
5. 예약 성공 시 콘솔에 구분선과 함께 상세 정보 출력:
   ```
   ============================================================
   예약 성공!
     출발역: 동탄
     도착역: 동대구
     날짜: YYYYMMDD
     시간: 08시 이후
     새로고침 횟수: N
   ============================================================
   ```
6. 프로세스 정상 종료 (exit code 0)
7. Chrome 프로세스가 남아있지 않음 확인 (close_driver 호출됨)

### E2E-2: 헤드리스 모드 + anti-bot 옵션 조합 동작 확인

**전제 조건**: 유효한 SRT 계정

**흐름 (enhanced)**:
1. `python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt YYYYMMDD --tm 08 --headless True --anti-bot enhanced` 실행
2. 로그에 `"선택한 봇 탐지 우회 방법: enhanced"` 출력 확인
3. 로그에 `"Chrome 헤드리스 모드 활성화 (--headless=new)"` 출력 확인
4. `"스텔스 스크립트 주입 완료"` 로그 확인 (CDP 명령 정상 동작)
5. 로그인 및 검색까지 정상 진행

**흐름 (stealth)**:
1. `--anti-bot stealth --headless True` 실행
2. `"selenium-stealth 적용 완료"` 로그 확인
3. 로그인 및 검색까지 정상 진행

**흐름 (undetected)**:
1. `--anti-bot undetected --headless True` 실행
2. `"undetected-chromedriver로 ChromeDriver를 초기화했습니다"` 로그 확인
3. 로그인 및 검색까지 정상 진행

### E2E-3: 헤드리스 모드에서 예약 실패 후 재검색

**전제 조건**: 유효한 SRT 계정, 모든 열차 매진 상태

**흐름**:
1. `python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt YYYYMMDD --tm 08 --headless True` 실행
2. 검색 후 매진 상태 감지: `"매진"` 로그 확인
3. 재시도 대기: `"다음 시도까지 N초 대기..."` 로그 확인
4. 새로고침 실행: `"새로고침 N회"` 로그 확인
5. 반복 루프가 정상 동작하며, 예약 가능 좌석 발견 시 예약 시도
6. Ctrl+C로 중단 시 프로세스 정상 종료, Chrome 프로세스 잔류 없음

### E2E-4: headless=False 기존 동작 유지 (재검색/재진입 시나리오)

**전제 조건**: 유효한 SRT 계정

**흐름**:
1. `python quickstart.py --user USER --psw PASS --dpt 동탄 --arr 동대구 --dt YYYYMMDD --tm 08` 실행 (--headless 미지정)
2. Chrome 브라우저 UI가 표시됨을 확인
3. 예약 성공 후 Chrome 창이 유지됨 (detach=True 동작)
4. 프로세스 종료 후에도 Chrome 창이 남아있음 확인

## 회귀 테스트

| 기존 기능 | 영향 여부 | 검증 방법 |
|-----------|-----------|-----------|
| F-01 로그인 | 영향 없음 | headless=False(기본값)에서 기존 `TestSRTLogin` 테스트 통과 확인 |
| F-03 자동 새로고침/예약 | 영향 없음 | headless=False에서 기존 `TestSRTCheckResult`, `TestSRTBookTicket` 테스트 통과 |
| F-05 봇 탐지 우회 | 간접 영향 | headless=False에서 기존 `TestSRTDriver.test_run_driver_success` 통과, `_chrome_options()` 변경으로 detach 로직 확인 |
| F-06 CLI 인터페이스 | 간접 영향 | `parse_cli_args()` 변경 후 기존 인자 파싱이 동일하게 동작하는지 확인 (--headless 미지정 시 `None` 반환) |
| F-07 설정 관리 | 간접 영향 | `Config.DEFAULTS`, `Config._BOOL_KEYS`, `Config.ENV_KEY_MAP` 추가 후 기존 `test_config.py` 테스트 전체 통과 |
| F-08 에러 리커버리 | 간접 영향 | `BrowserRecovery`가 SRT 인스턴스를 참조할 때 headless 속성이 유지되는지 확인 |

### 기존 테스트 파일 영향 분석

| 테스트 파일 | 영향 | 상세 |
|-------------|------|------|
| `tests/test_main.py` | **영향 없음** | SRT 생성자의 `headless` 파라미터 기본값이 `False`이므로 기존 테스트 코드 수정 불필요. 단, `TestSRTDriver.test_run_driver_success`가 enhanced 모드의 `_chrome_options()` 변경에 영향받을 수 있으나, Mock 기반이므로 실제 Chrome 옵션 검증은 하지 않음 |
| `tests/test_validation.py` | **영향 없음** | 역 목록 검증만 수행 |
| `tests/test_exceptions.py` | **영향 없음** | 예외 클래스만 테스트 |
| `tests/test_config.py` | **업데이트 필요** | `Config.DEFAULTS`, `_BOOL_KEYS`, `ENV_KEY_MAP`에 headless 관련 항목이 추가되므로, 기존 DEFAULTS 개수 검증 등이 있다면 업데이트 필요 |
