# encoding: utf-8

import time
import logging  
from functools import wraps    

log = logging.getLogger("apiserver")                                         

class timed(object):
    def __init__(self, callback=None):
        self.callback = callback
        
    def __call__(self, fn):
        @wraps(fn)
        def timed_fn(*vargs, **kwargs):
            start = time.time()
            result = fn(*vargs, **kwargs)
            finish = time.time()
            duration = round(finish-start, 2)
            msg = "Executed {module}.{name} in {time} seconds.".format(
                module=fn.__module__, name=fn.__name__, time=duration)
            if self.callback:
                self.callback(msg)
            else:
                log.info(msg)
            return result

        return timed_fn