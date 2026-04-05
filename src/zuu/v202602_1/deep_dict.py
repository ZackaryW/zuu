from collections.abc import Iterable, Mapping
from typing import Any


DeepPath = str | Iterable[str]


def _normalize_path(path: DeepPath) -> tuple[str, ...]:
	if isinstance(path, str):
		parts = tuple(part for part in path.split(".") if part)
	else:
		parts = tuple(path)

	if not parts:
		raise ValueError("Path must contain at least one key.")

	return parts


class DeepDict:
	@staticmethod
	def deepGet(data: dict[str, Any], path: DeepPath, default: Any = None) -> Any:
		current: Any = data

		for part in _normalize_path(path):
			if not isinstance(current, dict) or part not in current:
				return default
			current = current[part]

		return current

	@staticmethod
	def deepSet(data: dict[str, Any], path: DeepPath, value: Any) -> dict[str, Any]:
		parts = _normalize_path(path)
		current = data

		for part in parts[:-1]:
			next_value = current.get(part)
			if not isinstance(next_value, dict):
				next_value = {}
				current[part] = next_value
			current = next_value

		current[parts[-1]] = value
		return data

	@staticmethod
	def deepDelete(data: dict[str, Any], path: DeepPath) -> bool:
		parts = _normalize_path(path)
		current: Any = data

		for part in parts[:-1]:
			if not isinstance(current, dict) or part not in current:
				return False
			current = current[part]

		if not isinstance(current, dict) or parts[-1] not in current:
			return False

		del current[parts[-1]]
		return True

	@staticmethod
	def deepUpdate(data: dict[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
		for key, value in updates.items():
			current_value = data.get(key)
			if isinstance(current_value, dict) and isinstance(value, Mapping):
				DeepDict.deepUpdate(current_value, value)
				continue

			if isinstance(value, Mapping):
				data[key] = dict(value)
				continue

			data[key] = value

		return data


class DeepDictWrapper:
	def __init__(self, data: dict[str, Any]):
		self.data = data

	def deepGet(self, path: DeepPath, default: Any = None) -> Any:
		return DeepDict.deepGet(self.data, path, default)

	def deepSet(self, path: DeepPath, value: Any) -> dict[str, Any]:
		return DeepDict.deepSet(self.data, path, value)

	def deepDelete(self, path: DeepPath) -> bool:
		return DeepDict.deepDelete(self.data, path)

	def deepUpdate(self, updates: Mapping[str, Any]) -> dict[str, Any]:
		return DeepDict.deepUpdate(self.data, updates)
