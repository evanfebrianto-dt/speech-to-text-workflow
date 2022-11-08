import time

# Create custom decorator to time methods in a class
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print (f'[DEBUG] {method.__name__} method took {te-ts} sec')
        return result
    return timed