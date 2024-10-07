import pytest
import json
from zuu.util.onChangeDict import OnChangeSaveDict

class TestOnChangeSaveDict:
    @pytest.fixture
    def temp_file(self, tmp_path):
        file = tmp_path / "test_dict.json"
        return file

    def test_init_with_existing_file(self, temp_file):
        initial_data = {"key1": "value1", "key2": 2}
        with open(temp_file, 'w') as f:
            json.dump(initial_data, f)
        
        sio_dict = OnChangeSaveDict(temp_file)
        assert sio_dict == initial_data

    def test_setitem_simple_value(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        sio_dict["new_key"] = "new_value"
        assert sio_dict["new_key"] == "new_value"
        
        with open(temp_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == {"new_key": "new_value"}

    def test_setitem_nested_dict_raises_error(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        with pytest.raises(ValueError, match="Nested dictionaries are not allowed"):
            sio_dict["nested"] = {"key": "value"}

    def test_setitem_nested_list_raises_error(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        with pytest.raises(ValueError, match="Nested lists are not allowed"):
            sio_dict["nested_list"] = [1, 2, {"key": "value"}]

    def test_delitem(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        sio_dict["key_to_delete"] = "value"
        del sio_dict["key_to_delete"]
        assert "key_to_delete" not in sio_dict
        
        with open(temp_file, 'r') as f:
            saved_data = json.load(f)
        assert "key_to_delete" not in saved_data

    def test_update_simple_values(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        sio_dict.update({"key1": "value1", "key2": 2})
        assert sio_dict == {"key1": "value1", "key2": 2}
        
        with open(temp_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == {"key1": "value1", "key2": 2}

    def test_update_nested_dict_raises_error(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        with pytest.raises(ValueError, match="Nested dictionary found for key 'nested'. Nested dictionaries are not allowed"):
            sio_dict.update({"simple": "value", "nested": {"key": "value"}})

    def test_save_indentation(self, temp_file):
        sio_dict = OnChangeSaveDict(temp_file)
        sio_dict["key1"] = "value1"
        sio_dict["key2"] = 2
        
        with open(temp_file, 'r') as f:
            content = f.read()
        
        assert content == '{\n  "key1": "value1",\n  "key2": 2\n}'
