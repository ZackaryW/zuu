import time
import pytest
from zuu.std.time import remaining_time

class TestRemainingTime:
    def test_remaining_time_am_pm(self):
        result = remaining_time("10:25pm")
        assert result is not None
        assert isinstance(result, int)

    def test_remaining_time_24_hour_format(self):
        result = remaining_time("21:24")
        assert result is not None
        assert isinstance(result, int)

    def test_remaining_time_seconds(self):
        result = remaining_time("555")
        assert result is not None
        assert isinstance(result, int)

    def test_remaining_time_past_time_am_pm(self):
        current_time = time.localtime()
        past_time = f"{(current_time.tm_hour - 1) % 12}:{current_time.tm_min}pm"
        result = remaining_time(past_time)
        assert result

    def test_remaining_time_past_time_24_hour_format(self):
        current_time = time.localtime()
        past_time = f"{(current_time.tm_hour - 1) % 24}:{current_time.tm_min}"
        result = remaining_time(past_time)
        assert result is None

    def test_remaining_time_invalid_format(self):
        with pytest.raises(ValueError):
            remaining_time("invalid")
