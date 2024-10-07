class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


singleton_creation_string = """
class AbsoluteSingleton(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AbsoluteSingleton, cls).__call__(*args, **kwargs)
        return cls._instance
"""


def absoluteSingleton():
    local = {}
    exec(singleton_creation_string, local)
    return local["AbsoluteSingleton"]
