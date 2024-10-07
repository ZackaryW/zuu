import pytest
from zuu.std.importlib import (
    import_file,
    import_from_file,
    import_folder,
)


class TestImportFile:
    def test_import_file_success(self, tmp_path):
        test_file = tmp_path / "test_module.py"
        test_file.write_text("test_var = 42")

        module = import_file(str(test_file))
        assert module.test_var == 42

    def test_import_file_invalid_python(self, tmp_path):
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("This is not valid Python code")

        with pytest.raises(SyntaxError):
            import_file(str(invalid_file))


class TestImportFromFile:
    def test_import_from_file_success(self, tmp_path):
        test_file = tmp_path / "test_module.py"
        test_file.write_text("test_function = lambda: 'Hello'")

        func = import_from_file(str(test_file), "test_function")
        assert func() == "Hello"

    def test_import_from_file_attribute_error(self, tmp_path):
        test_file = tmp_path / "test_module.py"
        test_file.write_text("test_var = 42")

        with pytest.raises(AttributeError):
            import_from_file(str(test_file), "nonexistent_attribute")


class TestImportFolder:
    def test_import_folder(self, tmp_path):
        folder = tmp_path / "test_package"
        folder.mkdir()
        (folder / "module1.py").write_text("var1 = 'module1'")
        (folder / "module2.py").write_text("var2 = 'module2'")
        subfolder = folder / "subpackage"
        subfolder.mkdir()
        (subfolder / "module3.py").write_text("var3 = 'module3'")

        imported_modules = import_folder(str(folder))

        assert "module1" in imported_modules
        assert "module2" in imported_modules
        assert "subpackage.module3" in imported_modules
        assert imported_modules["module1"].var1 == "module1"
        assert imported_modules["module2"].var2 == "module2"
        assert imported_modules["subpackage.module3"].var3 == "module3"

    def test_import_folder_empty(self, tmp_path):
        empty_folder = tmp_path / "empty_folder"
        empty_folder.mkdir()

        imported_modules = import_folder(str(empty_folder))
        assert imported_modules == {}

    def test_import_folder_with_init(self, tmp_path):
        folder = tmp_path / "package_with_init"
        folder.mkdir()
        (folder / "__init__.py").write_text("init_var = 'initialized'")
        (folder / "module.py").write_text("module_var = 'from module'")

        imported_modules = import_folder(str(folder))
        assert "module" in imported_modules
        assert "module_var" in dir(imported_modules["module"])
        assert "__init__" not in imported_modules
