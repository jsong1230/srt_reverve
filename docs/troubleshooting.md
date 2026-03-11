# 트러블슈팅 가이드

자주 발생하는 문제와 해결 방법을 정리했습니다.

## 로그인 문제

### Q1: "로그인 실패" 메시지가 반복됨

#### 증상
```
❌ 로그인 실패
⏳ 재시도 중...
❌ 로그인 실패
⏳ 재시도 중...
```

#### 원인 (확인 순서)
1. SRT 회원 ID 오류
2. 비밀번호 오류
3. 계정 잠금
4. 네트워크 문제
5. 봇 탐지 차단

#### 해결법

**Step 1: 계정 확인**
- SRT 웹사이트에서 직접 로그인 테스트: https://etk.srail.co.kr/

**Step 2: 비밀번호 확인**
```bash
# 특수문자가 있으면 이스케이프 필요
python quickstart.py --psw 'pass@word'
```

**Step 3: 봇 탐지 우회 방법 변경**
```bash
# undetected 방법 시도 (기본)
python quickstart.py ... --anti-bot undetected

# stealth 방법 시도
python quickstart.py ... --anti-bot stealth
```

**Step 4: 헤드리스 모드 비활성화 (시각적 확인)**
```bash
python quickstart.py ... --headless false
```

**Step 5: 로그 레벨 상향**
```bash
python quickstart.py ... --log-level DEBUG
```

---

## WebDriver 문제

### Q2: "chromedriver not found" 오류

#### 증상
```
ERROR: Could not find chromedriver
```

#### 해결법

**macOS (Homebrew 사용)**
```bash
# ChromeDriver 설치
brew install chromedriver

# 또는 재설치
brew reinstall chromedriver

# 경로 확인
which chromedriver
```

**Linux**
```bash
# apt 사용
apt install chromium-chromedriver

# 또는 수동 설치
wget https://chromedriver.chromium.org/download
unzip chromedriver_linux64.zip
mv chromedriver ~/.local/bin/
```

### Q3: "Chrome version mismatch" 오류

#### 증상
```
ERROR: Chrome version XX does not match chromedriver version YY
```

#### 해결법

**Chrome 버전 확인**
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Linux
google-chrome --version
```

**ChromeDriver 버전 확인**
```bash
chromedriver --version
```

**해결책**
- Chrome 업데이트: `brew upgrade google-chrome`
- ChromeDriver 버전 맞추기

### Q4: 브라우저 연결 끊김

#### 증상
```
ERROR: invalid session id
브라우저 창이 갑자기 종료됨
```

#### 해결법

**1단계: 시스템 리소스 확인**
```bash
# 메모리 확인
free -h           # Linux
vm_stat           # macOS
```

**2단계: Chrome 업데이트**
```bash
brew upgrade google-chrome
```

**3단계: 다시 시도**
```bash
python quickstart.py ...
```

---

## 검색 및 예약 문제

### Q5: 검색 결과가 나타나지 않음

#### 증상
```
검색 중...
(30초 이상 로딩)
```

#### 원인
1. SRT 서버 응답 지연
2. 네트워크 불안정
3. 특정 역 조합 미지원

#### 해결법

**1단계: 역 조합 확인**
```
지원하는 역: 수서, 동탄, 평택지제, 천안아산, 오송, 
대전, 김천(구미), 동대구, 신경주, 울산(통도사), 부산,
공주, 익산, 정읍, 광주송정, 나주, 목포
```

**2단계: 재시도 간격 증가**
```bash
python quickstart.py ... \
  --retry-delay-min 120 --retry-delay-max 180
```

**3단계: 네트워크 확인**
```bash
ping -c 5 etk.srail.co.kr
```

### Q6: "예약 실패" - 좌석이 없어짐

#### 증상
```
✅ 좌석 발견!
예약 시도 중...
❌ 예약 실패 (이미 예약됨)
```

#### 원인
- 다른 사용자가 먼저 예약
- 네트워크 지연

#### 해결법

**1단계: 재시도 간격 단축**
```bash
python quickstart.py ... \
  --retry-delay-min 10 --retry-delay-max 20
```

**2단계: 다중 조건 확대**
```bash
python quickstart.py ... \
  --dt 20260315,20260316,20260317 \
  --tm 08,10,12
```

**3단계: 예약 대기 신청**
```bash
python quickstart.py ... --reserve True
```

---

## 성능 문제

### Q7: 메모리 사용량이 계속 증가

#### 증상
```
초기: 150MB → 1시간 후: 250MB → 2시간 후: 350MB
```

#### 원인
- 메모리 누수
- 로그 파일 누적

#### 해결법

**1단계: 로그 파일 크기 확인**
```bash
du -sh ~/.srt_reverve/logs/
```

**2단계: 프로그램 재시작 (주기적)**
- 30분마다 프로그램 재시작
- 임시 해결책: Ctrl+C → 재실행

### Q8: CPU 사용률이 높음 (95% 이상)

#### 증상
```
Chrome/Python 프로세스가 CPU 거의 모두 사용
```

#### 해결법

**1단계: 재시도 간격 늘리기**
```bash
python quickstart.py ... \
  --retry-delay-min 60 --retry-delay-max 120
```

**2단계: 헤드리스 모드 활성화**
```bash
python quickstart.py ... --headless true
```

**3단계: 로그 레벨 낮추기**
```bash
python quickstart.py ... --log-level WARNING
```

---

## 알림 문제

### Q9: Telegram 알림이 오지 않음

#### 증상
```
예약 성공했지만 Telegram 메시지 없음
```

#### 원인
1. 토큰/채팅 ID 오류
2. 네트워크 문제

#### 해결법

**Step 1: 환경변수 확인**
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

**Step 2: 토큰/ID 검증**
- 토큰 형식: `123456:ABCdefGHIjklMNOpqrsTUVwxyz`
- 채팅 ID: `-1234567890` (음수) 또는 `1234567890` (양수)

**Step 3: 로그 확인**
```bash
tail -f ~/.srt_reverve/logs/srt_*.log | grep -i telegram
```

---

## 네트워크 문제

### Q10: 인터넷 연결 불안정

#### 증상
```
가끔씩 "Network error"
연결이 끊어졌다가 다시 복구
```

#### 원인
- Wi-Fi 신호 약함
- ISP 네트워크 문제

#### 해결법

**1단계: 유선 연결 사용**
- Wi-Fi → Ethernet 케이블로 변경

**2단계: DNS 변경**
- 1.1.1.1 (Cloudflare) 또는 8.8.8.8 (Google)로 변경

---

## 일반적인 FAQ

### Q: SRT 회원가입은 어떻게?
A: [SRT 공식 사이트](https://etk.srail.co.kr)에서 가입

### Q: 여러 계정으로 동시 예약 가능?
A: 현재는 단일 계정만 지원

### Q: 예약 성공 후 자동 결제?
A: 예약만 완료. 결제는 수동으로 진행 필요

### Q: VPN 사용 시 문제?
A: VPN이 활성화되어 있으면 비활성화 권장

---

## 디버깅 팁

### 로그 파일 위치
```
~/.srt_reverve/logs/srt_YYYYMMDD.log
```

### 고급 로깅
```python
import logging
logging.getLogger('srt').setLevel(logging.DEBUG)
```

---

**마지막 업데이트**: 2026-03-12
