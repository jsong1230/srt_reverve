""" Quickstart script for SRT reservation """

# imports
import sys
from srt_reservation.main import SRT
from srt_reservation.util import parse_cli_args


if __name__ == "__main__":
    cli_args = parse_cli_args()

    # 필수 인자 확인
    required_args = {
        'user': cli_args.user,
        'psw': cli_args.psw,
        'dpt': cli_args.dpt,
        'arr': cli_args.arr,
        'dt': cli_args.dt,
        'tm': cli_args.tm
    }
    
    missing_args = [arg for arg, value in required_args.items() if value is None]
    if missing_args:
        print(f"에러: 필수 인자가 누락되었습니다: {', '.join(missing_args)}")
        print("사용법: python quickstart.py --user USER --psw PASSWORD --dpt 출발역 --arr 도착역 --dt 날짜 --tm 시간")
        sys.exit(1)

    login_id = cli_args.user
    login_psw = cli_args.psw
    dpt_stn = cli_args.dpt
    arr_stn = cli_args.arr
    dpt_dt = cli_args.dt
    dpt_tm = cli_args.tm

    num_trains_to_check = cli_args.num
    want_reserve = cli_args.reserve

    try:
        srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check, want_reserve)
        srt.run(login_id, login_psw)
    except Exception as e:
        print(f"에러 발생: {e}")
        sys.exit(1)