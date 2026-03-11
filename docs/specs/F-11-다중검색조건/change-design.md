# F-11: 다중 검색 조건 -- 변경 설계서

## 1. 참조

- 인수조건: docs/project/features.md #F-11
- 시스템 분석: docs/system/system-analysis.md
- CLI 설계: docs/system/cli-design.md

## 2. 변경 범위

- 변경 유형: 수정 (기존 단일 조건 -> 다중 조건)
- 영향 받는 모듈: `util.py`, `config.py`, `main.py`
- 영향 없는 모듈: `quickstart.py` (Config가 값을 넘겨주므로 변경 불필요), `manual_login.py`, `exceptions.py`, `validation.py`, `recovery.py`, `notifier.py`, `logger.py`

## 3. 아키텍처 결정

### 결정 1: CLI 인자 파싱 전략

- **선택지**:
  - A) `--dt`와 `--tm` 인자를 `nargs='+'`로 변경하여 공백 구분 다중값 수용 (`--dt 20260315 20260316`)
  - B) 기존 `type=str` 유지, 쉼표 구분 문자열을 파싱 함수에서 분리 (`--dt 20260315,20260316`)
- **결정**: B) 쉼표 구분 문자열
- **근거**:
  - 기존 단일값 입력과 완전 하위 호환 (쉼표 없으면 길이 1 리스트)
  - .env 환경변수에서도 쉼표 구분이 자연스러움 (`SRT_DT=20260315,20260316`)
  - argparse 인자 정의 변경이 최소화됨 (type, metavar만 수정)

### 결정 2: 다중 조건 검색 루프 구조

- **선택지**:
  - A) go_search()를 각 조건마다 호출 (검색 페이지 이동 포함)
  - B) go_search()를 최초 1회 호출 후, 조건 변경 시 날짜/시간만 변경하여 재조회
- **결정**: A) 각 조건마다 go_search() 호출
- **근거**:
  - SRT 검색 페이지는 Select 요소로 날짜/시간을 선택하므로, 페이지 재이동 없이 값만 변경하면 이전 검색 결과가 잔류할 위험이 있음
  - go_search()가 내부적으로 전체 페이지 로드 -> 입력 -> 조회를 수행하므로 상태가 깨끗하게 초기화됨
  - 성능 차이가 미미함 (조건별로 15~30초 대기하므로 페이지 로드 1~2초는 무시 가능)

### 결정 3: 조건 순회 단위

- **선택지**:
  - A) 날짜/시간 조합의 카테시안 곱 (dates x times)을 조건 배열로 만들어 순차 순회
  - B) 날짜 우선 순회 (날짜별로 모든 시간 확인 -> 다음 날짜)
- **결정**: A) 카테시안 곱 순차 순회
- **근거**:
  - 인수조건 "조건을 순차적으로 검색하여 가장 먼저 예약 가능한 좌석 예약"에 부합
  - 사용자가 `--dt 20260315,20260316 --tm 08,10`이면 `(0315,08) -> (0315,10) -> (0316,08) -> (0316,10)` 순서로 검색
  - 날짜 우선으로 정렬하면 동일 날짜의 모든 시간대를 먼저 확인할 수 있어 직관적

### 결정 4: SRT 클래스 인터페이스 변경 방식

- **선택지**:
  - A) `__init__`에서 `dpt_dt`와 `dpt_tm`을 리스트로 받도록 시그니처 변경
  - B) `__init__`은 단일값 유지, 별도 메서드 `set_search_conditions(dates, times)` 추가
  - C) `__init__`에서 `dpt_dt`와 `dpt_tm`을 리스트로 받되, 단일 문자열도 리스트 변환 처리
- **결정**: C) 리스트 수용 + 단일값 자동 변환
- **근거**:
  - 기존 코드와의 하위 호환성 유지 (`SRT("동탄", "동대구", "20260315", "08")` 그대로 동작)
  - `quickstart.py`에서 Config가 리스트를 넘겨주면 리스트로, 단일값을 넘겨주면 자동 변환
  - 인터페이스가 단순하고 호출부 변경 최소화

## 4. 영향 분석

### 기존 API 변경

#### util.py -- parse_cli_args()

| 항목 | 현재 | 변경 후 | 하위 호환성 |
|------|------|---------|-------------|
| `--dt` help 텍스트 | `"Departure Date"` | `"Departure Date(s), comma-separated"` | 호환 |
| `--dt` metavar | `"20220118"` | `"20260315,20260316"` | 호환 |
| `--tm` help 텍스트 | `"Departure Time"` | `"Departure Time(s), comma-separated"` | 호환 |
| `--tm` metavar | `"08, 10, 12, ..."` | `"08,10,12"` | 호환 |

> argparse의 `type=str`은 유지. 파싱은 Config 또는 SRT 클래스에서 수행.

#### config.py -- Config 클래스

| 항목 | 현재 | 변경 후 | 하위 호환성 |
|------|------|---------|-------------|
| `load_from_cli()` | `dt`, `tm`을 `str`로 반환 | 변경 없음 (argparse가 str 반환) | 호환 |
| `load_from_env()` | `SRT_DT`, `SRT_TM`을 `str`로 반환 | 변경 없음 (환경변수는 항상 str) | 호환 |
| `merge()` | 변경 없음 | 변경 없음 | 호환 |

> Config는 값을 그대로 전달. 쉼표 구분 파싱은 SRT 클래스 `__init__`에서 수행.

#### main.py -- SRT 클래스

| 메서드 | 현재 | 변경 후 | 하위 호환성 |
|--------|------|---------|-------------|
| `__init__` | `dpt_dt: str`, `dpt_tm: str` | `dpt_dt: str or list[str]`, `dpt_tm: str or list[str]` | 호환 (단일 str 입력 시 자동 변환) |
| `check_input` | 단일 날짜/시간 검증 | 리스트 내 각 항목 검증 | 호환 |
| `go_search` | `self.dpt_dt`, `self.dpt_tm` 사용 | 인자로 `dpt_dt`, `dpt_tm` 받도록 변경 (기본값: self 속성) | 호환 |
| `check_result` | 단일 조건 무한 루프 | 조건 배열 순회 외부 루프 추가 | 호환 |
| `run` | `go_search()` 1회 -> `check_result()` | `check_result_multi()` 호출로 대체 | 호환 |

### 사이드 이펙트

1. **기존 단일 조건 테스트**: `SRT("동탄", "동대구", "20240115", "08")` -- `dpt_dt`가 문자열이면 `["20240115"]`로 변환. `check_input()`이 리스트 순회하므로 기존 검증 로직 동작 유지.
2. **Telegram 알림**: `notifier.notify_success()`에 전달하는 정보에 "어떤 조건에서 예약 성공했는지" 추가 가능 (선택적 개선).
3. **에러 리커버리**: `check_result()` 루프 구조가 변경되므로, `recovery.py`의 `NetworkErrorRecovery.recover()`, `SessionRecovery.recover()` 호출 위치 조정 필요.
4. **로깅**: 현재 조건에 대한 로그 출력 추가 (어떤 날짜/시간을 검색 중인지).

## 5. 상세 설계

### 5.1 새로운 함수: generate_search_conditions()

SRT 클래스의 인스턴스 메서드로 추가.

```python
def generate_search_conditions(self) -> list[dict]:
    """
    날짜 x 시간의 카테시안 곱으로 검색 조건 배열 생성.

    Returns:
        list[dict]: [{"dpt_dt": "20260315", "dpt_tm": "08"}, ...]
        날짜 우선 정렬 (동일 날짜의 모든 시간 -> 다음 날짜)

    예시:
        dates = ["20260315", "20260316"]
        times = ["08", "10"]
        결과 = [
            {"dpt_dt": "20260315", "dpt_tm": "08"},
            {"dpt_dt": "20260315", "dpt_tm": "10"},
            {"dpt_dt": "20260316", "dpt_tm": "08"},
            {"dpt_dt": "20260316", "dpt_tm": "10"},
        ]
    """
```

### 5.2 __init__ 변경

```python
def __init__(self, dpt_stn, arr_stn, dpt_dt, dpt_tm, ...):
    # 쉼표 구분 문자열 또는 리스트를 list[str]로 정규화
    self.dpt_dates = self._normalize_to_list(dpt_dt)  # ["20260315", "20260316"]
    self.dpt_times = self._normalize_to_list(dpt_tm)  # ["08", "10"]

    # 하위 호환성: 첫 번째 값을 기본값으로 유지
    self.dpt_dt = self.dpt_dates[0]
    self.dpt_tm = self.dpt_times[0]

    # 검색 조건 배열 생성
    self.search_conditions = self.generate_search_conditions()

    self.check_input()
```

### 5.3 _normalize_to_list() -- 새 private 메서드

```python
@staticmethod
def _normalize_to_list(value) -> list[str]:
    """
    문자열 또는 리스트를 list[str]로 정규화.

    Args:
        value: str ("20260315" 또는 "20260315,20260316") 또는 list[str]

    Returns:
        list[str]: ["20260315"] 또는 ["20260315", "20260316"]

    반환값 계약:
        - 항상 길이 >= 1의 리스트 반환
        - 각 항목은 strip() 적용된 문자열
        - 빈 문자열 항목은 제거
    """
    if isinstance(value, list):
        return [v.strip() for v in value if v.strip()]
    return [v.strip() for v in str(value).split(',') if v.strip()]
```

### 5.4 check_input() 변경

```python
def check_input(self):
    # 역명 검증 (변경 없음)
    ...

    # 날짜 검증 -- 모든 날짜에 대해 반복
    for date_str in self.dpt_dates:
        date_str = str(date_str)
        if not date_str.isnumeric():
            raise InvalidDateFormatError("날짜는 숫자로만 이루어져야 합니다.")
        if len(date_str) != 8:
            raise InvalidDateError("날짜가 잘못 되었습니다. YYYYMMDD 형식으로 입력해주세요.")
        try:
            datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            raise InvalidDateError("날짜가 잘못 되었습니다. YYYYMMDD 형식으로 입력해주세요.")

    # 시간 검증 -- 모든 시간에 대해 반복
    for tm in self.dpt_times:
        try:
            hour = int(tm)
            if hour < 0 or hour > 23:
                raise InvalidTimeFormatError("시간은 0-23 사이의 값이어야 합니다.")
            if hour % 2 != 0:
                raise InvalidTimeFormatError("시간은 짝수 시간만 허용됩니다. (예: 06, 08, 10, ...)")
        except ValueError:
            raise InvalidTimeFormatError("시간은 숫자 형식이어야 합니다. (예: 06, 08, 14)")
```

### 5.5 go_search() 변경

```python
def go_search(self, dpt_dt=None, dpt_tm=None):
    """
    기차 조회 페이지로 이동 및 검색 조건 입력.

    Args:
        dpt_dt: 출발 날짜 (None이면 self.dpt_dt 사용) -- 하위 호환
        dpt_tm: 출발 시간 (None이면 self.dpt_tm 사용) -- 하위 호환
    """
    search_dt = dpt_dt or self.dpt_dt
    search_tm = dpt_tm or self.dpt_tm

    # 이하 기존 로직에서 self.dpt_dt -> search_dt, self.dpt_tm -> search_tm으로 교체
    ...
```

### 5.6 check_result() 변경 -- 다중 조건 루프

```python
def check_result(self):
    """
    검색 결과 확인 및 예약 시도.
    다중 조건이면 모든 조건을 1회씩 순회 후 다시 처음부터 반복.
    """
    while True:
        for condition in self.search_conditions:
            dpt_dt = condition["dpt_dt"]
            dpt_tm = condition["dpt_tm"]

            logger.info(f"검색 조건: 날짜={dpt_dt}, 시간={dpt_tm}")

            # 해당 조건으로 검색 실행
            self.go_search(dpt_dt=dpt_dt, dpt_tm=dpt_tm)

            # 검색 결과 1회 확인
            try:
                result = NetworkErrorRecovery.recover(
                    operation=self._check_result_once,
                    context=self.recovery_context,
                )
                if result is not None:
                    # 예약 성공 -- 어떤 조건에서 성공했는지 기록
                    self._booked_condition = condition
                    return result
            except RecoveryError as e:
                logger.error(f"네트워크 오류 복구 실패: {e}")
                raise
            except Exception as e:
                if SessionRecovery.is_session_expired(self.driver):
                    logger.warning("세션 만료 감지. 재로그인 시도...")
                    try:
                        SessionRecovery.recover(
                            driver=self.driver,
                            srt_instance=self,
                            context=self.recovery_context,
                        )
                        continue  # 현재 조건 건너뛰고 다음 조건으로
                    except RecoveryError as recovery_err:
                        logger.error(f"세션 복구 실패: {recovery_err}")
                        raise
                else:
                    raise

        # 모든 조건 1회 순회 완료 -- 대기 후 다시 처음부터
        if self.is_booked:
            return self.driver

        delay = randint(self.retry_delay_min, self.retry_delay_max)
        logger.info(f"모든 조건 확인 완료. {delay}초 대기 후 다시 처음부터 검색...")
        time.sleep(delay)
        self.cnt_refresh += 1
```

### 5.7 run() 변경

```python
def run(self, login_id, login_psw):
    try:
        self.run_driver()
        self.set_log_info(login_id, login_psw)
        self.login()

        # 로그인 확인 (기존 로직 유지)
        ...

        # go_search()는 check_result() 내부에서 조건별로 호출
        # 기존: self.go_search() + self.check_result()
        # 변경: self.check_result() (내부에서 go_search 호출)
        self.check_result()

        if self.is_booked:
            condition = getattr(self, '_booked_condition', {})
            logger.info(f"예약 성공 조건: 날짜={condition.get('dpt_dt', 'N/A')}, 시간={condition.get('dpt_tm', 'N/A')}")
            self.notifier.notify_success({
                "dept_time": condition.get('dpt_tm', self.dpt_tm),
                "arri_time": "N/A",
                "seat_type": "일반석",
            })
        ...
```

### 5.8 시퀀스 흐름

```
사용자 --dt 20260315,20260316 --tm 08,10
         |
    CLI 파싱 (util.py) -- dt="20260315,20260316", tm="08,10"
         |
    Config.merge() -- dt="20260315,20260316", tm="08,10" (str 그대로)
         |
    SRT.__init__()
      _normalize_to_list("20260315,20260316") -> ["20260315", "20260316"]
      _normalize_to_list("08,10") -> ["08", "10"]
      generate_search_conditions() -> [
        {"dpt_dt": "20260315", "dpt_tm": "08"},
        {"dpt_dt": "20260315", "dpt_tm": "10"},
        {"dpt_dt": "20260316", "dpt_tm": "08"},
        {"dpt_dt": "20260316", "dpt_tm": "10"},
      ]
      check_input() -- 각 날짜/시간 개별 검증
         |
    run() -> login() -> check_result()
         |
    check_result() 루프:
      [조건 1] go_search(20260315, 08) -> _check_result_once() -> 매진
      [조건 2] go_search(20260315, 10) -> _check_result_once() -> 매진
      [조건 3] go_search(20260316, 08) -> _check_result_once() -> 예약하기 발견!
        -> book_ticket() -> 예약 성공 -> return
```

## 6. 영향 범위

### 수정 필요 파일

| 파일 | 변경 내용 | 변경 규모 |
|------|-----------|-----------|
| `srt_reservation/main.py` | `__init__`, `check_input`, `go_search`, `check_result`, `run` 수정. `_normalize_to_list`, `generate_search_conditions` 신규 메서드 | 중 |
| `srt_reservation/util.py` | `--dt`, `--tm` help/metavar 텍스트 수정 | 소 |
| `docs/system/cli-design.md` | `--dt`, `--tm` 설명에 쉼표 구분 다중값 추가 | 소 |

### 신규 생성 파일

없음 (기존 파일 수정만으로 구현 가능)

### 변경 불필요 파일

| 파일 | 이유 |
|------|------|
| `quickstart.py` | Config가 문자열을 그대로 SRT에 전달. SRT가 내부에서 파싱 |
| `manual_login.py` | 동일 이유 |
| `srt_reservation/config.py` | dt, tm을 str로 전달하는 기존 로직 유지 |
| `srt_reservation/exceptions.py` | 기존 예외 클래스 재사용 |
| `srt_reservation/validation.py` | 역 목록 변경 없음 |
| `srt_reservation/recovery.py` | 인터페이스 변경 없음. check_result 내부에서 동일하게 호출 |
| `srt_reservation/notifier.py` | 인터페이스 변경 없음 |
| `srt_reservation/logger.py` | 변경 없음 |

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-12 | 초안 작성 | F-11 다중 검색 조건 설계 |
