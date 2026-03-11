""" Quickstart script for SRT reservation """

# imports
import sys
from srt_reservation.config import Config
from srt_reservation.main import SRT
from srt_reservation.util import parse_cli_args


if __name__ == "__main__":
    args = parse_cli_args()

    # Config 폴백 체인: CLI > ENV > DEFAULTS
    env_config = Config.load_from_env()
    cli_config = Config.load_from_cli(args)
    config = Config.merge(cli_config, env_config)

    # 필수값 검증
    try:
        Config.validate_required(config)
    except ValueError as e:
        print(f"에러: {e}")
        sys.exit(1)

    try:
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
        srt.run(config['user'], config['psw'])
    except Exception as e:
        print(f"에러 발생: {e}")
        sys.exit(1)
