import json
import os

__all__ = ["read_json", "write_json", "read_utf8_json", "write_utf8_json"]


def read_json(file: str):
    """
    simple json reader
    """
    with open(file) as f:
        return json.load(f)


def read_utf8_json(file: str):
    """
    Read a JSON file encoded in UTF-8.

    Args:
        file (str): The path to the JSON file to read.

    Returns:
        dict: The deserialized JSON data.
    """
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file: str, data):
    """
    simple json writer
    """
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


def write_utf8_json(file: str, data):
    """
    Write a JSON file encoded in UTF-8.

    Args:
        file (str): The path to the JSON file to write.
        data (dict): The data to serialize as JSON.
    """
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def touch_json(file: str, default: str = "{}"):
    """
    quickly touches a json file
    """
    if os.path.exists(file):
        return
    with open(file, "w") as f:
        f.write(default)
