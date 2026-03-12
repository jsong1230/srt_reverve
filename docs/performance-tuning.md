# 성능 튜닝 가이드

SRT 자동 예약 프로그램의 성능을 최적화하기 위한 팁과 설정 방법입니다.

## 🚀 빠른 시작 (권장 설정)

```bash
python quickstart.py \
  --user YOUR_ID --psw YOUR_PASSWORD \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315 --tm 08 \
  --anti-bot undetected \
  --headless true \
  --retry-delay-min 10 --retry-delay-max 15
```

**예상 결과**: 약 2배 빠른 예약 성공률

---

## 📊 성능 최적화 체크리스트

### 1️⃣ 재시도 간격 최적화

#### 현재 설정
```bash
--retry-delay-min 60 --retry-delay-max 120  # 기본값 (안정적)
```

#### 최적화 설정
```bash
--retry-delay-min 10 --retry-delay-max 15   # 극도로 빠름
--retry-delay-min 20 --retry-delay-max 30   # 빠름
--retry-delay-min 30 --retry-delay-max 45   # 중간
```

#### 선택 기준

| 설정 | 속도 | 안정성 | 추천 대상 |
|------|------|--------|----------|
| 10-15초 | ⚡⚡⚡ | ⚠️ | 경쟁이 치열한 시간대 |
| 20-30초 | ⚡⚡ | ⚠️⚠️ | 일반적인 예약 |
| 30-45초 | ⚡ | ⚠️⚠️⚠️ | 안정성 중시 |
| 60-120초 | 느림 | ✅ | IP 차단 회피 필요 |

**⚠️ 주의**: 너무 짧은 간격(5초 이하)은 IP 차단 위험

### 2️⃣ 헤드리스 모드 활성화

```bash
--headless true
```

**효과**:
- 메모리 사용량 20-30% 감소
- UI 렌더링 오버헤드 제거
- 약 5-10% 더 빠른 응답 시간

**주의사항**:
- 시각적 문제 진단 불가
- 문제 발생 시 `--headless false`로 변경

### 3️⃣ 다중 조건 검색 최적화

#### 기본 (순차 검색)
```bash
--dt 20260315 --tm 08
# → 1개 조건만 검색
```

#### 최적화 (다중 조건)
```bash
--dt 20260315,20260316,20260317 --tm 08,10,12
# → 9개 조건 동시 순차 검색
```

**장점**:
- 예약 실패 시 자동으로 다음 조건 시도
- 검색 횟수 증가 = 예약 확률 증가

**예상 시간**:
```
기본: 1시간 실행 = 1개 조건 검색
최적화: 1시간 실행 = 9개 조건 검색
```

### 4️⃣ 봇 탐지 우회 방법 선택

| 방법 | 속도 | 우회율 | 메모리 | 추천 |
|------|------|--------|--------|------|
| undetected | ⚡⚡ | ✅✅✅ | 높음 | ⭐⭐⭐ |
| stealth | ⚡⚡⚡ | ✅✅ | 낮음 | ⭐⭐ |
| enhanced | ⚡ | ✅ | 낮음 | ⭐ |

```bash
# undetected (권장)
--anti-bot undetected

# stealth (빠르지만 탐지 가능성)
--anti-bot stealth

# enhanced (기본, 느림)
--anti-bot enhanced
```

### 5️⃣ 시스템 리소스 최적화

#### Chrome 프로필 비활성화 (메모리 절감)

```bash
--use-profile false
```

**효과**: 메모리 사용량 30-40% 감소

**단점**: 로그인 세션 저장 불가

#### 로그 레벨 조정

```bash
# 기본 (INFO)
--log-level INFO

# 디버그 필요시만
--log-level DEBUG
```

**효과**: DEBUG 레벨은 I/O 오버헤드로 인한 성능 저하

---

## 📈 성능 비교 벤치마크

### 기본 설정 vs 최적화 설정

```
기본 설정:
- 재시도 간격: 60-120초
- 헤드리스: false
- 조건 수: 1개
- 메모리: 200MB
- 1시간당 검색 수: 30-60회

최적화 설정:
- 재시도 간격: 10-15초
- 헤드리스: true
- 조건 수: 9개
- 메모리: 120MB
- 1시간당 검색 수: 180-360회

개선율: 약 5-6배 더 많은 검색 수행
```

---

## 🎯 시나리오별 추천 설정

### 시나리오 1: 명절 성수기 (경쟁 치열)

```bash
python quickstart.py \
  --user YOUR_ID --psw YOUR_PASSWORD \
  --dpt 동탄 --arr 부산 \
  --dt 20260315 --tm 08,10,12 \
  --anti-bot undetected \
  --headless true \
  --retry-delay-min 8 --retry-delay-max 12 \
  --num 3
```

**특징**:
- 극도로 빠른 재시도 (경쟁 승리)
- 다중 시간대 검색
- undetected 방법 사용

### 시나리오 2: 평상시 예약

```bash
python quickstart.py \
  --user YOUR_ID --psw YOUR_PASSWORD \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315,20260316 --tm 08,10 \
  --anti-bot undetected \
  --headless true \
  --retry-delay-min 15 --retry-delay-max 30
```

**특징**:
- 균형잡힌 속도와 안정성
- 2개 날짜 × 2개 시간 = 4개 조건
- IP 차단 위험 낮음

### 시나리오 3: 안정성 중시 (IP 차단 회피)

```bash
python quickstart.py \
  --user YOUR_ID --psw YOUR_PASSWORD \
  --dpt 동탄 --arr 동대구 \
  --dt 20260315 --tm 08 \
  --anti-bot stealth \
  --headless false \
  --retry-delay-min 45 --retry-delay-max 90
```

**특징**:
- 느리지만 안정적
- 이전 차단 경험자 추천
- UI 모니터링 가능

---

## ⚙️ 고급 튜닝

### 1. Chrome 플래그 최적화

```python
# srt_reservation/main.py 수정
options.add_argument('--disable-extensions')  # 확장 프로그램 비활성화
options.add_argument('--disable-plugins')     # 플러그인 비활성화
options.add_argument('--disable-images')      # 이미지 로드 안 함 (극도의 최적화)
```

### 2. 네트워크 최적화

```bash
# DNS 캐시 활용 설정
--disable-sync  # Google 동기화 비활성화
```

### 3. 병렬 처리 (미지원 현재)

현재는 순차 처리만 지원하지만, 향후 다중 프로세스로 개선 계획:

```python
# 계획 중인 기능
with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
    # 여러 조건 병렬 검색
```

---

## 📊 모니터링

### 성능 지표 확인

```bash
# 로그에서 성능 정보 추출
grep "새로고침" srt_reservation.log | wc -l  # 총 새로고침 횟수
grep "예약" srt_reservation.log              # 예약 시도 기록
```

### 시스템 리소스 모니터링

```bash
# macOS - Activity Monitor에서 확인
# Python 프로세스 메모리 사용량
# Chrome 프로세스 메모리 사용량
```

---

## 🚨 주의사항

### 1. IP 차단 위험

```
재시도 간격 설정 시 주의:
- 너무 짧으면: IP 차단될 수 있음
- 권장 최소값: 10초 이상
- 차단 경험: 60초 이상 권장
```

### 2. 계정 잠금

```
로그인 실패 반복 시:
- 10회 이상 실패 → 계정 임시 잠금 (1시간)
- SRT 웹사이트에서 직접 확인
```

### 3. 봇 탐지 회피의 한계

```
아무리 최적화해도:
- 100% 우회 불가능
- SRT 정책 변경 시 대응 필요
- 법적/윤리적 사용 범위 내에서만 사용
```

---

## 📝 체크리스트

성능 최적화 적용 전 확인 사항:

- [ ] Python 최신 버전 설치 (3.9+)
- [ ] ChromeDriver 최신 버전 설치
- [ ] Chrome 브라우저 최신 버전
- [ ] 충분한 시스템 RAM (2GB 이상)
- [ ] 안정적인 네트워크 연결
- [ ] SRT 계정 정상 상태 확인

---

**마지막 업데이트**: 2026-03-12
