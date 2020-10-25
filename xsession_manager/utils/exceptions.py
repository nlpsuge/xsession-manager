

class MoreThanOneResultFound(BaseException):

    def __init__(self, reason: str):
        super(self).__init__()
        self.reason: str = reason

