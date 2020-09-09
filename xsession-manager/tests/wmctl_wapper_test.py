from utils import wmctl_wapper


def test_get_windows():
    lines = wmctl_wapper.get_running_windows()
    print(lines)
    print()
    for line in lines:
        print(line)



