# macOS 환경 구축 가이드

SRT 예매 자동화 스크립트를 macOS에서 실행하기 위해 필요한 준비 절차를 정리했습니다. 아래 순서를 따라 하면 동일한 환경을 손쉽게 재현할 수 있습니다.

## 1. 기본 개발 도구 설치
- Xcode Command Line Tools (컴파일 및 기본 Unix 툴)
  ```bash
  xcode-select --install
  ```
- Homebrew (패키지 관리자)
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

## 2. 필수 패키지 설치
```bash
brew update
brew install pyenv
brew install chromedriver
```
- `chromedriver`는 SRT 웹 자동화를 위해 반드시 필요합니다. 설치 후 `/opt/homebrew/bin` 혹은 `/usr/local/bin`이 `PATH`에 포함되어 있는지 확인하세요.

## 3. pyenv 설정 및 Python 설치
터미널 초기화 파일(`~/.zshrc` 등)에 다음 내용을 추가합니다.
```bash
eval "$(pyenv init -)"
```
새 터미널을 열고 프로젝트 루트로 이동한 뒤 요구 버전을 설치·적용합니다.
```bash
cd /Users/jsong/dev/srt_reverve
pyenv install 3.9.20   # 이미 설치되어 있다면 건너뜀
pyenv local 3.9.20     # 이 명령이 .python-version을 설정
```
`python --version` 출력이 `3.9.20`인지 꼭 확인하세요.

## 4. 가상환경 생성 및 패키지 설치
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
작업을 마친 뒤에는 `deactivate`로 가상환경을 종료합니다.

## 5. 환경 확인
- Chrome 브라우저가 최신 버전인지, 설치된 `chromedriver`와 호환되는지 확인합니다.
- 필요한 경우 `which chromedriver`로 경로를 확인하고, 자동화 스크립트에서 해당 경로를 사용하도록 설정합니다.
- 회원 ID 기반 로그인이 필수이므로 유효한 SRT 계정 정보를 준비합니다.

## 6. 기본 실행 및 테스트
```bash
python quickstart.py --user <회원번호> --psw <비밀번호> --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08
```
추가 옵션(`--num`, `--reserve` 등)은 `README.md`를 참고하세요.

테스트로 환경을 검증하려면:
```bash
pytest tests/ -v
```

이 과정을 완료하면 macOS에서 SRT 예약 자동화 코드를 안정적으로 실행할 수 있습니다.

