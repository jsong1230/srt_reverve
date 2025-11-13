# -*- coding: utf-8 -*-
import os
import time
import logging
from random import randint
from datetime import datetime
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

from srt_reservation.exceptions import InvalidStationNameError, InvalidDateError, InvalidDateFormatError, InvalidTimeFormatError
from srt_reservation.validation import station_list

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# chromedriver 경로는 환경 변수에서 가져오거나 기본값 사용
chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')

class SRT:
    def __init__(self, dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check=2, want_reserve=False):
        """
        :param dpt_stn: SRT 출발역
        :param arr_stn: SRT 도착역
        :param dpt_dt: 출발 날짜 YYYYMMDD 형태 ex) 20220115
        :param dpt_tm: 출발 시간 hh 형태, 반드시 짝수 ex) 06, 08, 14, ...
        :param num_trains_to_check: 검색 결과 중 예약 가능 여부 확인할 기차의 수 ex) 2일 경우 상위 2개 확인
        :param want_reserve: 예약 대기가 가능할 경우 선택 여부
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

        self.check_input()

    def check_input(self):
        if self.dpt_stn not in station_list:
            raise InvalidStationNameError(f"출발역 오류. '{self.dpt_stn}' 은/는 목록에 없습니다.")
        if self.arr_stn not in station_list:
            raise InvalidStationNameError(f"도착역 오류. '{self.arr_stn}' 은/는 목록에 없습니다.")
        if self.dpt_stn == self.arr_stn:
            raise InvalidStationNameError("출발역과 도착역이 같을 수 없습니다.")
        if not str(self.dpt_dt).isnumeric():
            raise InvalidDateFormatError("날짜는 숫자로만 이루어져야 합니다.")
        try:
            datetime.strptime(str(self.dpt_dt), '%Y%m%d')
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

    def run_driver(self):
        """Chrome WebDriver 초기화"""
        try:
            # Service 객체를 사용하여 ChromeDriver 초기화
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service)
            logger.info(f"ChromeDriver를 {chromedriver_path}에서 로드했습니다.")
        except (WebDriverException, FileNotFoundError) as e:
            # WebDriverException 발생 시, WebDriver Manager로 드라이버 설치
            logger.warning(f"기본 경로에서 ChromeDriver를 찾을 수 없습니다: {e}")
            logger.info("WebDriver Manager를 사용하여 ChromeDriver를 설치합니다.")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service)
            logger.info("ChromeDriver 설치 완료")
    
    def close_driver(self):
        """WebDriver 리소스 정리"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver가 정상적으로 종료되었습니다.")
            except Exception as e:
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
        """SRT 로그인"""
        try:
            self.driver.get('https://etk.srail.co.kr/cmc/01/selectLoginForm.do')
        except UnexpectedAlertPresentException:
            self.handle_alert()
            # Alert 처리 후 다시 시도
            self.driver.get('https://etk.srail.co.kr/cmc/01/selectLoginForm.do')

        self.driver.implicitly_wait(15)
        try:
            self.driver.find_element(By.ID, 'srchDvNm01').send_keys(str(self.login_id))
            self.driver.find_element(By.ID, 'hmpgPwdCphd01').send_keys(str(self.login_psw))
            self.driver.find_element(By.XPATH, '//*[@id="login-form"]/fieldset/div[1]/div[1]/div[2]/div/div[2]/input').click()
            self.driver.implicitly_wait(5)
            logger.info("로그인 시도 완료")
        except Exception as e:
            logger.error(f"로그인 중 오류 발생: {e}")
            raise
        return self.driver

    def check_login(self):
        menu_text = self.driver.find_element(By.CSS_SELECTOR, "#wrap > div.header.header-e > div.global.clear > div").text
        if "환영합니다" in menu_text:
            return True
        else:
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
        elm_dpt_dt = self.driver.find_element(By.ID, "dptDt")
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_dt)
        Select(self.driver.find_element(By.ID, "dptDt")).select_by_value(self.dpt_dt)

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

    def check_result(self):
        """검색 결과 확인 및 예약 시도"""
        max_refresh = 1000  # 무한 루프 방지
        while self.cnt_refresh < max_refresh:
            for i in range(1, self.num_trains_to_check+1):
                try:
                    standard_seat = self.driver.find_element(By.CSS_SELECTOR, f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7)").text
                    reservation = self.driver.find_element(By.CSS_SELECTOR, f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(8)").text
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

            if self.is_booked:
                return self.driver

            else:
                time.sleep(randint(2, 4))
                self.refresh_result()
        
        logger.warning(f"최대 새로고침 횟수({max_refresh}회)에 도달했습니다.")
        return self.driver

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
            
            # 로그인 확인
            if not self.check_login():
                logger.error("로그인 실패")
                raise Exception("로그인에 실패했습니다.")
            logger.info("로그인 성공")
            
            self.go_search()
            self.check_result()
            
            if self.is_booked:
                logger.info("예약 프로세스 완료")
            else:
                logger.warning("예약을 완료하지 못했습니다.")
                
        except Exception as e:
            logger.error(f"예약 프로세스 중 오류 발생: {e}")
            raise
        finally:
            # 예약 완료 후에도 브라우저를 유지할지 선택할 수 있도록 주석 처리
            # 필요시 주석을 해제하여 브라우저를 자동으로 닫을 수 있습니다
            # self.close_driver()
            pass

