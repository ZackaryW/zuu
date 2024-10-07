import os
import pytest
from zuu.std.os import preserve_cwd

class TestPreserveCwd:
    def test_preserve_cwd_changes_directory(self, tmp_path):
        original_cwd = os.getcwd()
        new_dir = tmp_path / "test_dir"
        new_dir.mkdir()

        @preserve_cwd
        def change_directory():
            os.chdir(str(new_dir))
            return os.getcwd()

        result = change_directory()
        assert result == str(new_dir)
        assert os.getcwd() == original_cwd

    def test_preserve_cwd_with_exception(self, tmp_path):
        original_cwd = os.getcwd()
        new_dir = tmp_path / "test_dir"
        new_dir.mkdir()

        @preserve_cwd
        def raise_exception():
            os.chdir(str(new_dir))
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            raise_exception()

        assert os.getcwd() == original_cwd

    def test_preserve_cwd_nested_calls(self, tmp_path):
        original_cwd = os.getcwd()
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        @preserve_cwd
        def outer_function():
            os.chdir(str(dir1))

            @preserve_cwd
            def inner_function():
                os.chdir(str(dir2))
                return os.getcwd()

            inner_result = inner_function()
            return os.getcwd(), inner_result

        outer_result, inner_result = outer_function()
        assert outer_result == str(dir1)
        assert inner_result == str(dir2)
        assert os.getcwd() == original_cwd

    def test_preserve_cwd_with_args_and_kwargs(self):
        @preserve_cwd
        def function_with_args(arg1, arg2, kwarg1=None):
            return arg1, arg2, kwarg1

        result = function_with_args(1, 2, kwarg1="test")
        assert result == (1, 2, "test")
