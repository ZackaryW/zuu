class Nothing:
    """
    A class that does nothing.

    This class is used as a placeholder for situations where a placeholder
    object is needed, but where no specific action is required.
    """

    def __getattribute__(self, __name: str):
        if __name.startswith("__"):
            return object.__getattribute__(self, __name)

        return self

    def __call__(self, *args, **kwds):
        return self


NothingInstance = Nothing()
