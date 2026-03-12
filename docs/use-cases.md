# 실제 사용 예시 (Use Cases)

SRT 자동 예약 프로그램의 다양한 사용 사례와 실제 예제입니다.

---

## 📍 Use Case 1: 주말 부산 여행 예약

### 상황
- 금요일 저녁 동탄 → 부산 예약 (매진 상태)
- 주말 여행 4명 예약 필요
- 일반석 원함 (예약 대기 안 함)

### 명령어

```bash
python quickstart.py \
  --user 1234567890 \
  --psw 'password123' \
  --dpt 동탄 \
  --arr 부산 \
  --dt 20260315 \
  --tm 17,18,19 \
  --num 4 \
  --reserve False \
  --anti-bot undetected \
  --headless true \
  --retry-delay-min 15 --retry-delay-max 30
```

### 설명

| 옵션 | 값 | 이유 |
|------|-----|------|
| `--dt 20260315` | 금요일 | 여행 출발일 |
| `--tm 17,18,19` | 3개 시간대 | 저녁 시간 (일과 끝나고 출발) |
| `--num 4` | 4명 | 예약 필요 인원 |
| `--anti-bot undetected` | 우회율 높음 | 성수기 대비 |
| `--headless true` | 빠른 속도 | 경쟁 승리 필요 |

### 예상 결과

```
✅ 17:00 기차: 4인석 예약 성공 (05:23 소요)
또는
✅ 18:00 기차: 4인석 예약 성공 (12:45 소요)
또는
✅ 19:00 기차: 4인석 예약 성공 (8:12 소요)
```

---

## 📍 Use Case 2: 명절 특수 - 대체 경로 검색

### 상황
- 추석 명절 예약 (가장 경쟁 치열)
- 직통 불가능 → 경유 옵션 탐색
- 최대한 빨리 어떤 표든 예약해야 함

### 명령어

```bash
# 터미널 1: 동탄 → 부산 (직통)
python quickstart.py \
  --user 1234567890 --psw 'password123' \
  --dpt 동탄 --arr 부산 \
  --dt 20260315,20260316 --tm 08,10,12,14 \
  --num 1 --anti-bot undetected --headless true \
  --retry-delay-min 8 --retry-delay-max 12

# 터미널 2: 동탄 → 대전 (경유용)
python quickstart.py \
  --user 1234567890 --psw 'password123' \
  --dpt 동탄 --arr 대전 \
  --dt 20260315,20260316 --tm 08,10,12 \
  --num 1 --anti-bot undetected --headless true \
  --retry-delay-min 8 --retry-delay-max 12
```

### 설명

**멀티 프로세스 전략**:
- 2개 터미널에서 병렬 실행
- 더 많은 검색 시도 = 높은 예약 확률
- 어떤 것이든 먼저 예약되는 것 사용

**다중 시간대**:
- 아침(08), 오전(10), 정오(12), 오후(14)
- 예약 가능성 극대화

### 예상 결과

```
터미널 1:
⏳ 동탄→부산 검색 중... (1시간)
✅ 16:00에 10시 기차 예약 성공

또는

터미널 2:
⏳ 동탄→대전 검색 중... (45분)
✅ 14:32에 12시 기차 예약 성공 (경유 확인)

→ 둘 중 하나라도 예약 성공하면 여행 가능
```

---

## 📍 Use Case 3: 정기 출장 예약

### 상황
- 매주 목요일 서울(동탄) → 대구(동대구) 출장
- 반복 예약 필요
- 안정성 최우선

### 스크립트 자동화

```bash
#!/bin/bash
# book_weekly_trip.sh

USER_ID="1234567890"
PASSWORD="password123"

# 다음주 목요일 (일주일 뒤)
NEXT_THURSDAY=$(date -v+7d +%Y%m%d)

python quickstart.py \
  --user "$USER_ID" \
  --psw "$PASSWORD" \
  --dpt 동탄 \
  --arr 동대구 \
  --dt "$NEXT_THURSDAY" \
  --tm 06,07,08 \
  --num 1 \
  --reserve True \
  --anti-bot stealth \
  --retry-delay-min 30 --retry-delay-max 60
```

### 설정 이유

| 옵션 | 설정 | 이유 |
|------|------|------|
| `--tm 06,07,08` | 이른 시간 | 출장 서둘러야 함 |
| `--reserve True` | 예약 대기 | 못 사도 대기 신청 |
| `--anti-bot stealth` | 안정성 | 정기 실행은 IP 차단 회피 |
| `--retry-delay 30-60` | 느림 | 안정성 중시 |

### 자동화 설정 (cron)

```bash
# 매주 월요일 09:00에 자동 실행
0 9 * * 1 /path/to/book_weekly_trip.sh
```

---

## 📍 Use Case 4: 개발자/테스터용 API 활용

### 상황
- Python 코드로 직접 통제
- 로그 수집 및 분석
- 맞춤형 에러 처리

### Python 코드 예시

```python
#!/usr/bin/env python3
from srt_reservation.main import SRT
from srt_reservation.exceptions import InvalidStationNameError
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def book_train_with_retry(max_attempts=3):
    """3회 시도 후 포기"""
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"시도 {attempt}/{max_attempts}")

            srt = SRT(
                dpt_stn='동탄',
                arr_stn='동대구',
                dpt_dt='20260315',
                dpt_tm='08',
                num_trains_to_check=2,
                anti_bot_method='undetected',
                headless=True
            )

            srt.set_log_info('1234567890', 'password123')
            srt.run()

            # 성공 시 루프 탈출
            logger.info("✅ 예약 성공!")
            break

        except InvalidStationNameError as e:
            logger.error(f"역 이름 오류: {e}")
            break  # 재시도 불필요

        except Exception as e:
            logger.warning(f"시도 {attempt} 실패: {e}")
            if attempt == max_attempts:
                logger.error("❌ 모든 시도 실패")
                raise

if __name__ == '__main__':
    book_train_with_retry()
```

### 활용 사례

```python
# 1. 데이터 수집
srt_list = []
for date in ['20260315', '20260316', '20260317']:
    srt = SRT(..., dpt_dt=date)
    # 수집 로직
    srt_list.append(result)

# 2. 로그 분석
import json
with open('srt_log.json', 'r') as f:
    logs = json.load(f)
    retry_count = sum(1 for log in logs if 'retry' in log['message'])
    print(f"총 재시도: {retry_count}회")

# 3. 성공률 계산
success_rate = (success_count / total_attempts) * 100
print(f"성공률: {success_rate:.1f}%")
```

---

## 📍 Use Case 5: 헤드리스 모드 + 서버 실행

### 상황
- VPS/클라우드 서버에서 실행
- GUI 환경 없음
- 24시간 지속 예약 필요

### 서버 설정

```bash
# 1. SSH 접속
ssh user@your-server.com

# 2. 가상환경 활성화
cd /home/user/srt_reverve
source .venv/bin/activate

# 3. 헤드리스 모드로 실행
python quickstart.py \
  --user 1234567890 \
  --psw password123 \
  --dpt 동탄 \
  --arr 부산 \
  --dt 20260315,20260316,20260317 \
  --tm 08,10,12 \
  --headless true \
  --log-level INFO \
  > srt_output.log 2>&1 &

# 4. 백그라운드 실행 확인
jobs -l
nohup python quickstart.py ... > srt.log &
```

### systemd 서비스 설정

```ini
# /etc/systemd/system/srt-booking.service
[Unit]
Description=SRT Auto Booking Service
After=network.target

[Service]
Type=simple
User=srt-user
WorkingDirectory=/home/srt-user/srt_reverve
ExecStart=/home/srt-user/srt_reverve/.venv/bin/python quickstart.py \
  --user 1234567890 --psw password123 \
  --dpt 동탄 --arr 부산 \
  --dt 20260315 --tm 08 \
  --headless true --log-level INFO
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
```

### 실행

```bash
sudo systemctl enable srt-booking
sudo systemctl start srt-booking
sudo journalctl -u srt-booking -f  # 로그 확인
```

---

## 📍 Use Case 6: Docker 컨테이너 실행

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 헤드리스 모드로 실행
CMD ["python", "quickstart.py", \
     "--headless", "true", \
     "--log-level", "INFO"]
```

### Docker 실행

```bash
docker build -t srt-booking .

docker run \
  -e SRT_USER_ID=1234567890 \
  -e SRT_PASSWORD=password123 \
  -v $(pwd)/logs:/app/logs \
  srt-booking \
  python quickstart.py \
    --user $SRT_USER_ID \
    --psw $SRT_PASSWORD \
    --dpt 동탄 --arr 부산 \
    --dt 20260315 --tm 08 \
    --headless true
```

---

## 🎯 시나리오별 빠른 참조

### 1. 급할 때 (5분 안에 예약)
```bash
python quickstart.py --user ID --psw PASS --dpt 동탄 --arr 부산 \
  --dt 20260315 --tm 08 --headless true --retry-delay-min 8 --retry-delay-max 10
```

### 2. 안정적으로 (IP 차단 회피)
```bash
python quickstart.py --user ID --psw PASS --dpt 동탄 --arr 부산 \
  --dt 20260315 --tm 08 --anti-bot stealth --retry-delay-min 60 --retry-delay-max 120
```

### 3. 다중 옵션 (최고의 확률)
```bash
python quickstart.py --user ID --psw PASS --dpt 동탄 --arr 부산 \
  --dt 20260315,20260316 --tm 08,10,12 --num 2 --headless true \
  --anti-bot undetected --retry-delay-min 10 --retry-delay-max 20
```

### 4. 예약 대기 (절대 못 놓칠 때)
```bash
python quickstart.py --user ID --psw PASS --dpt 동탄 --arr 부산 \
  --dt 20260315 --tm 08 --reserve true --anti-bot undetected --headless true
```

---

## ⚠️ 주의사항

### 1. 보안
```bash
# ❌ 나쁜 예: 명령어에 직접 입력
python quickstart.py --user 1234567890 --psw password123

# ✅ 좋은 예: 환경변수 사용
export SRT_USER_ID=1234567890
export SRT_PASSWORD=password123
python quickstart.py --user $SRT_USER_ID --psw $SRT_PASSWORD
```

### 2. IP 차단 회피
```bash
# 여러 계정으로 동시 실행 시 IP 차단 위험 ⬆️
# 안전을 위해 한 IP당 1개 계정만 권장
```

### 3. 법적/윤리적 사용
```
- 개인 사용만 허용
- 재판매 목적 금지
- 대량 예약 금지
- SRT 이용약관 확인 필수
```

---

**마지막 업데이트**: 2026-03-12
