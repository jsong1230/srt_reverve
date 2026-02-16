#!/usr/bin/env python3
"""브라우저 기본 동작 테스트"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

print("=" * 50)
print("브라우저 테스트 시작")
print("=" * 50)

# Chrome 옵션
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("detach", True)

print("\n1. ChromeDriver 초기화 중...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

print(f"✓ ChromeDriver 초기화 완료")
print(f"✓ 현재 URL: {driver.current_url}")

print("\n2. Google 접속 테스트...")
driver.get("https://www.google.com")
time.sleep(2)
print(f"✓ Google 접속 성공")
print(f"✓ 페이지 제목: {driver.title}")

print("\n3. SRT 사이트 접속 테스트...")
driver.get("https://etk.srail.co.kr/")
time.sleep(3)
print(f"✓ SRT 사이트 접속 성공")
print(f"✓ 현재 URL: {driver.current_url}")
print(f"✓ 페이지 제목: {driver.title}")

print("\n4. SRT 로그인 페이지 접속 테스트...")
driver.get("https://etk.srail.co.kr/cmc/01/selectLoginForm.do")
time.sleep(3)
print(f"✓ 로그인 페이지 접속 성공")
print(f"✓ 현재 URL: {driver.current_url}")
print(f"✓ 페이지 제목: {driver.title}")

print("\n" + "=" * 50)
print("테스트 완료!")
print("Chrome 창을 확인하고 수동으로 닫으세요.")
print("=" * 50)

# 브라우저는 자동으로 닫히지 않음 (detach=True)
