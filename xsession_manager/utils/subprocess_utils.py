import subprocess


def run_cmd(commandline: list):
    # return subprocess.getstatusoutput(commandline)
    # Run cmd as a daemonic one
    # Ignore standard output and standard error
    # subprocess.DEVNULL only support > 3.3
    return subprocess.Popen(commandline, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

