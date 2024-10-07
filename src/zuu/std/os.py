import os
import stat
import functools

__all__ = ["has_hidden_attribute", "preserve_cwd"]


def has_hidden_attribute(filepath):
    """
    Check if a file has the hidden attribute.

    Parameters:
        filepath (str): The path to the file.

    Returns:
        bool: True if the file has the hidden attribute, False otherwise.
    """
    return bool(os.stat(filepath).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)


def preserve_cwd(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        original_cwd = os.getcwd()
        try:
            return func(*args, **kwargs)
        finally:
            os.chdir(original_cwd)

    return wrapper
