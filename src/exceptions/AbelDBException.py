from src.utils.status_enum import StatusEnum


class AbelDBException(Exception):
    def __init__(self, message: str, code: StatusEnum, info=[]) -> None:
        self.name = "AbelDBException"
        self.message = message
        self.code = code
        self.info = info
        super().__init__(self.message)
