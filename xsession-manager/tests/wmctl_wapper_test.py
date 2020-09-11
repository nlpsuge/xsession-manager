from utils import wmctl_wrapper


def test_get_windows():
    lines = wmctl_wrapper.get_running_windows()
    print(lines)
    print()
    for line in lines:
        print(line)



