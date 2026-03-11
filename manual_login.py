#!/usr/bin/env python3
"""수동 로그인 후 자동 예약 스크립트"""

import sys
import time
from srt_reservation.config import Config
from srt_reservation.main import SRT
from srt_reservation.util import parse_cli_args

if __name__ == "__main__":
    args = parse_cli_args()

    # Config 폴백 체인: CLI > ENV > DEFAULTS
    # 수동 로그인 모드: user/psw는 필수가 아님
    env_config = Config.load_from_env()
    cli_config = Config.load_from_cli(args)
    config = Config.merge(cli_config, env_config)

    # 수동 로그인 모드 필수값 검증 (user/psw 제외)
    required_keys = ['dpt', 'arr', 'dt', 'tm']
    missing = [k for k in required_keys if k not in config or config[k] is None]
    if missing:
        print(f"에러: 필수 인자가 누락되었습니다: {', '.join(missing)}")
        sys.exit(1)

    # 수동 로그인 모드에서는 프로필 사용 안 함 (충돌 방지)
    config['use_profile'] = False
    config['profile_dir'] = None

    print("\n⚠️  주의: 수동 로그인 모드에서는 Chrome 프로필을 사용하지 않습니다.")

    try:
        print("=" * 60)
        print("수동 로그인 모드")
        print("=" * 60)

        srt = SRT(
            config['dpt'],
            config['arr'],
            config['dt'],
            config['tm'],
            config['num'],
            config['reserve'],
            config['anti_bot'],
            config['delay_min'],
            config['delay_max'],
            config['use_profile'],
            config['profile_dir'],
        )

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
