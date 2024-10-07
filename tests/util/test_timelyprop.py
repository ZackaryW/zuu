import pytest
import time
from zuu.prop import timely_cls_property, timely_property

class TestTimelyProperty:
    @pytest.fixture
    def test_class(self):
        class TestClass:
            @timely_property(1)
            def test_property(self):
                return time.time()

        return TestClass()

    def test_property_caching(self, test_class):
        first_value = test_class.test_property
        time.sleep(0.5)
        second_value = test_class.test_property
        assert first_value == second_value

    def test_property_expiration(self, test_class):
        first_value = test_class.test_property
        time.sleep(1.1)
        second_value = test_class.test_property
        assert first_value != second_value

    def test_multiple_properties(self):
        class MultiPropClass:
            @timely_property(1)
            def prop1(self):
                return time.time()

            @timely_property(2)
            def prop2(self):
                return time.time()

        obj = MultiPropClass()
        p1_first = obj.prop1
        p2_first = obj.prop2

        time.sleep(1.2)
        assert obj.prop1 != p1_first
        assert obj.prop2 == p2_first

    def test_negative_expiration(self):

        try:

            class NegExpClass:
                @timely_property(-1)
                def always_cached(self):
                    return time.time()

        except:  # noqa
            return

        pytest.fail("Negative expiration should not raise an exception")


class TestTimelyCLSProperty:
    @pytest.fixture
    def test_class(self):
        class TestClass:
            @timely_cls_property(1)
            def test_property(cls):
                return time.time()

        return TestClass

    def test_cls_property_caching(self, test_class):
        first_value = test_class.test_property
        time.sleep(0.5)
        second_value = test_class.test_property
        assert first_value == second_value

    def test_cls_property_expiration(self, test_class):
        first_value = test_class.test_property
        time.sleep(1.1)
        second_value = test_class.test_property
        assert first_value != second_value

    def test_multiple_cls_properties(self):
        class MultiPropClass:
            @timely_cls_property(1)
            def prop1(cls):
                return time.time()

            @timely_cls_property(2)
            def prop2(cls):
                return time.time()

        p1_first = MultiPropClass.prop1
        p2_first = MultiPropClass.prop2

        time.sleep(1.5)
        assert MultiPropClass.prop1 != p1_first
        assert MultiPropClass.prop2 == p2_first

    def test_very_long_expiration(self):
        class LongExpClass:
            @timely_cls_property(3600)  # 1 hour
            def long_lived(cls):
                return time.time()

        first_value = LongExpClass.long_lived
        time.sleep(0.1)
        second_value = LongExpClass.long_lived
        assert first_value == second_value
