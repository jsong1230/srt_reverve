# 기여 가이드 (Contributing Guide)

SRT 자동 예약 프로젝트에 기여하는 방법입니다.

---

## 🤝 기여 방식

### 1️⃣ 이슈 보고 (Bug Reports)

버그를 발견했다면 GitHub Issues에 보고해주세요.

#### 이슈 제목
```
[BUG] 로그인 실패 - "StaleElementReferenceException" 발생
```

#### 이슈 내용 템플릿

```markdown
## 증상
- 어떤 현상이 발생했는가?
- 어떤 오류 메시지가 나왔는가?

## 재현 방법
```bash
python quickstart.py \
  --user 1234567890 --psw password123 \
  --dpt 동탄 --arr 부산 --dt 20260315 --tm 08
```

## 환경
- Python: 3.9.20
- Selenium: 4.15.0
- Chrome: 120.0
- macOS: 13.5

## 예상 결과
예약이 성공해야 함

## 실제 결과
StaleElementReferenceException 발생 후 프로그램 종료
```

---

### 2️⃣ 기능 요청 (Feature Requests)

새로운 기능을 제안하고 싶다면:

#### 이슈 제목
```
[FEATURE] 예약 메모 저장 기능 추가
```

#### 이슈 내용

```markdown
## 요청 기능
예약 성공 후 예약 번호, 시간, 좌석 등을 파일에 자동 저장

## 사용 사례
예약 확인 시 정보를 수동으로 찾을 필요 없음

## 제안 구현
- 예약 성공 시 JSON 파일 생성
- 파일명: `booking_YYYYMMDD_HHMMSS.json`
- 내용: {예약번호, 기차정보, 좌석, 가격}

## 우선순위
🟢 낮음 (나중에 해도 됨)
```

---

## 🛠️ 코드 기여

### Step 1: Fork & Clone

```bash
# 1. GitHub에서 Fork
# jsong1230/srt_reverve → YOUR_USERNAME/srt_reverve

# 2. 로컬에 Clone
git clone https://github.com/YOUR_USERNAME/srt_reverve.git
cd srt_reverve

# 3. Upstream 추가
git remote add upstream https://github.com/jsong1230/srt_reverve.git
```

### Step 2: 브랜치 생성

#### 브랜치 명명 규칙

```
feature/{기능-번호}-{기능-설명}      # 새 기능
bugfix/{버그-번호}-{버그-설명}      # 버그 수정
docs/{문서-설명}                    # 문서 작성
refactor/{모듈-설명}                # 리팩토링
```

#### 예시

```bash
# 새 기능
git checkout -b feature/f13-multi-process-booking

# 버그 수정
git checkout -b bugfix/memory-leak-fix

# 문서
git checkout -b docs/windows-setup-guide

# 리팩토링
git checkout -b refactor/split-main-module
```

### Step 3: 코드 작성

#### 코딩 규칙

**Python 스타일 (PEP 8)**

```python
# ✅ Good
def login_to_srt(user_id: str, password: str) -> bool:
    """SRT 사이트에 로그인합니다.

    Args:
        user_id: SRT 회원 ID
        password: SRT 비밀번호

    Returns:
        로그인 성공 여부

    Raises:
        InvalidCredentialsError: 잘못된 자격증명
    """
    logger.info(f"Logging in with ID: {user_id}")
    # ...
    return success


# ❌ Bad
def login(id,pw):
    logging.info("login")  # 부실한 설명
    # ...
    return True
```

**변수명 규칙**

```python
# ✅ Good
dpt_station = "동탄"
reservation_count = 0
is_booked = False

# ❌ Bad
ds = "동탄"          # 축약 금지
cnt = 0              # 의도 불명확
booked = False       # is_ 접두어 권장
```

**주석 작성**

```python
# ✅ Good
# 1분마다 새로고침 (봇 탐지 회피)
time.sleep(60)

# ❌ Bad
# 대기
time.sleep(60)

# ❌ 매우 나쁨
time.sleep(60)  # 딜레이
```

#### 로깅 레벨

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG - 개발자용 상세 정보
logger.debug(f"WebDriver element found: {element}")

# INFO - 정상 진행 상황
logger.info("Successfully logged in to SRT")

# WARNING - 경고 (재시도 가능)
logger.warning("Login attempt failed, retrying...")

# ERROR - 오류 (치명적)
logger.error("Failed to connect to SRT server")
```

### Step 4: 테스트 작성

#### 테스트 구조

```bash
tests/
├── test_main.py              # 메인 로직 테스트
├── test_validation.py        # 검증 로직 테스트
├── test_exceptions.py        # 예외 처리 테스트
└── test_main_recovery.py     # 복구 패턴 테스트
```

#### 테스트 작성 예시

```python
import pytest
from unittest.mock import Mock, patch
from srt_reservation.main import SRT
from srt_reservation.exceptions import InvalidStationNameError


class TestSRTValidation:
    """SRT 입력 검증 테스트"""

    def test_valid_station_name(self):
        """유효한 역명 검증"""
        srt = SRT("동탄", "부산", "20260315", "08")
        assert srt.dpt_stn == "동탄"

    def test_invalid_station_name(self):
        """잘못된 역명 검증"""
        with pytest.raises(InvalidStationNameError):
            SRT("강남", "부산", "20260315", "08")

    def test_valid_date_format(self):
        """유효한 날짜 형식 검증"""
        srt = SRT("동탄", "부산", "20260315", "08")
        assert srt.dpt_dt == "20260315"

    def test_invalid_date_format(self):
        """잘못된 날짜 형식 검증"""
        with pytest.raises(InvalidDateError):
            SRT("동탄", "부산", "2026-03-15", "08")

    @patch('srt_reservation.main.webdriver.Chrome')
    def test_login_success(self, mock_chrome):
        """로그인 성공 테스트"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        srt = SRT("동탄", "부산", "20260315", "08")
        srt.run_driver()
        assert srt.driver is not None
```

#### 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 특정 테스트
pytest tests/test_main.py::TestSRTValidation::test_valid_station_name -v

# 커버리지 확인
pytest tests/ --cov=srt_reservation --cov-report=html
```

### Step 5: Commit 메시지

#### Commit 메시지 포맷

```
<타입>(<범위>): <제목>

<설명>

<푸터>
```

#### 타입

- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 스타일 (공백, 포맷)
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 의존성 관리

#### 예시

```bash
# ✅ Good
git commit -m "feat(booking): 예약 후 JSON 저장 기능 추가

- 예약 성공 시 booking_YYYYMMDD.json 파일 생성
- 예약번호, 기차정보, 좌석 정보 포함
- 중복 저장 방지를 위한 파일명 충돌 체크

Fixes #42"

# ❌ Bad
git commit -m "수정"
git commit -m "기능 추가"
```

### Step 6: Push & Pull Request

```bash
# 1. 최신 upstream 받기
git fetch upstream
git rebase upstream/main

# 2. Push
git push origin feature/f13-multi-process-booking

# 3. GitHub에서 Pull Request 생성
# Compare & pull request 버튼 클릭

# 4. PR 제목과 설명 작성
```

#### Pull Request 템플릿

```markdown
## 📝 설명
이 PR은 무엇을 구현하는가?

## 🎯 관련 이슈
Fixes #42

## 💡 구현 방법
어떻게 구현했는가?
- 메커니즘 1
- 메커니즘 2

## ✅ 테스트
어떻게 테스트했는가?
```bash
python quickstart.py --user ID --psw PASS --dpt 동탄 --arr 부산 ...
```

## 📊 변경사항
- [ ] 버그 수정
- [x] 새 기능
- [ ] 문서 수정
- [ ] 테스트 추가

## 🚨 Breaking Changes
변경에 따른 API 호환성 문제?

없음
```

---

## 📋 체크리스트

PR을 보내기 전에 확인하세요:

- [ ] 코드가 PEP 8 스타일을 따름
- [ ] 모든 테스트 통과 (`pytest tests/ -v`)
- [ ] 새 기능에 테스트 추가
- [ ] 변경사항에 대한 설명 추가
- [ ] Commit 메시지가 명확함
- [ ] 불필요한 파일 커밋 안 함 (`.pyc`, `__pycache__`, `.env`)
- [ ] PR 설명이 상세함

---

## 🎓 개발 가이드

### 환경 설정

```bash
# 1. Python 3.9 설정
pyenv install 3.9.20
pyenv local 3.9.20

# 2. 가상환경
python3 -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 개발용

# 4. Pre-commit Hook (선택)
pre-commit install
```

### 디버깅

```python
# ✅ 적절한 로깅 사용
logger.debug(f"WebDriver state: {driver}")

# ❌ print 사용 금지
print("debug")  # 프로덕션에서 출력됨

# pdb 사용 (개발 중에만)
import pdb; pdb.set_trace()
```

### 성능 고려

```python
# ❌ Bad - 불필요한 재계산
for i in range(1000):
    result = expensive_function()  # 매번 실행

# ✅ Good - 결과 캐시
result = expensive_function()
for i in range(1000):
    use(result)

# ❌ Bad - 메모리 누수
driver = webdriver.Chrome()
# ... 사용 후
# driver.quit() 없음

# ✅ Good - 명시적 정리
driver = webdriver.Chrome()
try:
    # ... 사용
finally:
    driver.quit()
```

---

## 🐛 코드 리뷰 가이드

### 리뷰어 되기

- [ ] 코드 정확성 확인
- [ ] 테스트 커버리지 확인
- [ ] 문서 업데이트 확인
- [ ] 성능 문제 확인

### 피드백 제공

```markdown
❌ 좋지 않은 리뷰
"이건 잘못된 코드야"

✅ 좋은 리뷰
"메모리 누수 위험이 있습니다. `driver.quit()`을 finally 블록에 추가해주세요."

📚 제안
이 부분은 이렇게 개선할 수 있습니다: [코드 예시]
```

---

## 📚 자원

- [Git 이용 가이드](https://git-scm.com/book/ko/)
- [Python PEP 8](https://pep8.org/)
- [pytest 가이드](https://docs.pytest.org/)
- [Selenium 문서](https://www.selenium.dev/documentation/)

---

## ❓ 질문이 있으신가요?

1. [GitHub Issues](https://github.com/jsong1230/srt_reverve/issues)에서 질문하세요
2. [Discussions](https://github.com/jsong1230/srt_reverve/discussions)에서 토론하세요
3. 이 문서에서 찾을 수 없으면 새 이슈를 작성하세요

---

## 📄 라이선스

이 프로젝트의 모든 기여는 MIT 라이선스 하에서 이루어집니다.

---

**마지막 업데이트**: 2026-03-12

감사합니다! 🎉
