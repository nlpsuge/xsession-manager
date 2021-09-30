# See also: https://linux.die.net/man/1/wmctrl

from ..utils.base import Base


class XSessionConfig(Base):
    session_name: str
    session_create_time: str
    backup_time: str
    restore_times: list = []
    x_session_config_objects: list


class XSessionConfigObject(Base):

    class WindowState(Base):
        # If always on visible workspace
        is_sticky: bool
        # If always on top
        is_above: bool

    class WindowPosition(Base):
        provider: str
        x_offset: int
        y_offset: int
        width: int
        height: int

    window_id: str  # hexadecimal
    window_id_the_int_type: int
    desktop_number: int
    pid: int
    window_position: WindowPosition
    client_machine_name: str
    window_title: str

    app_name: str
    cmd: list
    process_create_time: str

    window_state: WindowState

    @staticmethod
    def convert_wmctl_result_2_list(windows_list: list, remove_duplicates_by_pid=True) -> XSessionConfig:
        session_details = []
        for window in windows_list:
            config = XSessionConfigObject()
            # Use hex type window id if closing via wmctl
            config.window_id = window[0]
            # Use int type window id if closing via Wnck
            config.window_id_the_int_type = int(window[0], 16)
            config.desktop_number = int(window[1])
            config.pid = int(window[2])
            config.client_machine_name = window[7]
            # The title will be empty in some case.
            # For instance:
            # Open a non-existence.docx file using LibreOffice, a 'non-existence.docx does not exist.'
            # dialog popups. This dialog has no title in the result of 'wmctl -lpG'.
            config.window_title = window[8] if len(window) >= 9 else ''

            session_details.append(config)

        x_session_config = XSessionConfig()

        if remove_duplicates_by_pid:
            session_details_dict = {x_session_config.pid: x_session_config
                                    for x_session_config in session_details}
            x_session_config.x_session_config_objects = list(session_details_dict.values())
            return x_session_config

        x_session_config.x_session_config_objects = session_details
        return x_session_config




