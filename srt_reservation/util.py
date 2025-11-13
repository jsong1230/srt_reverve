import argparse

def str_to_bool(value):
    """문자열을 boolean으로 변환하는 헬퍼 함수"""
    if isinstance(value, bool):
        return value
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError(f'Boolean value expected, got: {value}')

def parse_cli_args():

    parser = argparse.ArgumentParser(description='')

    parser.add_argument("--user", help="Username", type=str, metavar="1234567890")
    parser.add_argument("--psw", help="Password", type=str, metavar="abc1234")
    parser.add_argument("--dpt", help="Departure Station", type=str, metavar="동탄")
    parser.add_argument("--arr", help="Arrival Station", type=str, metavar="동대구")
    parser.add_argument("--dt", help="Departure Date", type=str, metavar="20220118")
    parser.add_argument("--tm", help="Departure Time", type=str, metavar="08, 10, 12, ...")

    parser.add_argument("--num", help="no of trains to check", type=int, metavar="2", default=2)
    parser.add_argument("--reserve", help="Reserve or not (True/False)", type=str_to_bool, metavar="True/False", default=False)

    args = parser.parse_args()

    return args
