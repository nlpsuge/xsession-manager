

class MoreThanOneResultFound(BaseException):

    def __init__(self, reason: str):
        super(MoreThanOneResultFound).__init__()
        self.reason: str = reason

