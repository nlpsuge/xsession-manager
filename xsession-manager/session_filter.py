from settings.xsession_config import XSessionConfigObject


class SessionFilter:

    def __call__(self, session: XSessionConfigObject):
        return False
