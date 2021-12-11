from ..xsession_manager import XSessionManager


def test_get_session_details():
    session_details = XSessionManager().get_session_details()
    print(session_details)

