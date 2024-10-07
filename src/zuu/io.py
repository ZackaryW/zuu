from .std.json import read_json, write_json


def read_toml(path: str):
    import toml

    return toml.load(path)


def write_toml(path: str, data):
    import toml

    with open(path, "w") as f:
        toml.dump(data, f)


def read_yaml(path: str):
    import yaml

    with open(path, "r") as f:
        return yaml.safe_load(f)


def write_yaml(path: str, data):
    import yaml

    with open(path, "w") as f:
        yaml.dump(data, f)


def read_smart(path: str):
    extension = path.split(".")[-1]
    match extension:
        case "json":
            return read_json(path)
        case "toml":
            import toml

            return toml.load(path)
        case "yaml" | "yml":
            import yaml

            with open(path, "r") as f:
                return yaml.safe_load(f)
        case "pickle":
            import pickle

            with open(path, "rb") as f:
                return pickle.load(f)
        case "csv":
            import csv

            with open(path, "r") as f:
                return list(csv.reader(f))
        case _:
            with open(path, "r") as f:
                return f.read()


def write_smart(path: str, data):
    json_data_type = isinstance(data, dict | list)
    path_has_extension = "." in path
    extension = path.split(".")[-1] if path_has_extension else None

    if extension:
        match extension:
            case "json":
                write_json(path, data)
            case "toml":
                import toml

                with open(path, "w") as f:
                    toml.dump(data, f)
            case "yaml" | "yml":
                import yaml

                with open(path, "w") as f:
                    yaml.safe_dump(data, f)
            case "pickle":
                import pickle

                with open(path, "wb") as f:
                    pickle.dump(data, f)
            case "csv":
                import csv

                with open(path, "w") as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
            case _:
                with open(path, "w") as f:
                    if json_data_type:
                        data = str(data)
                    f.write(data)
        return
    if json_data_type:
        write_json(path, data)
    else:
        with open(path, "w") as f:
            f.write(data)


__all__ = [
    "read_json",
    "write_json",
    "read_toml",
    "write_toml",
    "read_yaml",
    "write_yaml",
    "read_smart",
    "write_smart"
]
