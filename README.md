# SRT 자동 예약 프로그램

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Selenium 4.15+](https://img.shields.io/badge/selenium-4.15+-green.svg)](https://selenium.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

매진된 SRT 기차표를 자동으로 예약하는 Python 프로그램입니다. Selenium WebDriver를 사용하여 SRT 예약 사이트를 자동화하고, 표가 나올 때까지 반복적으로 새로고침하여 예약을 시도합니다.

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/jsong1230-github/srt_reverve.git
cd srt_reverve

# 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt

# ChromeDriver 설치 (macOS)
brew install chromedriver
```

### 2. 설정

```bash
# .env 파일 생성
cp .env.example .env

# SRT 로그인 정보 입력
export SRT_USER_ID=YOUR_ID
export SRT_PASSWORD=YOUR_PASSWORD
```

### 3. 실행

```bash
# 기본 예약 (동탄 → 동대구, 2026-03-15 08:00)
python quickstart.py \
  --user YOUR_ID --psw YOUR_PASSWORD \
  --dpt 동탄 --arr 동대구 --dt 20260315 --tm 08

# 다중 조건 예약
python quickstart.py \
  --user YOUR_ID --psw YOUR_PASSWORD \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315,20260316,20260317 \
  --tm 08,10,12
```

## 📋 주요 기능

✅ **자동 로그인**: SRT 회원 ID/비밀번호 인증
✅ **스마트 검색**: 17개 역 목록, 다중 검색 조건
✅ **자동 예약**: 15~30초 주기 새로고침
✅ **봇 탐지 우회**: undetected, stealth, enhanced 3가지 방식
✅ **인간처럼 동작**: 랜덤 대기, 자연스러운 타이핑
✅ **강력한 복구**: 네트워크 오류, 세션 만료 자동 처리
✅ **알림 기능**: Telegram Bot 알림
✅ **로그 관리**: 날짜별 로그 자동 회전

## 🛠️ CLI 옵션

```
필수 옵션:
  --user TEXT           SRT 회원 ID
  --psw TEXT            SRT 비밀번호
  --dpt TEXT            출발역 (17개)
  --arr TEXT            도착역 (17개)
  --dt TEXT             출발 날짜 (YYYYMMDD 또는 쉼표 구분)
  --tm TEXT             출발 시간 (HH, 짝수만)

선택 옵션:
  --num INTEGER         확인할 기차 수 (기본: 2)
  --reserve BOOLEAN     예약 대기 신청 (기본: False)
  --anti-bot TEXT       봇 탐지 방법 (기본: undetected)
  --headless BOOLEAN    UI 숨김 (기본: False)
  --retry-delay-min INT 재시도 최소 대기 (기본: 60초)
  --retry-delay-max INT 재시도 최대 대기 (기본: 120초)
  --log-level TEXT      로그 레벨 (기본: INFO)
```

## 💡 사용 예시

### 예 1: 기본 예약
```bash
python quickstart.py \
  --user 1234567890 --psw password123 \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315 --tm 08
```

### 예 2: 다중 조건
```bash
python quickstart.py \
  --user 1234567890 --psw password123 \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315,20260316,20260317 \
  --tm 08,10,12 \
  --num 3
```

### 예 3: 헤드리스 모드
```bash
python quickstart.py \
  --user 1234567890 --psw password123 \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315 --tm 08 \
  --headless true
```

## 📊 프로젝트 현황

| 항목 | 상태 |
|------|------|
| 기능 완료도 | ✅ 100% (F-01~F-12) |
| 코드 품질 | 72/100 |
| 테스트 커버리지 | ✅ 확보 |
| 문서화 | 진행 중 |
| 메모리 누수 | 알려진 문제 |
| 봇 탐지 우회 | ✅ 3가지 방법 |

### 주요 완료 기능

- ✅ F-01: 기본 로그인/예약 자동화
- ✅ F-02: Telegram 알림
- ✅ F-03: 봇 탐지 우회 (undetected/stealth/enhanced)
- ✅ F-04~F-07: 로그 관리, 사용자 입력 검증
- ✅ F-08~F-10: 복구 패턴, 예약 대기
- ✅ F-11: 다중 검색 조건
- ✅ F-12: 헤드리스 모드

## 📖 문서

### 시작하기
- [README.md](README.md) - 빠른 시작 (이 파일)
- [docs/mac_setup.md](docs/mac_setup.md) - macOS 설정 가이드

### 심화 가이드
- [CLAUDE.md](CLAUDE.md) - 프로젝트 전체 기술 가이드
- [docs/api.md](docs/api.md) - API 상세 문서
- [docs/architecture.md](docs/architecture.md) - 아키텍처 설명

### 문제 해결 & 최적화
- [docs/troubleshooting.md](docs/troubleshooting.md) - FAQ 및 문제 해결
- [docs/performance-tuning.md](docs/performance-tuning.md) - 성능 최적화 팁
- [docs/anti_bot_guide.md](docs/anti_bot_guide.md) - 봇 탐지 우회 방법

### 실제 사용 예시
- [docs/use-cases.md](docs/use-cases.md) - 6가지 실제 사용 시나리오

## 📁 프로젝트 구조

```
srt_reverve/
├── srt_reservation/          # 메인 패키지
│   ├── main.py              # 핵심 SRT 클래스 (2000+ 줄)
│   ├── exceptions.py        # 커스텀 예외 (5가지)
│   ├── validation.py        # 역 목록 및 검증
│   └── util.py              # CLI 인자 파싱
├── tests/                   # pytest 테스트 (4개 모듈)
│   ├── test_main.py
│   ├── test_main_recovery.py
│   ├── test_validation.py
│   └── test_exceptions.py
├── docs/                    # 문서
└── quickstart.py            # CLI 진입점
```

## 🧪 테스트

```bash
pytest tests/ -v                    # 전체 테스트
pytest tests/test_main.py -v        # 특정 모듈
pytest tests/ --cov=srt_reservation # 커버리지
```

## 🚀 지원 역

```
수서, 동탄, 평택지제, 천안아산, 오송, 대전, 김천(구미), 동대구,
신경주, 울산(통도사), 부산, 공주, 익산, 정읍, 광주송정, 나주, 목포
```

## ⚠️ 주의사항

1. **SRT 회원 ID로만 로그인** (휴대폰 번호 불가)
2. **Chrome 설치 필수**: `brew install chromedriver`
3. **운영 중 창 닫지 말 것** (예약 결과 확인용)
4. **명절 승차권 예약 불가** (일반 승차권만)
5. **너무 짧은 재시도 간격 피하기** (IP 차단 위험)

## 🛠️ 기술 스택

| 항목 | 버전 |
|------|------|
| Python | 3.9+ |
| Selenium | 4.15+ |
| pytest | 8.4+ |
| undetected-chromedriver | 3.5+ |
| selenium-stealth | 1.0+ |

## 📊 성능

| 항목 | 시간 |
|------|------|
| 시작 → 로그인 | ~15초 |
| 로그인 → 검색 | ~5초 |
| 검색 주기 | 15-30초 |
| 메모리 | 150-200MB |

## ⚙️ 알려진 문제 및 제한사항

### 현재 미해결 문제

1. **메모리 누수**: 장시간 실행 시 점진적 메모리 증가
   - 원인: WebDriver 세션 재사용 미구현
   - 영향: 12시간 이상 연속 실행 시 관찰

2. **코드 구조**: main.py가 단일 파일 (2000+ 줄)
   - 개선 방안: 모듈화 (SRTConfig, SRTLogin 등)

3. **동시 검색**: 현재 순차 검색만 지원
   - 대안: 다중 조건 순차 검색 지원

### 향후 개선 계획

- [ ] 메모리 누수 제거
- [ ] main.py 모듈화 (2시간)
- [ ] 성능 최적화 (3시간)
- [ ] API 문서화 (5시간)

## 📄 라이선스

MIT License

## 🤝 기여

버그 리포트와 Pull Request를 환영합니다.

## 🐛 문제 보고

버그를 발견하면 [GitHub Issues](https://github.com/jsong1230/srt_reverve/issues)에 등록해주세요.

### 일반적인 문제 해결

**ChromeDriver 오류**
```bash
brew reinstall chromedriver
# 또는 undetected-chromedriver 사용
pip install undetected-chromedriver
python quickstart.py --anti-bot undetected ...
```

**로그인 실패**
- SRT 회원 ID(숫자)로만 로그인 가능
- 휴대폰 번호, 이메일 로그인 불가

**요소를 찾을 수 없음**
- SRT 웹사이트 구조 변경 가능성
- [CLAUDE.md](CLAUDE.md)의 CSS Selector 업데이트 확인

---

**마지막 업데이트**: 2026-03-12
**프로젝트 상태**: 모든 기능 완료, 품질 개선 진행 중
