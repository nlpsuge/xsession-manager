from typing import List

from .settings.xsession_config import XSessionConfigObject
from .utils.number_utils import is_int, is_hexadecimal


def filter_session(session, includes):
    for include in includes:
        ii, value = is_int(include)
        if ii and value == session.pid:
            return True

        ih, _ = is_hexadecimal(include)
        # Use string type values to compare
        if ih and include == session.window_id:
            return True

        if include.lower() in session.app_name.lower() \
                or include.lower() in session.window_title.lower():
            return True


class SessionFilter:

    def __call__(self,
                 sessions: List[XSessionConfigObject]):
        return sessions


class ExcludeSessionFilter(SessionFilter):

    excludes: list

    def __init__(self, excludes):
        self.excludes = excludes

    def __call__(self, sessions: List[XSessionConfigObject]):
        if self.excludes is None or len(self.excludes) == 0:
            return sessions
        return [session for session in sessions if not filter_session(session, self.excludes)]


class IncludeSessionFilter(SessionFilter):

    includes: list

    def __init__(self, includes):
        self.includes = includes

    def __call__(self, sessions: List[XSessionConfigObject]):
        if self.includes is None or len(self.includes) == 0:
            return sessions
        return [session for session in sessions if filter_session(session, self.includes)]
