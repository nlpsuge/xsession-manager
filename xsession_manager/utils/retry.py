from time import sleep


class NeedRetryException(BaseException):
    pass


class Retry:

    retry_num: int
    retry_interval: float

    def __init__(self, retry_num=0, retry_interval=0.5):
        self.retry_num = retry_num
        self.retry_interval = retry_interval

    def do_retry(self, func, args=()):
        for i in range(0, self.retry_num + 1):
            try:
                return func(*args)
            except NeedRetryException:
                # print('Retrying ... (%d/%d)' % ((i + 1), self.retry_num))
                sleep(self.retry_interval)
