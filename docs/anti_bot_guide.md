# SRT 봇 탐지 우회 가이드

## 🚨 문제 상황

SRT 예약 사이트에서 "봇으로 인지"되어 차단되는 경우가 발생할 수 있습니다. 이는 Selenium의 자동화 흔적을 사이트가 탐지하기 때문입니다.

## ✅ 해결 방법

세 가지 봇 탐지 우회 방법을 제공합니다.

### 방법 1: undetected-chromedriver (가장 권장 ⭐⭐⭐⭐⭐)

**가장 강력한 봇 탐지 우회 방법**입니다. ChromeDriver 바이너리를 패치하여 자동화 흔적을 제거합니다.

#### 설치
```bash
pip install undetected-chromedriver
```

#### 사용법
```bash
python quickstart.py \
  --user 1234567890 \
  --psw 000000 \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20220117 \
  --tm 08 \
  --anti-bot undetected
```

**장점:**
- Cloudflare, DataDome, Imperva 등 주요 봇 차단 시스템 우회
- ChromeDriver 자체를 패치하여 근본적으로 자동화 흔적 제거
- 가장 높은 성공률

**단점:**
- Chrome 버전 호환성 관리 필요
- 초기 실행 시 ChromeDriver 다운로드에 시간 소요

---

### 방법 2: selenium-stealth (권장 ⭐⭐⭐⭐)

JavaScript 레벨에서 자동화 흔적을 숨기는 방법입니다.

#### 설치
```bash
pip install selenium-stealth
```

#### 사용법
```bash
python quickstart.py \
  --user 1234567890 \
  --psw 000000 \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20220117 \
  --tm 08 \
  --anti-bot stealth
```

**장점:**
- 일반 ChromeDriver와 함께 사용 가능
- 설정이 간단함
- 중급 수준의 봇 탐지 우회

**단점:**
- undetected-chromedriver보다 탐지 가능성 높음
- 고급 fingerprinting 기술에는 취약

---

### 방법 3: enhanced (기본 향상 모드 ⭐⭐⭐)

향상된 옵션과 JavaScript 주입을 통한 우회 방법입니다.

#### 설치
추가 패키지 설치 불필요 (기본 제공)

#### 사용법
```bash
python quickstart.py \
  --user 1234567890 \
  --psw 000000 \
  --dpt 동탄 \
  --arr 동대구 \
  --dt 20220117 \
  --tm 08 \
  --anti-bot enhanced
```

**장점:**
- 추가 라이브러리 설치 불필요
- 기본 제공되는 방법
- 가벼움

**단점:**
- 고급 봇 탐지 시스템에는 취약
- 낮은 성공률

---

## 🔧 환경변수로 설정

CLI 인자 대신 환경변수로도 설정 가능합니다:

```bash
export ANTI_BOT_METHOD=undetected
python quickstart.py --user ... --psw ...
```

---

## 💡 추가 개선 사항

이번 업데이트에서 다음 기능들이 추가되었습니다:

### 1. 인간처럼 동작하는 기능

- **랜덤 대기**: 작업 간 0.5~2초 랜덤 대기
- **자연스러운 타이핑**: 글자 하나씩 입력 (0.05~0.15초 간격)
- **부드러운 스크롤**: smooth scroll 애니메이션 적용
- **마우스 이동 시뮬레이션**: 랜덤 마우스 이벤트 발생

### 2. 강화된 Chrome 옵션

```python
# User-Agent 설정
user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...

# 자동화 플래그 제거
--disable-blink-features=AutomationControlled
excludeSwitches: ["enable-automation", "enable-logging"]

# 권한 및 플러그인 설정
navigator.webdriver = undefined
navigator.permissions = { query: ... }
navigator.plugins = [1, 2, 3, 4, 5]
navigator.languages = ['ko-KR', 'ko', 'en-US', 'en']
```

### 3. JavaScript 스크립트 주입

- `navigator.webdriver` 숨기기
- `window.chrome` 객체 추가
- Permissions API 수정
- Plugins 수정
- Languages 설정

---

## 🎯 권장 사용 순서

1. **먼저 시도**: `undetected` 방법
2. **실패 시**: `stealth` 방법
3. **그래도 실패**: `enhanced` 방법 + VPN 사용 고려

---

## 📦 전체 설치 명령어

모든 방법을 사용할 수 있도록 패키지 설치:

```bash
# 가상환경 활성화
source .venv/bin/activate

# 의존성 업데이트
pip install --upgrade pip
pip install -r requirements.txt
```

requirements.txt에 포함된 패키지:
- `selenium>=4.15.0`
- `webdriver_manager>=4.0.0`
- `undetected-chromedriver>=3.5.0` ✨ 새로 추가
- `selenium-stealth>=1.0.6` ✨ 새로 추가
- `pytest>=7.4.0`
- `pytest-mock>=3.11.0`

---

## ⚠️ 주의사항

### 1. Chrome 버전
- undetected-chromedriver는 Chrome 버전과 호환되어야 합니다
- Chrome 자동 업데이트 비활성화 권장

### 2. 재시도 간격
- 너무 짧은 간격은 오히려 봇으로 의심받을 수 있음
- 현재 15~30초 랜덤 간격 사용 중

### 3. IP 차단
- 반복적인 실패 시 IP 차단 가능성
- VPN 사용 고려
- 다른 네트워크에서 시도

### 4. Captcha
- 고급 봇 차단 시스템은 Captcha 발생 가능
- 수동 해결 필요

---

## 🐛 문제 해결

### undetected-chromedriver 설치 오류
```bash
# pip 업그레이드
pip install --upgrade pip

# 재설치
pip uninstall undetected-chromedriver
pip install undetected-chromedriver
```

### Chrome 버전 불일치
```bash
# Chrome 버전 확인
chrome://version

# ChromeDriver 버전 확인
chromedriver --version

# 버전이 다르면 ChromeDriver 재설치
brew reinstall chromedriver
```

### 여전히 봇으로 탐지됨
1. Chrome 업데이트 확인
2. 다른 봇 탐지 우회 방법 시도
3. VPN 사용
4. 재시도 간격 늘리기 (30~60초)
5. 새로운 User-Agent 설정

---

## 📚 참고 자료

- [undetected-chromedriver GitHub](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [selenium-stealth PyPI](https://pypi.org/project/selenium-stealth/)
- [Selenium 봇 탐지 우회 가이드](https://www.zenrows.com/blog/selenium-avoid-bot-detection)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)

---

## 🔄 업데이트 이력

- **2026-02-16**: 초기 버전 작성
  - undetected-chromedriver 지원 추가
  - selenium-stealth 지원 추가
  - 인간처럼 동작하는 기능 추가
  - 강화된 Chrome 옵션 적용
