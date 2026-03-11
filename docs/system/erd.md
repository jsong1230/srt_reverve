# 데이터 모델 설계

## 1. 개요

Python CLI 애플리케이션이므로 영속적 DB를 사용하지 않는다. 대신 런타임 상태 모델과 설정 데이터 모델을 정의하여, 각 기능(F-07~F-12) 구현 시 데이터 구조의 일관성을 보장한다.

## 2. 런타임 상태 모델 (SRT 클래스)

```
+---------------------------------------------------------------+
|                      SRT Instance State                        |
+---------------------------------------------------------------+
| +--------------------+  +--------------------+  +------------+ |
| | Configuration      |  | WebDriver State    |  | Search     | |
| +--------------------+  +--------------------+  +------------+ |
| | dpt_stn: str       |  | driver: WebDriver  |  | is_booked  | |
| | arr_stn: str       |  |   | None            |  |   : bool   | |
| | dpt_dt: str        |  | session_id: str    |  | cnt_refresh| |
| | dpt_tm: str        |  |   | None            |  |   : int    | |
| | num_trains: int    |  | detach: bool       |  | last_error | |
| | want_reserve: bool |  +--------------------+  |   : str    | |
| | anti_bot_method:   |                          |   | None   | |
| |   str              |                          +------------+ |
| | retry_delay_min:   |                                         |
| |   int              |                                         |
| | retry_delay_max:   |                                         |
| |   int              |                                         |
| +--------------------+                                         |
|                                                                |
| 모든 상태는 SRT 클래스 인스턴스 속성으로 관리                  |
+---------------------------------------------------------------+
```

### 속성 상세

| 속성 | 타입 | 기본값 | 설명 | 관련 기능 |
|------|------|--------|------|-----------|
| `dpt_stn` | str | (필수) | 출발역명 (17개 역 중 선택) | F-02 |
| `arr_stn` | str | (필수) | 도착역명 (17개 역 중 선택) | F-02 |
| `dpt_dt` | str | (필수) | 출발날짜 (YYYYMMDD) | F-02 |
| `dpt_tm` | str | (필수) | 출발시간 (짝수 HH) | F-02 |
| `num_trains` | int | 2 | 확인할 상위 기차 개수 | F-03 |
| `want_reserve` | bool | False | 예약 대기 신청 여부 | F-04 |
| `anti_bot_method` | str | "undetected" | 봇 탐지 우회 방식 | F-05 |
| `retry_delay_min` | int | 60 | 새로고침 최소 대기(초) | F-03 |
| `retry_delay_max` | int | 120 | 새로고침 최대 대기(초) | F-03 |
| `driver` | WebDriver / None | None | Selenium WebDriver 인스턴스 | F-05 |
| `is_booked` | bool | False | 예약 완료 플래그 | F-03 |
| `cnt_refresh` | int | 0 | 새로고침 횟수 카운터 | F-03 |

## 3. 설정 데이터 모델 (F-07, M1)

`config.py`의 `Config` 클래스가 관리하는 설정 트리 구조:

```
Config
+-- SRT 로그인
|   +-- user: str              (SRT 회원 ID, 필수)
|   +-- password: str          (비밀번호, 필수)
|
+-- 예약 조건
|   +-- dpt_stn: str           (출발역, 17개 역 중 선택, 필수)
|   +-- arr_stn: str           (도착역, 17개 역 중 선택, 필수)
|   +-- dpt_dt: str            (YYYYMMDD, 필수)
|   +-- dpt_tm: str            (짝수 시간 HH, 필수)
|   +-- num_trains: int        (기본값 2)
|   +-- want_reserve: bool     (기본값 False)
|
+-- 봇 탐지 우회
|   +-- anti_bot_method: str   (undetected | stealth | enhanced, 기본값 undetected)
|   +-- retry_delay_min: int   (기본값 60)
|   +-- retry_delay_max: int   (기본값 120)
|
+-- Chrome 프로필
|   +-- use_profile: bool      (기본값 True)
|   +-- profile_dir: str | None (기본값 None)
|
+-- Telegram 알림 (F-09, M2)
|   +-- telegram_token: str | None   (기본값 None, 미설정 시 알림 비활성화)
|   +-- telegram_chat_id: str | None (기본값 None, 미설정 시 알림 비활성화)
|
+-- 로깅 (F-10, M2)
|   +-- log_level: str         (DEBUG | INFO | WARNING | ERROR, 기본값 INFO)
|
+-- 확장 (M3)
    +-- headless: bool         (기본값 False, F-12)
    +-- dpt_dt_list: list[str] (다중 날짜, F-11)
    +-- dpt_tm_list: list[str] (다중 시간, F-11)
```

### 설정 우선순위 체인

```
CLI 인자 (최우선) > 환경변수 (.env) > 기본값
```

### 환경변수 매핑

| 환경변수 | Config 속성 | CLI 인자 | 마일스톤 |
|----------|-------------|----------|----------|
| `SRT_USER` | `user` | `--user` | M1 |
| `SRT_PASSWORD` | `password` | `--psw` | M1 |
| `SRT_DPT` | `dpt_stn` | `--dpt` | M1 |
| `SRT_ARR` | `arr_stn` | `--arr` | M1 |
| `SRT_DT` | `dpt_dt` | `--dt` | M1 |
| `SRT_TM` | `dpt_tm` | `--tm` | M1 |
| `ANTI_BOT_METHOD` | `anti_bot_method` | `--anti-bot` | M1 |
| `RETRY_DELAY_MIN` | `retry_delay_min` | `--delay-min` | M1 |
| `RETRY_DELAY_MAX` | `retry_delay_max` | `--delay-max` | M1 |
| `TELEGRAM_TOKEN` | `telegram_token` | (코드 내 설정) | M2 |
| `TELEGRAM_CHAT_ID` | `telegram_chat_id` | (코드 내 설정) | M2 |
| `LOG_LEVEL` | `log_level` | `--log-level` | M2 |

## 4. 에러 복구 상태 모델 (F-08, M1)

`recovery.py`의 `RecoveryManager`가 관리하는 상태:

```
RecoveryManager
+-- srt: SRT                         (SRT 인스턴스 참조)
+-- retry_counts: dict[str, int]     (에러 유형별 재시도 횟수)
|   +-- "network": int               (기본값 0, 최대 3)
|   +-- "session": int               (기본값 0, 최대 2)
|   +-- "crash": int                 (기본값 0, 최대 1)
+-- recovery_history: list[dict]     (복구 이력)
    +-- [0]: {"type": str, "timestamp": str, "success": bool, "error": str}
    +-- ...
```

### 에러 유형별 상수

| 상수 | 값 | 설명 |
|------|-----|------|
| `MAX_NETWORK_RETRIES` | 3 | 네트워크 오류 최대 재시도 |
| `MAX_SESSION_RETRIES` | 2 | 세션 만료 최대 재로그인 |
| `MAX_CRASH_RETRIES` | 1 | 브라우저 크래시 최대 재초기화 |

### 에러 분류

| 에러 유형 | 해당 예외 | 복구 가능 | 복구 전략 |
|-----------|-----------|-----------|-----------|
| 네트워크 | `TimeoutException`, `ConnectionError` | O | 동일 작업 재시도 |
| 세션 만료 | 로그인 페이지 리다이렉트 감지 | O | 재로그인 후 검색 재개 |
| 브라우저 크래시 | `WebDriverException`, 세션 끊김 | O | WebDriver 재초기화 + 전체 재시작 |
| 입력 오류 | `InvalidStation/Date/TimeError` | X | 즉시 종료 |

## 5. 알림 데이터 모델 (F-09, M2)

Telegram 메시지 발송에 사용되는 데이터 구조:

### 예약 성공 알림 페이로드

```python
{
    "type": "success",
    "dpt_stn": str,       # 출발역
    "arr_stn": str,       # 도착역
    "dpt_dt": str,        # 출발날짜
    "dpt_tm": str,        # 출발시간
    "seat_type": str,     # "일반석" | "예약대기"
    "refresh_count": int, # 새로고침 횟수
    "elapsed_time": str   # 소요 시간 (예: "47분 23초")
}
```

### 예약 실패 알림 페이로드

```python
{
    "type": "failure",
    "error_msg": str,      # 에러 메시지
    "last_error": str,     # 마지막 예외 이름
    "retry_count": int,    # 총 재시도 횟수
    "elapsed_time": str    # 소요 시간
}
```

## 6. 데이터 흐름 (마일스톤별)

### M0 (현재): 직접 인자 전달

```
CLI 인자 (argparse) --> SRT.__init__() --> 인스턴스 속성
```

### M1: 설정 관리 + 에러 복구

```
CLI 인자 -.
           +-> Config.from_env_and_cli() -> Config 객체 -> SRT.__init__(config)
.env 파일 -'

런타임 오류 -> RecoveryManager -> 자동 복구 -> 프로세스 재개
```

### M2: 알림 + 로깅

```
SRT 상태 변화 -> Logger (듀얼: 콘솔 + 파일)
예약 결과     -> TelegramNotifier -> Telegram Bot API
```

### M3: 기능 확장

```
Config.dpt_dt_list / dpt_tm_list -> SRT.check_result() 조건 순환
Config.headless -> SRT._chrome_options() --headless=new 추가
```

## 7. 정적 데이터

### 역 목록 (validation.py)

17개 SRT 역 목록 (변경 빈도 낮음):

```python
station_list = [
    "수서", "동탄", "평택지제", "천안아산", "오송", "대전",
    "김천(구미)", "동대구", "신경주", "울산(통도사)", "부산",
    "공주", "익산", "정읍", "광주송정", "나주", "목포"
]
```

### 봇 탐지 우회 방식 (main.py)

```python
ANTI_BOT_METHODS = ["undetected", "stealth", "enhanced"]
```

## 변경 이력

| 날짜 | 변경 내용 | 이유 |
|------|-----------|------|
| 2026-03-11 | 초안 작성 | /design 스킬 산출물 -- M0 전체 설계 |
