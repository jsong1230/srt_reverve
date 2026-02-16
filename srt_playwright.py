#!/usr/bin/env python3
"""Playwright 기반 SRT 자동 예약 (Selenium보다 탐지 어려움)"""

import sys
import time
import argparse
from random import randint, uniform
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def parse_args():
    parser = argparse.ArgumentParser(description='Playwright SRT 예약')
    parser.add_argument("--user", required=True, help="회원번호")
    parser.add_argument("--psw", required=True, help="비밀번호")
    parser.add_argument("--dpt", required=True, help="출발역")
    parser.add_argument("--arr", required=True, help="도착역")
    parser.add_argument("--dt", required=True, help="날짜 (YYYYMMDD)")
    parser.add_argument("--tm", required=True, help="시간 (HH)")
    parser.add_argument("--num", type=int, default=10, help="확인할 기차 수")
    return parser.parse_args()

def human_delay(min_sec=0.5, max_sec=2.0):
    """인간처럼 대기"""
    time.sleep(uniform(min_sec, max_sec))

def human_type(page, selector, text):
    """인간처럼 타이핑"""
    element = page.locator(selector)
    element.click()
    for char in text:
        element.type(char, delay=uniform(50, 150))
    human_delay(0.3, 0.7)

def main():
    args = parse_args()

    print("=" * 60)
    print("Playwright SRT 자동 예약 (탐지 우회 강화)")
    print("=" * 60)

    with sync_playwright() as p:
        # Chromium 실행 (headless=False로 창 표시)
        print("\n브라우저 시작 중...")
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--start-maximized',
            ]
        )

        # 컨텍스트 생성 (User-Agent 등 설정)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
        )

        # navigator.webdriver 제거
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
        """)

        page = context.new_page()

        try:
            # 1. 로그인
            print("\n1. 로그인 페이지 이동...")
            page.goto('https://etk.srail.co.kr/cmc/01/selectLoginForm.do', timeout=60000)
            human_delay(2, 3)

            print("2. 로그인 정보 입력...")
            human_type(page, '#srchDvNm01', args.user)
            human_type(page, '#hmpgPwdCphd01', args.psw)

            print("3. 로그인 버튼 클릭...")
            page.click('input.loginSubmit[type="submit"]')
            human_delay(3, 5)

            # 로그인 확인
            try:
                page.wait_for_selector('#wrap > div.header.header-e > div.global.clear > div', timeout=10000)
                print("✓ 로그인 성공!")
            except:
                print("✗ 로그인 실패 - 계속 진행...")

            # 2. 기차 검색
            print("\n4. 기차 조회 페이지 이동...")
            page.goto('https://etk.srail.co.kr/hpg/hra/01/selectScheduleList.do', timeout=60000)
            human_delay(2, 3)

            print(f"5. 검색 조건 입력 ({args.dpt} → {args.arr}, {args.dt}, {args.tm}시)...")

            # 출발역
            page.fill('#dptRsStnCdNm', args.dpt)
            human_delay(0.3, 0.7)

            # 도착역
            page.fill('#arvRsStnCdNm', args.arr)
            human_delay(0.3, 0.7)

            # 날짜
            page.evaluate(f"document.getElementById('dptDt').style.display = 'block';")
            page.select_option('#dptDt', args.dt)
            human_delay(0.3, 0.7)

            # 시간
            page.evaluate(f"document.getElementById('dptTm').style.display = 'block';")
            page.select_option('#dptTm', label=args.tm)
            human_delay(0.5, 1.0)

            print("6. 조회 버튼 클릭...")
            page.click('input[value="조회하기"]')
            human_delay(2, 3)

            # 3. 예약 가능한 기차 찾기
            print(f"\n7. 예약 가능한 기차 찾기 시작 (상위 {args.num}개 확인)...")
            cnt_refresh = 0

            while True:
                found = False

                for i in range(1, args.num + 1):
                    try:
                        # 일반석 상태 확인
                        selector = f'#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7)'
                        seat_text = page.text_content(selector, timeout=5000)

                        if "예약하기" in seat_text:
                            print(f"\n✓ {i}번째 기차 예약 가능! 예약 시도 중...")

                            # 예약 버튼 클릭
                            page.click(f'#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a')
                            human_delay(2, 3)

                            # 예약 성공 확인
                            if page.locator('#isFalseGotoMain').count() > 0:
                                print("\n" + "=" * 60)
                                print("🎉 예약 성공!")
                                print("=" * 60)
                                found = True
                                break
                            else:
                                print("✗ 잔여석 없음, 뒤로가기...")
                                page.go_back()
                                human_delay(2, 3)

                    except Exception as e:
                        print(f"  {i}번째 기차 확인 중 오류 (무시): {e}")
                        continue

                if found:
                    break

                # 새로고침
                cnt_refresh += 1
                delay = randint(150, 300)
                print(f"\n새로고침 {cnt_refresh}회 (다음 시도까지 {delay}초 대기...)")
                time.sleep(delay)

                page.click('input[value="조회하기"]')
                human_delay(2, 3)

            # 완료 후 대기
            print("\n브라우저 창을 수동으로 닫으세요.")
            input("종료하려면 Enter를 누르세요...")

        except KeyboardInterrupt:
            print("\n\n사용자가 중단했습니다.")
        except Exception as e:
            print(f"\n에러 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == "__main__":
    main()
