import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict
import os

__all__: list[str] = ["import_from_file", "import_folder", "import_file", "import_folder"]

def import_file(file_path: str) -> Any:
    """
    Import a Python file as a module.

    Args:
        file_path (str): The path to the Python file to import.

    Returns:
        Any: The imported module.

    Raises:
        ImportError: If the file cannot be imported.
    """
    file_path = Path(file_path).resolve()
    module_name = file_path.stem

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(
            f"Could not load spec for module {module_name} from {file_path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    if spec.loader is None:
        raise ImportError(f"Could not load module {module_name} from {file_path}")

    spec.loader.exec_module(module)
    return module


def import_from_pkg_path(dotted_path: str, file_path: str) -> Any:
    """
    Import a module from a package using a dotted path and file path.

    Args:
        dotted_path (str): The traversal path within the package (e.g., 'subpackage.module').
        file_path (str): The initial current working directory (root package path).

    Returns:
        Any: The imported module.

    Raises:
        ImportError: If the module cannot be imported.
    """
    root_path = Path(file_path).resolve()
    module_path = root_path.joinpath(*dotted_path.split("."))
    module_file = module_path.with_suffix(".py")

    if not module_file.is_file():
        raise ImportError(f"Module file not found: {module_file}")

    module_name = dotted_path

    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None:
        raise ImportError(
            f"Could not load spec for module {module_name} from {module_file}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    if spec.loader is None:
        raise ImportError(f"Could not load module {module_name} from {module_file}")

    spec.loader.exec_module(module)
    return module


def import_from_file(file_path: str, name: str) -> Any:
    """
    Import a specific object from a Python file.

    Args:
        file_path (str): The path to the Python file to import from.
        name (str): The name of the object to import.

    Returns:
        Any: The imported object.

    Raises:
        ImportError: If the file or object cannot be imported.
        AttributeError: If the specified object is not found in the module.
    """
    module = import_file(file_path)
    try:
        return getattr(module, name)
    except AttributeError:
        raise AttributeError(f"Module {module.__name__} has no attribute '{name}'")

def import_folder(folder_path: str) -> Dict[str, Any]:
    """
    Import all Python modules from a folder and its subfolders.

    Args:
        folder_path (str): The path to the folder to import from.

    Returns:
        Dict[str, Any]: A dictionary with package.subpackage as keys and imported modules as values.
    """
    import_dict = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = os.path.join(root, file)
                module_name = os.path.splitext(file)[0]
                package_path = os.path.relpath(root, folder_path).replace(
                    os.path.sep, "."
                )
                full_module_name = (
                    f"{package_path}.{module_name}"
                    if package_path != "."
                    else module_name
                )
                try:
                    module = import_file(file_path)
                    import_dict[full_module_name] = module
                except ImportError:
                    continue
    return import_dict
