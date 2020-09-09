# See also: https://linux.die.net/man/1/wmctrl

from utils.base import Base


class XSessionConfigObject(Base):

    class WindowPosition(Base):
        x_offset: int
        y_offset: int
        width: int
        height: int

    window_id: str
    desktop_number: int
    pid: int
    window_position: WindowPosition
    client_machine_name: str
    window_title: str

    app_name: str
    cmd: list
    create_time: str

    @staticmethod
    def convert_wmctl_result_2_list(windows_list: list, remove_duplicates_by_pid=True):
        session_details = []
        for window in windows_list:
            config = XSessionConfigObject()
            config.window_id = window[0]
            config.desktop_number = window[1]
            config.pid = int(window[2])
            window_position = config.WindowPosition()
            window_position.x_offset = window[3]
            window_position.y_offset = window[4]
            window_position.width = window[5]
            window_position.height = window[6]
            config.window_position = window_position
            config.client_machine_name = window[7]
            config.window_title = window[8]

            session_details.append(config)

        if remove_duplicates_by_pid:
            session_details_dict = {x_session_config.pid: x_session_config
                                    for x_session_config in session_details}
            return list(session_details_dict.values())

        return session_details




