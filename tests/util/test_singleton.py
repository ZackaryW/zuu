from zuu.util.singleton import absoluteSingleton

class TestAbsoluteSingleton:

    def test_absoluteSingleton_returns_class(self):
        result = absoluteSingleton()
        assert isinstance(result, type)

    def test_absoluteSingleton_class_name(self):
        result = absoluteSingleton()
        assert result.__name__ == "AbsoluteSingleton"

    def test_absoluteSingleton_not_same(self):
        Singleton1 = absoluteSingleton()
        Singleton2 = absoluteSingleton()
        assert Singleton1 is not Singleton2

