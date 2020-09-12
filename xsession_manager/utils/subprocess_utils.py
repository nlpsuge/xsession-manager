import subprocess


def run_cmd(commandline: list):
    # return subprocess.getstatusoutput(commandline)
    # Run cmd as a daemonic one
    return subprocess.Popen(commandline)
