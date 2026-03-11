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

## 📖 문서

- [CLAUDE.md](CLAUDE.md) - 프로젝트 전체 가이드
- [docs/mac_setup.md](docs/mac_setup.md) - macOS 설정 가이드

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

## 📊 성능

| 항목 | 시간 |
|------|------|
| 시작 → 로그인 | ~15초 |
| 로그인 → 검색 | ~5초 |
| 검색 주기 | 15-30초 |
| 메모리 | 150-200MB |

## 📄 라이선스

MIT License

## 🤝 기여

버그 리포트와 Pull Request를 환영합니다.

---

**마지막 업데이트**: 2026-03-12
