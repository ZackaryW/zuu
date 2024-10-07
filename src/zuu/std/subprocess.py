import json
import subprocess
import platform

__all__ = [
    "open_detached",
    "check_is_installed",
    "query_bytes",
    "query_string",
    "query_json",
]


def open_detached(path: str, *args) -> subprocess.Popen:
    """
    Opens a new process in a detached state.

    Args:
        path (str): The path to the executable file.
        *args: Additional arguments to be passed to the executable.

    Returns:
        None: This function does not return anything.

    Description:
        This function uses the `subprocess.Popen` method to create a new process
        and execute the specified executable file with the given arguments. The
        process is created in a detached state, meaning it runs independently
        of the parent process. The standard input, output, and error streams of
        the process are set to be pipes. The `creationflags` parameter is used
        to specify the creation flags for the process, including `DETACHED_PROCESS`,
        `CREATE_NEW_PROCESS_GROUP`, and `CREATE_BREAKAWAY_FROM_JOB`.

    Example:
        ```python
        open_detached("path/to/executable", "arg1", "arg2")
        ```
    """
    return subprocess.Popen(
        [path, *(str(arg) for arg in args)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=(
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_BREAKAWAY_FROM_JOB
        ),
    )


def check_is_installed(app_name: str) -> bool:
    """
    Check if an application is installed on the operating system.

    Args:
        app_name (str): The name of the application to check.

    Returns:
        bool: True if the application is installed, False otherwise.

    This function checks if an application is installed on the operating system by using the appropriate command for the operating system.

    On Windows, it uses the 'where' command to check for the app existence.

    On macOS, it uses the 'type' command or 'which' command to check for the app existence.

    On Linux, it uses the 'which' command to check for the app existence.

    If the command succeeds, the application is considered installed and the function returns True.

    If the command fails, the application is considered not installed and the function returns False.

    If the operating system is not Windows, macOS, or Linux, the function returns False.
    """

    os_type = platform.system()

    try:
        if os_type == "Windows":
            # On Windows, use 'where' command to check for the app existence
            subprocess.check_call(
                ["where", app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif os_type == "Darwin":
            # On macOS, use 'type' command or 'which'
            subprocess.check_call(
                ["type", app_name],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif os_type == "Linux":
            # On Linux, use 'which' command
            subprocess.check_call(
                ["which", app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            return False
    except subprocess.CalledProcessError:
        # The command failed, the application is not installed
        return False

    # The command succeeded, the application is installed
    return True


DEFAULT_QUERY_TIMEOUT = 5


def query_bytes(
    path: str,
    *args,
    timeout: int = None,
):
    """
    Executes a subprocess and returns the captured output as bytes.

    Args:
        path (str): The path to the executable to run.
        *args: Additional arguments to pass to the executable.
        timeout (int, optional): The maximum time in seconds to wait for the subprocess to complete. If not provided, the `DEFAULT_QUERY_TIMEOUT` value will be used.

    Raises:
        subprocess.TimeoutExpired: If the subprocess takes longer than the specified timeout to complete.
        subprocess.CalledProcessError: If the subprocess returns a non-zero exit code.

    Returns:
        bytes: The captured output of the subprocess.
    """
    timeout = timeout or DEFAULT_QUERY_TIMEOUT
    try:
        command = [path, *(str(arg) for arg in args)]
        proc = subprocess.run(command, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise e
    except subprocess.CalledProcessError as e:
        raise e

    return proc.stdout


def query_string(path: str, *args, timeout: int = None, strip: bool = False):
    """
    Executes a subprocess and returns the captured output as a string.

    Args:
        path (str): The path to the executable to run.
        *args: Additional arguments to pass to the executable.
        timeout (int, optional): The maximum time in seconds to wait for the subprocess to complete. If not provided, the `DEFAULT_QUERY_TIMEOUT` value will be used.

    Raises:
        subprocess.TimeoutExpired: If the subprocess takes longer than the specified timeout to complete.
        subprocess.CalledProcessError: If the subprocess returns a non-zero exit code.

    Returns:
        str: The captured output of the subprocess as a string.
    """
    raw = query_bytes(path, *args, timeout=timeout)
    return raw.decode("utf-8").strip() if strip else raw.decode("utf-8")


def query_json(
    path: str,
    *args,
    timeout: int = None,
):
    """
    Executes a subprocess, parses the captured output as JSON, and returns the parsed data.

    Args:
        path (str): The path to the executable to run.
        *args: Additional arguments to pass to the executable.
        timeout (int, optional): The maximum time in seconds to wait for the subprocess to complete. If not provided, the `DEFAULT_QUERY_TIMEOUT` value will be used.

    Raises:
        subprocess.TimeoutExpired: If the subprocess takes longer than the specified timeout to complete.
        subprocess.CalledProcessError: If the subprocess returns a non-zero exit code.
        json.JSONDecodeError: If the captured output cannot be parsed as valid JSON.

    Returns:
        dict: The parsed JSON data from the subprocess output.
    """
    return json.loads(query_string(path, *args, timeout=timeout))
