import multiprocessing


class Decorators:
    
    def __init__(self):
        pass
    
    def run_async(self, func):
        def wrapper(*args, **kwargs):
            p1 = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
            p1.start()
        return wrapper

