# -*- coding: utf-8 -*-
import os
import time
from random import randint, uniform
import logging
from datetime import datetime
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
    InvalidSessionIdException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

from srt_reservation.exceptions import InvalidStationNameError, InvalidDateError, InvalidDateFormatError, InvalidTimeFormatError
from srt_reservation.validation import station_list
from srt_reservation.recovery import (
    RecoveryContext,
    RecoveryError,
    NetworkErrorRecovery,
    SessionRecovery,
    BrowserRecovery,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# chromedriver 경로는 환경 변수에서 가져오거나 기본값 사용
chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')

# 봇 탐지 우회 방법 선택 (환경변수로 제어 가능)
# 옵션: 'undetected', 'stealth', 'enhanced'
ANTI_BOT_METHOD = os.environ.get('ANTI_BOT_METHOD', 'undetected')

# 선택적 import (설치된 경우에만 사용)
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
    logger.info("undetected-chromedriver 사용 가능")
except ImportError:
    UNDETECTED_AVAILABLE = False
    logger.warning("undetected-chromedriver가 설치되지 않았습니다. 기본 모드 사용")

try:
    from selenium_stealth import stealth
    STEALTH_AVAILABLE = True
    logger.info("selenium-stealth 사용 가능")
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("selenium-stealth가 설치되지 않았습니다.")


def _is_browser_session_lost(exc):
    """브라우저가 닫히거나 세션이 끊어진 예외인지 확인"""
    if isinstance(exc, InvalidSessionIdException):
        return True
    if isinstance(exc, WebDriverException):
        msg = str(exc).lower()
        return "invalid session" in msg or "session deleted" in msg or "browser has closed" in msg
    return False

class SRT:
    def __init__(self, dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check=2, want_reserve=False, anti_bot_method=None, retry_delay_min=60, retry_delay_max=120, use_profile=True, profile_dir=None):
        """
        :param dpt_stn: SRT 출발역
        :param arr_stn: SRT 도착역
        :param dpt_dt: 출발 날짜 YYYYMMDD 형태 ex) 20220115
        :param dpt_tm: 출발 시간 hh 형태, 반드시 짝수 ex) 06, 08, 14, ...
        :param num_trains_to_check: 검색 결과 중 예약 가능 여부 확인할 기차의 수 ex) 2일 경우 상위 2개 확인
        :param want_reserve: 예약 대기가 가능할 경우 선택 여부
        :param anti_bot_method: 봇 탐지 우회 방법 ('undetected', 'stealth', 'enhanced', None)
        :param retry_delay_min: 재시도 최소 대기 시간(초) - 기본 60초
        :param retry_delay_max: 재시도 최대 대기 시간(초) - 기본 120초
        :param use_profile: 실제 Chrome 프로필 사용 여부 (기본: True, 봇 탐지 회피에 매우 효과적)
        :param profile_dir: Chrome 프로필 디렉토리 (None이면 기본 프로필 사용)
        """
        self.login_id = None
        self.login_psw = None

        self.dpt_stn = dpt_stn
        self.arr_stn = arr_stn
        self.dpt_dt = dpt_dt
        self.dpt_tm = dpt_tm

        self.num_trains_to_check = num_trains_to_check
        self.want_reserve = want_reserve
        self.driver = None

        self.is_booked = False  # 예약 완료 되었는지 확인용
        self.cnt_refresh = 0  # 새로고침 회수 기록
        self.recovery_context = RecoveryContext(max_retries=3)

        # 재시도 간격 설정 (봇 탐지 회피)
        self.retry_delay_min = retry_delay_min
        self.retry_delay_max = retry_delay_max

        # Chrome 프로필 설정
        self.use_profile = use_profile
        self.profile_dir = profile_dir
        if self.use_profile:
            logger.info("실제 Chrome 프로필 사용 모드 (봇 탐지 회피 효과 높음)")

        # 봇 탐지 우회 방법 설정
        if anti_bot_method:
            self.anti_bot_method = anti_bot_method
        else:
            self.anti_bot_method = ANTI_BOT_METHOD

        logger.info(f"봇 탐지 우회 방법: {self.anti_bot_method}")
        logger.info(f"재시도 간격: {self.retry_delay_min}~{self.retry_delay_max}초")

        self.check_input()

    def check_input(self):
        if self.dpt_stn not in station_list:
            raise InvalidStationNameError(f"출발역 오류. '{self.dpt_stn}' 은/는 목록에 없습니다.")
        if self.arr_stn not in station_list:
            raise InvalidStationNameError(f"도착역 오류. '{self.arr_stn}' 은/는 목록에 없습니다.")
        if self.dpt_stn == self.arr_stn:
            raise InvalidStationNameError("출발역과 도착역이 같을 수 없습니다.")
        date_str = str(self.dpt_dt)
        if not date_str.isnumeric():
            raise InvalidDateFormatError("날짜는 숫자로만 이루어져야 합니다.")
        if len(date_str) != 8:
            raise InvalidDateError("날짜가 잘못 되었습니다. YYYYMMDD 형식으로 입력해주세요.")
        try:
            datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            raise InvalidDateError("날짜가 잘못 되었습니다. YYYYMMDD 형식으로 입력해주세요.")
        # 시간 형식 검증 (짝수 시간만 허용)
        try:
            hour = int(self.dpt_tm)
            if hour < 0 or hour > 23:
                raise InvalidTimeFormatError("시간은 0-23 사이의 값이어야 합니다.")
            if hour % 2 != 0:
                raise InvalidTimeFormatError("시간은 짝수 시간만 허용됩니다. (예: 06, 08, 10, ...)")
        except ValueError:
            raise InvalidTimeFormatError("시간은 숫자 형식이어야 합니다. (예: 06, 08, 14)")

    def set_log_info(self, login_id, login_psw):
        if not login_id or not login_psw:
            raise ValueError("로그인 ID와 비밀번호는 필수입니다.")
        self.login_id = login_id
        self.login_psw = login_psw

    def _get_chrome_profile_path(self):
        """Chrome 프로필 경로 자동 감지 (macOS, Linux, Windows)"""
        import platform

        system = platform.system()
        home = os.path.expanduser("~")

        if system == "Darwin":  # macOS
            base_path = os.path.join(home, "Library", "Application Support", "Google", "Chrome")
        elif system == "Linux":
            base_path = os.path.join(home, ".config", "google-chrome")
        elif system == "Windows":
            base_path = os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data")
        else:
            logger.warning(f"알 수 없는 운영체제: {system}")
            return None

        if not os.path.exists(base_path):
            logger.warning(f"Chrome 프로필 경로를 찾을 수 없습니다: {base_path}")
            return None

        return base_path

    def _chrome_options(self, for_undetected=False):
        """크롬 창 유지, 장시간 실행 안정성, 봇 탐지 완화 옵션

        :param for_undetected: undetected-chromedriver 사용 시 True
        """
        if for_undetected:
            # undetected-chromedriver는 자체 옵션을 사용
            options = uc.ChromeOptions() if UNDETECTED_AVAILABLE else ChromeOptions()
        else:
            options = ChromeOptions()

        # 실제 Chrome 프로필 사용 (봇 탐지 회피에 매우 효과적)
        if self.use_profile:
            if self.profile_dir:
                profile_path = self.profile_dir
            else:
                profile_path = self._get_chrome_profile_path()

            if profile_path and os.path.exists(profile_path):
                logger.info(f"Chrome 프로필 사용: {profile_path}")
                options.add_argument(f"--user-data-dir={profile_path}")
                options.add_argument("--profile-directory=Default")
                logger.warning("⚠️  주의: Chrome이 실행 중이면 프로필을 사용할 수 없습니다. Chrome을 먼저 종료해주세요.")
            else:
                logger.warning("Chrome 프로필 경로를 찾을 수 없어서 프로필 없이 실행합니다.")

        # 스크립트 종료 후에도 크롬 창이 닫히지 않도록 (detach)
        # undetected-chromedriver는 detach 옵션을 지원하지 않으므로 제외
        if not for_undetected:
            options.add_experimental_option("detach", True)

        # 강화된 봇/자동화 탐지 완화 옵션
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        # 추가 봇 탐지 완화 옵션
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
        }
        options.add_experimental_option("prefs", prefs)

        # 일반 사용자처럼 보이는 User-Agent 설정
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')

        # 자동화 제어 플래그 비활성화
        options.add_argument("--disable-blink-features=AutomationControlled")

        # 장시간 새로고침 시 크롬이 꺼지지 않도록 안정성 옵션
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--no-sandbox")

        # 일반 사용자에 가깝게
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")

        # 언어 설정
        options.add_argument("--lang=ko-KR")

        return options

    def _get_chrome_version(self):
        """설치된 Chrome 버전 감지"""
        import subprocess
        import re
        import platform

        try:
            system = platform.system()

            if system == "Darwin":  # macOS
                cmd = '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --version'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                version_str = result.stdout.strip()
            elif system == "Linux":
                cmd = 'google-chrome --version'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                version_str = result.stdout.strip()
            elif system == "Windows":
                cmd = r'reg query "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon" /v version'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                version_str = result.stdout.strip()
            else:
                logger.warning(f"알 수 없는 운영체제: {system}")
                return None

            # 버전 번호 추출 (예: "Google Chrome 144.0.7559.133" → 144)
            match = re.search(r'(\d+)\.', version_str)
            if match:
                major_version = int(match.group(1))
                logger.info(f"감지된 Chrome 버전: {major_version}")
                return major_version
            else:
                logger.warning(f"Chrome 버전을 파싱할 수 없습니다: {version_str}")
                return None
        except Exception as e:
            logger.warning(f"Chrome 버전 감지 실패: {e}")
            return None

    def _run_driver_undetected(self):
        """undetected-chromedriver를 사용한 WebDriver 초기화 (가장 강력한 우회)"""
        if not UNDETECTED_AVAILABLE:
            logger.error("undetected-chromedriver가 설치되지 않았습니다. pip install undetected-chromedriver")
            raise ImportError("undetected-chromedriver를 설치해주세요: pip install undetected-chromedriver")

        # Chrome 버전 자동 감지
        chrome_version = self._get_chrome_version()

        try:
            # undetected_chromedriver는 최소한의 옵션만 사용
            # 너무 많은 옵션은 오히려 문제를 일으킬 수 있음
            options = uc.ChromeOptions()

            # 실제 Chrome 프로필 사용
            if self.use_profile:
                if self.profile_dir:
                    profile_path = self.profile_dir
                else:
                    profile_path = self._get_chrome_profile_path()

                if profile_path and os.path.exists(profile_path):
                    logger.info(f"Chrome 프로필 사용: {profile_path}")
                    options.add_argument(f"--user-data-dir={profile_path}")
                    options.add_argument("--profile-directory=Default")
                    logger.warning("⚠️  주의: Chrome이 실행 중이면 프로필을 사용할 수 없습니다. Chrome을 먼저 종료해주세요.")

            # 필수 옵션만 추가
            options.add_argument("--start-maximized")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")

            # 언어 설정
            options.add_argument("--lang=ko-KR")

            # User-Agent (선택사항)
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            options.add_argument(f'user-agent={user_agent}')

            # undetected_chromedriver 사용
            self.driver = uc.Chrome(
                options=options,
                version_main=chrome_version,  # 감지된 Chrome 버전 사용
                driver_executable_path=None,  # 자동으로 ChromeDriver 다운로드
                use_subprocess=False,
            )
            logger.info(f"undetected-chromedriver로 ChromeDriver를 초기화했습니다 (Chrome {chrome_version})")
        except Exception as e:
            logger.error(f"undetected-chromedriver 초기화 실패: {e}")
            logger.info("Chrome을 최신 버전으로 업데이트하거나, --anti-bot stealth 옵션을 시도해보세요.")
            raise

        # 추가 스크립트 주입
        self._inject_stealth_scripts()

    def _run_driver_stealth(self):
        """selenium-stealth를 사용한 WebDriver 초기화"""
        if not STEALTH_AVAILABLE:
            logger.error("selenium-stealth가 설치되지 않았습니다. pip install selenium-stealth")
            raise ImportError("selenium-stealth를 설치해주세요: pip install selenium-stealth")

        options = self._chrome_options()

        try:
            # 일반 ChromeDriver 초기화
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info(f"ChromeDriver를 {chromedriver_path}에서 로드했습니다.")
        except (WebDriverException, FileNotFoundError) as e:
            logger.warning(f"기본 경로에서 ChromeDriver를 찾을 수 없습니다: {e}")
            logger.info("WebDriver Manager를 사용하여 ChromeDriver를 설치합니다.")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("ChromeDriver 설치 완료")

        # selenium-stealth 적용
        stealth(self.driver,
                languages=["ko-KR", "ko", "en-US", "en"],
                vendor="Google Inc.",
                platform="MacIntel",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )
        logger.info("selenium-stealth 적용 완료")

    def _run_driver_enhanced(self):
        """향상된 옵션을 사용한 WebDriver 초기화"""
        options = self._chrome_options()

        try:
            # Service 객체를 사용하여 ChromeDriver 초기화
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info(f"ChromeDriver를 {chromedriver_path}에서 로드했습니다.")
        except (WebDriverException, FileNotFoundError) as e:
            # WebDriverException 발생 시, WebDriver Manager로 드라이버 설치
            logger.warning(f"기본 경로에서 ChromeDriver를 찾을 수 없습니다: {e}")
            logger.info("WebDriver Manager를 사용하여 ChromeDriver를 설치합니다.")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("ChromeDriver 설치 완료")

        # 추가 스크립트 주입
        self._inject_stealth_scripts()

    def _inject_stealth_scripts(self):
        """봇 탐지 우회를 위한 JavaScript 스크립트 주입"""
        try:
            # navigator.webdriver 숨기기
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    """
                }
            )

            # Chrome 객체 추가
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    window.chrome = {
                        runtime: {}
                    };
                    """
                }
            )

            # Permissions 수정
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: () => Promise.resolve({ state: 'granted' })
                        })
                    });
                    """
                }
            )

            # Plugins 수정
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    """
                }
            )

            # Languages 수정
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ko-KR', 'ko', 'en-US', 'en']
                    });
                    """
                }
            )

            logger.info("스텔스 스크립트 주입 완료")
        except Exception as e:
            logger.warning(f"스크립트 주입 중 오류 (무시 가능): {e}")

    def run_driver(self):
        """Chrome WebDriver 초기화 - 선택한 방법에 따라 다르게 초기화"""
        logger.info(f"선택한 봇 탐지 우회 방법: {self.anti_bot_method}")

        if self.anti_bot_method == 'undetected' and UNDETECTED_AVAILABLE:
            self._run_driver_undetected()
        elif self.anti_bot_method == 'stealth' and STEALTH_AVAILABLE:
            self._run_driver_stealth()
        else:
            # 기본값 또는 'enhanced'
            if self.anti_bot_method not in ['enhanced', 'undetected', 'stealth']:
                logger.warning(f"알 수 없는 방법: {self.anti_bot_method}. 향상된 모드 사용")
            self._run_driver_enhanced()

        logger.info("WebDriver 초기화 완료")
        logger.info(f"브라우저 시작됨, 현재 URL: {self.driver.current_url}")

    def _human_like_delay(self, min_sec=0.5, max_sec=2.0):
        """인간처럼 랜덤 대기"""
        delay = uniform(min_sec, max_sec)
        time.sleep(delay)

    def _human_like_type(self, element, text, typing_speed=0.1):
        """인간처럼 타이핑 (글자 하나씩 입력)"""
        for char in text:
            element.send_keys(char)
            time.sleep(uniform(0.05, typing_speed))

    def _smooth_scroll(self, element):
        """부드러운 스크롤"""
        try:
            # 요소 위치 가져오기
            location = element.location_once_scrolled_into_view
            # JavaScript로 부드럽게 스크롤
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            self._human_like_delay(0.3, 0.8)
        except Exception as e:
            logger.debug(f"스크롤 중 오류 (무시): {e}")

    def _random_mouse_movement(self):
        """랜덤 마우스 이동 시뮬레이션"""
        try:
            # JavaScript로 마우스 이벤트 트리거
            self.driver.execute_script("""
                var event = new MouseEvent('mousemove', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': Math.random() * window.innerWidth,
                    'clientY': Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)
        except Exception as e:
            logger.debug(f"마우스 이동 시뮬레이션 중 오류 (무시): {e}")

    def close_driver(self):
        """WebDriver 리소스 정리"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver가 정상적으로 종료되었습니다.")
            except Exception as e:
                if _is_browser_session_lost(e):
                    logger.info("브라우저가 이미 종료되어 있습니다.")
                else:
                    logger.error(f"WebDriver 종료 중 오류 발생: {e}")
    
    def handle_alert(self):
        """Alert 처리 헬퍼 메서드"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            logger.warning(f"Alert 발생: {alert_text}")
            alert.accept()
            return True
        except NoAlertPresentException:
            return False
        except Exception as e:
            logger.error(f"Alert 처리 중 오류 발생: {e}")
            return False

    def login(self):
        """SRT 로그인 - 인간처럼 동작"""
        logger.info("로그인 페이지로 이동 중...")
        try:
            self.driver.get('https://etk.srail.co.kr/cmc/01/selectLoginForm.do')
            logger.info(f"현재 URL: {self.driver.current_url}")
            self._human_like_delay(1.0, 2.0)  # 페이지 로딩 대기
        except UnexpectedAlertPresentException:
            logger.warning("Alert 발생, 처리 중...")
            self.handle_alert()
            # Alert 처리 후 다시 시도
            self.driver.get('https://etk.srail.co.kr/cmc/01/selectLoginForm.do')
            self._human_like_delay(1.0, 2.0)
        except Exception as e:
            logger.error(f"로그인 페이지 로드 중 오류: {e}")
            logger.error(f"현재 URL: {self.driver.current_url if self.driver else 'driver 없음'}")
            raise

        # 랜덤 마우스 이동 시뮬레이션
        self._random_mouse_movement()

        wait = WebDriverWait(self.driver, 15)
        try:
            # ID 입력 - 인간처럼 타이핑
            id_input = wait.until(EC.element_to_be_clickable((By.ID, 'srchDvNm01')))
            self._smooth_scroll(id_input)
            id_input.clear()
            self._human_like_delay(0.3, 0.7)
            self._human_like_type(id_input, str(self.login_id), typing_speed=0.15)
            self._human_like_delay(0.5, 1.0)

            # 비밀번호 입력 - 인간처럼 타이핑
            password_input = wait.until(EC.element_to_be_clickable((By.ID, 'hmpgPwdCphd01')))
            self._smooth_scroll(password_input)
            password_input.clear()
            self._human_like_delay(0.3, 0.7)
            self._human_like_type(password_input, str(self.login_psw), typing_speed=0.15)
            self._human_like_delay(0.8, 1.5)

            # 로그인 버튼 클릭
            login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#login-form input.loginSubmit:not([disabled])')))
            self._smooth_scroll(login_button)
            self._human_like_delay(0.5, 1.0)

            try:
                login_button.click()
            except ElementClickInterceptedException:
                logger.warning("로그인 버튼 클릭이 가로채어짐, JavaScript 클릭으로 재시도")
                self.driver.execute_script("arguments[0].click();", login_button)

            logger.info("로그인 버튼 클릭 완료")

            # 로그인 처리 대기
            self._human_like_delay(2.0, 3.5)
            self.driver.implicitly_wait(10)
            logger.info("로그인 시도 완료")
        except Exception as e:
            logger.error(f"로그인 중 오류 발생: {e}")
            raise
        return self.driver

    def check_login(self):
        """로그인 성공 여부 확인"""
        try:
            wait = WebDriverWait(self.driver, 10)
            # 여러 방법으로 로그인 확인 시도
            try:
                # 방법 1: 환영 메시지 확인
                menu_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#wrap > div.header.header-e > div.global.clear > div")))
                menu_text = menu_element.text
                if "환영합니다" in menu_text:
                    logger.info("로그인 확인: 환영 메시지 발견")
                    return True
            except:
                pass
            
            try:
                # 방법 2: 로그인 폼이 사라졌는지 확인
                wait.until(EC.invisibility_of_element_located((By.ID, "login-form")))
                logger.info("로그인 확인: 로그인 폼 사라짐")
                return True
            except:
                pass
            
            try:
                # 방법 3: URL 변경 확인
                current_url = self.driver.current_url
                if "selectLoginForm" not in current_url:
                    logger.info(f"로그인 확인: URL 변경됨 ({current_url})")
                    return True
            except:
                pass
            
            logger.warning("로그인 확인 실패: 모든 확인 방법 실패")
            return False
        except Exception as e:
            logger.error(f"로그인 확인 중 오류: {e}")
            return False

    def go_search(self):
        """기차 조회 페이지로 이동 및 검색 조건 입력"""
        try:
            self.driver.get('https://etk.srail.co.kr/hpg/hra/01/selectScheduleList.do')
        except UnexpectedAlertPresentException:
            self.handle_alert()
            # Alert 처리 후 다시 시도
            self.driver.get('https://etk.srail.co.kr/hpg/hra/01/selectScheduleList.do')
        self.driver.implicitly_wait(5)

        # 출발지 입력
        elm_dpt_stn = self.driver.find_element(By.ID, 'dptRsStnCdNm')
        elm_dpt_stn.clear()
        elm_dpt_stn.send_keys(self.dpt_stn)

        # 도착지 입력
        elm_arr_stn = self.driver.find_element(By.ID, 'arvRsStnCdNm')
        elm_arr_stn.clear()
        elm_arr_stn.send_keys(self.arr_stn)

        # 출발 날짜 입력
        wait = WebDriverWait(self.driver, 10)
        elm_dpt_dt = wait.until(EC.presence_of_element_located((By.ID, "dptDt")))
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_dt)
        
        date_select = Select(elm_dpt_dt)
        
        # 사용 가능한 날짜 옵션 확인
        available_dates = [option.get_attribute('value') for option in date_select.options if option.get_attribute('value')]
        logger.info(f"사용 가능한 날짜 옵션 수: {len(available_dates)}")
        
        # 날짜 선택 시도
        try:
            date_select.select_by_value(self.dpt_dt)
            logger.info(f"날짜 선택 성공: {self.dpt_dt}")
        except Exception as e:
            logger.error(f"날짜 선택 실패: {self.dpt_dt}")
            logger.error(f"사용 가능한 날짜 옵션: {available_dates[:10]}...")  # 처음 10개만 표시
            raise Exception(f"날짜 '{self.dpt_dt}'를 선택할 수 없습니다. 예약 가능한 날짜 범위를 확인해주세요.")

        # 출발 시간 입력
        elm_dpt_tm = self.driver.find_element(By.ID, "dptTm")
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_tm)
        Select(self.driver.find_element(By.ID, "dptTm")).select_by_visible_text(self.dpt_tm)

        logger.info("기차를 조회합니다")
        logger.info(f"출발역: {self.dpt_stn}, 도착역: {self.arr_stn}")
        logger.info(f"날짜: {self.dpt_dt}, 시간: {self.dpt_tm}시 이후")
        logger.info(f"{self.num_trains_to_check}개의 기차 중 예약 확인")
        logger.info(f"예약 대기 사용: {self.want_reserve}")

        try:
            self.driver.find_element(By.XPATH, "//input[@value='조회하기']").click()
            self.driver.implicitly_wait(5)
            time.sleep(1)
        except Exception as e:
            logger.error(f"조회 버튼 클릭 중 오류 발생: {e}")
            raise

    def book_ticket(self, standard_seat, i):
        """
        일반석 예약 시도
        :param standard_seat: 일반석 검색 결과 텍스트
        :param i: 기차 번호 (테이블 행 번호)
        :return: 예약 성공 시 driver, 실패 시 None
        """
        if "예약하기" in standard_seat:
            logger.info(f"{i}번째 기차 예약 가능 - 예약 시도")

            # Error handling in case that click does not work
            try:
                self.driver.find_element(By.CSS_SELECTOR,
                                         f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a").click()
            except ElementClickInterceptedException as err:
                logger.warning(f"클릭 실패, ENTER 키로 재시도: {err}")
                try:
                    self.driver.find_element(By.CSS_SELECTOR,
                                             f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a").send_keys(Keys.ENTER)
                except Exception as e:
                    logger.error(f"예약 버튼 클릭 실패: {e}")
                    return None
            finally:
                self.driver.implicitly_wait(3)

            # 예약이 성공하면
            if self.driver.find_elements(By.ID, 'isFalseGotoMain'):
                self.is_booked = True
                logger.info("예약 성공!")
                return self.driver
            else:
                logger.info("잔여석 없음. 다시 검색")
                self.driver.back()  # 뒤로가기
                self.driver.implicitly_wait(5)
        return None

    def refresh_result(self):
        """검색 결과 새로고침"""
        try:
            submit = self.driver.find_element(By.XPATH, "//input[@value='조회하기']")
            self.driver.execute_script("arguments[0].click();", submit)
            self.cnt_refresh += 1
            logger.info(f"새로고침 {self.cnt_refresh}회")
            self.driver.implicitly_wait(10)
            time.sleep(0.5)
        except Exception as e:
            if _is_browser_session_lost(e):
                logger.error("새로고침 중 브라우저 연결이 끊어졌습니다.")
            else:
                logger.error(f"새로고침 중 오류 발생: {e}")
            raise

    def reserve_ticket(self, reservation, i):
        """예약 대기 신청"""
        if "신청하기" in reservation:
            logger.info(f"{i}번째 기차 예약 대기 신청")
            try:
                self.driver.find_element(By.CSS_SELECTOR,
                                         f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(8) > a").click()
                self.is_booked = True
                logger.info("예약 대기 신청 완료")
                return self.is_booked
            except Exception as e:
                logger.error(f"예약 대기 신청 중 오류 발생: {e}")
                return False
        return False

    def _check_result_once(self):
        """단일 검색 결과 확인 사이클 (네트워크 오류 복구에서 호출)"""
        for i in range(1, self.num_trains_to_check + 1):
            try:
                standard_seat = self.driver.find_element(
                    By.CSS_SELECTOR,
                    f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7)"
                ).text
                reservation = self.driver.find_element(
                    By.CSS_SELECTOR,
                    f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(8)"
                ).text
            except StaleElementReferenceException:
                logger.warning(f"{i}번째 기차 정보를 가져올 수 없습니다 (StaleElement)")
                standard_seat = "매진"
                reservation = "매진"
            except Exception as e:
                logger.warning(f"{i}번째 기차 정보를 가져올 수 없습니다: {e}")
                standard_seat = "매진"
                reservation = "매진"

            if self.book_ticket(standard_seat, i):
                return self.driver

            if self.want_reserve:
                if self.reserve_ticket(reservation, i):
                    return self.driver

        return None

    def check_result(self):
        """검색 결과 확인 및 예약 시도 (예약 성공 또는 오류 시까지 반복)"""
        while True:
            try:
                result = NetworkErrorRecovery.recover(
                    operation=self._check_result_once,
                    context=self.recovery_context,
                )
                if result is not None:
                    return result
            except RecoveryError as e:
                logger.error(f"네트워크 오류 복구 실패: {e}")
                raise
            except Exception as e:
                if SessionRecovery.is_session_expired(self.driver):
                    logger.warning("세션 만료 감지. 재로그인 시도...")
                    try:
                        SessionRecovery.recover(
                            driver=self.driver,
                            srt_instance=self,
                            context=self.recovery_context,
                        )
                        self.go_search()
                        continue
                    except RecoveryError as recovery_err:
                        logger.error(f"세션 복구 실패: {recovery_err}")
                        raise
                else:
                    raise

            if self.is_booked:
                return self.driver

            # 재시도 간격 (봇 탐지 회피)
            delay = randint(self.retry_delay_min, self.retry_delay_max)
            logger.info(f"다음 시도까지 {delay}초 대기...")
            time.sleep(delay)
            self.refresh_result()

    def run(self, login_id, login_psw):
        """
        SRT 예약 프로세스 실행
        :param login_id: 로그인 ID
        :param login_psw: 로그인 비밀번호
        """
        try:
            self.run_driver()
            self.set_log_info(login_id, login_psw)
            self.login()
            
            # 로그인 확인 (여러 번 시도)
            login_success = False
            for attempt in range(3):
                time.sleep(2)  # 페이지 로딩 대기
                if self.check_login():
                    login_success = True
                    break
                logger.info(f"로그인 확인 재시도 {attempt + 1}/3")
            
            if not login_success:
                logger.error("로그인 실패")
                # 현재 페이지 정보 출력 (디버깅용)
                try:
                    logger.error(f"현재 URL: {self.driver.current_url}")
                    logger.error(f"페이지 제목: {self.driver.title}")
                except:
                    pass
                raise Exception("로그인에 실패했습니다.")
            logger.info("로그인 성공")
            
            self.go_search()
            self.check_result()
            
            if self.is_booked:
                logger.info("예약 프로세스 완료")
            else:
                logger.warning("예약을 완료하지 못했습니다.")
                
        except Exception as e:
            if _is_browser_session_lost(e):
                logger.warning("브라우저 크래시 가능성. 자동 복구 시도...")
                try:
                    BrowserRecovery.recover(
                        driver=self.driver,
                        srt_instance=self,
                        context=self.recovery_context,
                    )
                    self.check_result()
                    return
                except RecoveryError as recovery_err:
                    logger.error(f"브라우저 복구 실패: {recovery_err}")
                    raise RuntimeError(
                        "브라우저 연결이 끊어졌습니다. Chrome을 중간에 닫으셨거나 연결이 끊어진 것 같습니다. 다시 실행해 주세요."
                    ) from e
            else:
                logger.error(f"예약 프로세스 중 오류 발생: {e}")
            raise
        finally:
            # 예약 완료 후에도 브라우저를 유지할지 선택할 수 있도록 주석 처리
            # 필요시 주석을 해제하여 브라우저를 자동으로 닫을 수 있습니다
            # self.close_driver()
            pass

