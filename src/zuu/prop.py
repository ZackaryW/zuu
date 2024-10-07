import time
from functools import wraps


def timely_property(expiration_seconds):
    """
    A decorator that creates a property that caches the result of a function call for a specified expiration time.

    The `timely_property` decorator takes an `expiration_seconds` argument, which specifies the number of seconds to cache the result of the decorated function. If `expiration_seconds` is 0, the cache is disabled and the function is called every time the property is accessed.

    When the property is accessed, the decorator checks if the cached value is still valid (i.e., the expiration time has not been reached). If the cached value is valid, it is returned. Otherwise, the function is called, the result is cached, and the new value is returned.

    The decorator uses private attributes on the object to store the cached value and the timestamp of the last update. These attributes are named `__<function_name>_value` and `__<function_name>_timestamp`, respectively.

    The `timely_property` decorator can be used on any instance method of a class.
    """
    if expiration_seconds < 0:
        raise ValueError("expiration_seconds must be greater than 0")

    def decorator(func):
        @wraps(func)
        def wrapper(self):
            if not hasattr(self, f"__{func.__name__}_value"):
                setattr(self, f"__{func.__name__}_value", None)
                setattr(self, f"__{func.__name__}_timestamp", 0)

            current_time = time.time()
            if (
                expiration_seconds == 0
                or current_time - getattr(self, f"__{func.__name__}_timestamp")
                >= expiration_seconds
            ):
                value = func(self)
                setattr(self, f"__{func.__name__}_value", value)
                setattr(self, f"__{func.__name__}_timestamp", current_time)

            return getattr(self, f"__{func.__name__}_value")

        return property(wrapper)

    return decorator


class TimelyClsProperty:
    """
    A class that provides a class-level property that caches the result of a function call for a specified expiration time.

    The `TimelyClsProperty` class is a descriptor that can be used to create a class-level property. When the property is accessed, the descriptor checks if the cached value is still valid (i.e., the expiration time has not been reached). If the cached value is valid, it is returned. Otherwise, the function is called, the result is cached, and the new value is returned.

    The class uses a dictionary `self.cache` to store the cached values, where the key is the class object and the value is a dictionary containing the cached value and the expiration time.

    """

    def __init__(self, func, expiration_seconds):
        self.func = func
        self.expiration_seconds = expiration_seconds
        self.cache = {}

    def __get__(self, instance, owner):
        current_time = time.time()
        cache_entry = self.cache.get(owner)

        if cache_entry and (current_time < cache_entry["expire_time"]):
            return cache_entry["value"]

        value = self.func(owner)
        self.cache[owner] = {
            "value": value,
            "expire_time": current_time + self.expiration_seconds,
        }
        return value


def timely_cls_property(expiration_seconds):
    def decorator(func):
        prop = TimelyClsProperty(func, expiration_seconds)
        return prop

    return decorator

# ANCHOR clsprop

class classProperty(object):
    """
    A class that provides a descriptor for defining class-level properties.
    """

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self
