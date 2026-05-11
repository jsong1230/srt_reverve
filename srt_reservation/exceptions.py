class InvalidStationNameError(Exception):
    pass

class InvalidDateFormatError(Exception):
    pass

class InvalidDateError(Exception):
    pass

class InvalidTimeFormatError(Exception):
    pass


class BlockedByServerError(Exception):
    """SRT 서버가 매크로/자동화 트래픽으로 판정하여 IP 접속을 차단한 상태.

    검색 결과 페이지가 "접속 제한 안내" 페이지로 치환되었을 때 발생.
    이 예외가 발생하면 즉시 모든 새로고침을 중단해야 하며, 그렇지 않으면
    SR 회원 자격에 영향을 줄 수 있다.
    """

    def __init__(self, message: str = "", request_id: str = "", matched_signatures=None):
        super().__init__(message or "SRT 서버가 IP 접속을 차단했습니다")
        self.request_id = request_id
        self.matched_signatures = matched_signatures or []

