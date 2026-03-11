# F-07 설정 관리 -- 구현 계획서

## 1. 개요

- 기능명: F-07 설정 관리
- 의존성: F-06 완료
- 마일스톤: M1
- 소요 시간 추정: 3~4시간 (설정 로드, 폴백 체인, 통합 테스트)

## 2. 참조

- 설계서: docs/specs/F-07-설정관리/change-design.md
- 인수조건: docs/project/features.md #F-07
- 테스트 명세: docs/specs/F-07-설정관리/test-spec.md

## 3. 태스크 목록

### Phase 1: 인프라 준비

- [ ] [shared] requirements.txt에 `python-dotenv>=1.0.0` 추가

### Phase 2: 구현

- [ ] [shared] srt_reservation/config.py 신규 모듈 작성
  - ENV_KEY_MAP 상수 정의 (환경변수명 -> Config 속성명 매핑)
  - DEFAULTS dict 정의 (num=2, reserve=False, anti_bot="undetected", delay_min=60, delay_max=120)
  - Config 클래스: load_from_env, load_from_cli, merge, validate_required 정적 메서드
  - 타입 변환 실패 시 기본값 폴백 + WARNING 로그 처리

- [ ] [backend] srt_reservation/util.py 수정
  - 선택 인자 기본값 None으로 변경: --num, --reserve, --anti-bot, --delay-min, --delay-max, --use-profile
  - 기본값은 config.py DEFAULTS에서만 관리하도록 책임 이전

- [ ] [backend] quickstart.py 수정
  - `from srt_reservation.config import Config` 추가
  - 기존 수동 필수 인자 검증 (missing_args 로직) 제거
  - Config.load_from_env() -> Config.load_from_cli() -> Config.merge() -> Config.validate_required() 호출 체인 적용
  - validate_required 필수 키: ["user", "password", "dpt", "arr", "dt", "tm"]
  - 병합된 config dict에서 SRT 생성자 인자 추출

- [ ] [backend] manual_login.py 수정
  - quickstart.py와 동일한 Config 로드 패턴 적용
  - validate_required 필수 키: ["dpt", "arr", "dt", "tm"] (user, password 제외)
  - 수동 로그인 전용 하드코딩 기본값 유지 (retry_delay_min=150, retry_delay_max=300, anti_bot_method='stealth')

### Phase 3: 테스트

- [ ] [shared] tests/test_config.py 신규 작성
  - Config.load_from_env() 6개 케이스 (정상 로드, 미존재, 빈 파일, 주석만, 일부 변수, 따옴표 처리)
  - Config.load_from_cli() 4개 케이스 (전체 인자, 필수만, 모두 None, 일부 제공)
  - Config.merge() 10개 케이스 (CLI만, env만, CLI 우선, 기본값 폴백, 혼합, 타입 변환 성공/실패)
  - Config.validate_required() 5개 케이스 (전체 충족, 단일 누락, 다중 누락, 빈 문자열 허용, manual_login 모드)
  - 경계 조건: 총 25개 이상 케이스

- [ ] [shared] tests/test_integration_config.py 신규 작성
  - E2E-01: .env만으로 실행 (Config 전체 플로우)
  - E2E-02: CLI 인자가 .env 값 덮어쓰기
  - E2E-03: .env 미존재 + CLI 인자만으로 실행
  - E2E-04: 필수값 누락 시 ValueError 발생 확인
  - E2E-05: manual_login.py에서 .env 로드 (user/password 불필요)
  - 총 5개 E2E 시나리오

### Phase 4: 검증

- [ ] [shared] 기존 F-01~F-06 테스트 전체 통과 확인 (회귀 테스트)
  - `pytest tests/test_main.py -v` -- SRT 클래스 호환성
  - `pytest tests/test_validation.py -v` -- 역 목록 무결성
  - `pytest tests/test_exceptions.py -v` -- 예외 클래스 호환성

## 4. 태스크 의존성

```
Phase 1 (인프라)
  |
  v
Phase 2 (구현)
  config.py 작성
    |
    +---> util.py 수정
    |       |
    +---> quickstart.py 수정 (util.py + config.py 완료 후)
    |
    +---> manual_login.py 수정 (util.py + config.py 완료 후)
  |
  v
Phase 3 (테스트)
  |
  v
Phase 4 (검증)
```

## 5. 병렬 실행 판단

- Agent Team 권장: No
- 근거: 이 기능은 CLI(util.py), 엔트리포인트(quickstart.py, manual_login.py), 신규 모듈(config.py)이 단일 데이터 흐름(설정 폴백 체인)으로 연결되어 있어 순차 구현이 안전함. config.py 인터페이스 확정 후 util.py 수정, 그 후 엔트리포인트 수정 순서가 필수. 테스트는 구현 완료 후 단일 에이전트가 작성 가능.

## 6. 구현 주의사항

- config.py의 load_from_cli()는 argparse Namespace에서 None 값을 제외한 인자만 dict에 포함해야 함
- util.py 선택 인자 기본값을 None으로 변경하는 것이 폴백 체인의 전제 조건임
- validate_required() 에러 메시지 형식 준수: "필수 설정이 누락되었습니다: {키목록}. CLI 인자 또는 .env 파일에서 설정하세요."
- 타입 변환 실패 WARNING 로그 형식 준수: "환경변수 {KEY}의 값 '{value}'를 {type}으로 변환할 수 없습니다. 기본값 {default}를 사용합니다."
- main.py는 변경 없음 (SRT 클래스 시그니처 유지, 하위 호환성 완전 보장)

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-03-12 | 초안 작성 |
