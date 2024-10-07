import hashlib

import os
import typing

__all__ = ["hash_file", "hash_bytes", "hash_folder", "hash_python_directory"]


def hash_file(
    path: str,
    algorithm: str = "sha256",
    chunk_size: int = 65536,
    normalize_newline: bool = True,
) -> str:
    """
    Computes the hash value of a file.

    Args:
        path (str): The path to the file.
        algorithm (str): The hashing algorithm to use. Defaults to "sha256".
        chunk_size (int): The size of the chunks used to read the file. Defaults to 65536.

    Returns:
        str: The computed hash value of the file.
    """
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            if normalize_newline:
                chunk = chunk.replace(b"\r\n", b"\n")
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_bytes(
    data: bytes, algorithm: str = "sha256", normalize_newline: bool = True
) -> str:
    """
    Computes the hash value of a given byte string using the specified algorithm.

    Args:
        data (bytes): The byte string to be hashed.
        algorithm (str, optional): The hashing algorithm to use. Defaults to "sha256".

    Returns:
        str: The computed hash value of the byte string in hexadecimal format.
    """
    if normalize_newline:
        data = data.replace(b"\r\n", b"\n")
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def hash_folder(
    *files: typing.List[str],
    algorithm: str = "sha256",
    chunk_size: int = 65536,
    normalize_newline: bool = True,
) -> str:
    """
    Computes the hash value of the contents of the specified files using the given hashing algorithm.

    Args:
        *files (List[str]): The paths to the files to be hashed.
        algorithm (str, optional): The hashing algorithm to use. Defaults to "sha256".
        chunk_size (int, optional): The size of the chunks used to read the files. Defaults to 65536.
        normalize_newline (bool, optional): Whether to normalize newline characters in the file contents. Defaults to True.

    Returns:
        str: The computed hash value of the contents of the specified files.
    """

    hasher = hashlib.new(algorithm)
    for file in files:
        hasher.update(
            hash_file(file, algorithm, chunk_size, normalize_newline).encode("utf-8")
        )
    return hasher.hexdigest()


def hash_python_directory(
    directory: str,
    algorithm: str = "sha256",
    chunk_size: int = 65536,
    normalize_newline: bool = True,
) -> str:
    """
    Computes the hash value of all Python files in a directory using the specified hashing algorithm.

    Args:
        directory (str): The path to the directory containing the Python files.
        algorithm (str, optional): The hashing algorithm to use. Defaults to "sha256".
        chunk_size (int, optional): The size of the chunks used to read the files. Defaults to 65536.
        normalize_newline (bool, optional): Whether to normalize newline characters in the file contents. Defaults to True.

    Returns:
        str: The computed hash value of all Python files in the directory.
    """

    hasher = hashlib.new(algorithm)
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            if "__pycache__" in root:
                continue
            path = os.path.join(root, file)
            hasher.update(
                hash_file(path, algorithm, chunk_size, normalize_newline).encode(
                    "utf-8"
                )
            )
