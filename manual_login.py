#!/usr/bin/env python3
"""수동 로그인 후 자동 예약 스크립트"""

import sys
import time
from srt_reservation.main import SRT
from srt_reservation.util import parse_cli_args

if __name__ == "__main__":
    cli_args = parse_cli_args()

    # 필수 인자 확인
    required_args = {
        'dpt': cli_args.dpt,
        'arr': cli_args.arr,
        'dt': cli_args.dt,
        'tm': cli_args.tm
    }

    missing_args = [arg for arg, value in required_args.items() if value is None]
    if missing_args:
        print(f"에러: 필수 인자가 누락되었습니다: {', '.join(missing_args)}")
        sys.exit(1)

    dpt_stn = cli_args.dpt
    arr_stn = cli_args.arr
    dpt_dt = cli_args.dt
    dpt_tm = cli_args.tm
    num_trains_to_check = cli_args.num
    want_reserve = cli_args.reserve
    anti_bot_method = getattr(cli_args, 'anti_bot', 'stealth')
    retry_delay_min = getattr(cli_args, 'delay_min', 150)  # 더 긴 대기
    retry_delay_max = getattr(cli_args, 'delay_max', 300)

    # 수동 로그인 모드에서는 프로필을 사용하지 않음 (충돌 방지)
    use_profile = False
    profile_dir = None

    print("\n⚠️  주의: 수동 로그인 모드에서는 Chrome 프로필을 사용하지 않습니다.")

    try:
        print("=" * 60)
        print("수동 로그인 모드")
        print("=" * 60)

        srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm,
                  num_trains_to_check, want_reserve,
                  anti_bot_method, retry_delay_min, retry_delay_max,
                  use_profile, profile_dir)

        # 드라이버 시작
        srt.run_driver()

        print("\n1. Chrome 창이 열렸습니다.")
        print("2. 수동으로 SRT 사이트에 로그인하세요:")
        print("   https://etk.srail.co.kr/cmc/01/selectLoginForm.do")
        print("\n3. 로그인 완료 후 이 터미널로 돌아와서 Enter를 누르세요...")

        # SRT 로그인 페이지로 이동
        srt.driver.get('https://etk.srail.co.kr/cmc/01/selectLoginForm.do')

        # 사용자가 수동으로 로그인할 때까지 대기
        input("\n로그인 완료 후 Enter를 누르세요 >>> ")

        print("\n로그인 확인 중...")
        time.sleep(2)

        # 로그인 확인
        if srt.check_login():
            print("✓ 로그인 확인 완료!")
            print("\n자동 예약을 시작합니다...")

            # 검색 및 예약
            srt.go_search()
            srt.check_result()

            if srt.is_booked:
                print("\n" + "=" * 60)
                print("✓ 예약 성공!")
                print("=" * 60)
            else:
                print("\n예약을 완료하지 못했습니다.")
        else:
            print("✗ 로그인이 확인되지 않았습니다. 다시 시도해주세요.")

    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n에러 발생: {e}")
        sys.exit(1)
