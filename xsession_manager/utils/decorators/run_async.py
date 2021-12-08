import multiprocessing


def run_async(func):
    
    def wrapper(*args, **kwargs):
        
        processing = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        processing.start()
        return processing
    return wrapper
