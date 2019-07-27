from unittest import mock
from collections import namedtuple

import pytest

import generatorify


class Error(namedtuple('Error', 'e')):
    def _key(self):
        return (type(self.e), self.e.args)

    def __eq__(self, other):
        if not isinstance(other, Error):
            return NotImplemented
        return self._key() == other._key()

    def __ne__(self, other):
        if not isinstance(other, Error):
            return NotImplemented
        return self._key() != other._key()


class Value(namedtuple('Value', 'v')):
    def _key(self):
        return self.v

    def __eq__(self, other):
        if not isinstance(other, Value):
            return NotImplemented
        return self._key() == other._key()

    def __ne__(self, other):
        if not isinstance(other, Value):
            return NotImplemented
        return self._key() != other._key()


def result_of(f, *args, **kwargs):
    try:
        return Value(f(*args, **kwargs))
    except BaseException as e:
        return Error(e)


class ComparisonTest:
    @pytest.fixture
    def g_m(self):
        return mock.MagicMock()

    @pytest.fixture
    def g(self, g_m):
        g = self.generator(g_m)
        assert g_m.method_calls == []
        return g

    @pytest.fixture
    def c_m(self):
        return mock.MagicMock()

    @pytest.fixture
    def c_direct(self, c_m):
        c = generatorify.generator_from_callback(lambda yield_: self.callback(c_m, yield_))
        assert c_m.method_calls == []
        return c

    @pytest.fixture
    def c_roundtrip(self, c_m):
        callback = generatorify.callback_from_generator(lambda: self.generator(c_m))
        c = generatorify.generator_from_callback(callback)
        assert c_m.method_calls == []
        return c

    @pytest.fixture(params=['roundtrip', 'normal'])
    def c(self, c_direct, c_roundtrip, request):
        if request.param == 'roundtrip':
            return c_roundtrip
        else:
            return c_direct


class TestNext(ComparisonTest):
    """ Test that next behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        yield 1
        m.two()
        yield 2
        m.three()

    @staticmethod
    def callback(m, yield_):
        m.one()
        yield_(1)
        m.two()
        yield_(2)
        m.three()

    def test(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestReturn(ComparisonTest):
    """ Test that return behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        yield 1
        m.two()
        return 2

    @staticmethod
    def callback(m, yield_):
        m.one()
        yield_(1)
        m.two()
        return 2

    def test(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration(2,))
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestRaise(ComparisonTest):
    """ Test that raise behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        yield 1
        m.two()
        raise ValueError

    @staticmethod
    def callback(m, yield_):
        m.one()
        yield_(1)
        m.two()
        raise ValueError

    def test(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(ValueError())
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestSend(ComparisonTest):
    """ Test that send behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        ret1 = yield 1
        m.two(ret1)
        ret2 = yield 2
        m.three(ret2)

    @staticmethod
    def callback(m, yield_):
        m.one()
        ret1 = yield_(1)
        m.two(ret1)
        ret2 = yield_(2)
        m.three(ret2)

    def test(self, c, g, c_m, g_m):
        # first send call must be non-none
        assert result_of(g.send, "not none") == result_of(c.send, "not none") == Error(TypeError(mock.ANY))
        assert g_m.method_calls == c_m.method_calls == []

        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.send, 'a') == result_of(c.send, 'a') == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.send, 'b') == result_of(c.send, 'b') == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestCatch(ComparisonTest):
    """ Test that catch behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        try:
            yield 1
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test
        else:
            m.two()

        # not caught
        yield 2
        m.three()

    @staticmethod
    def callback(m, yield_):
        m.one()
        try:
            yield_(1)
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test
        else:
            m.two()

        # not caught
        yield_(2)
        m.three()

    def test_throw_before_first(self, c, g, c_m, g_m):
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Error(ValueError())
        assert g_m.method_calls == c_m.method_calls == []
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls == []

    def test_throw_within_try_except(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_throw_outside_try_except(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Error(ValueError())
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_close_within_try_except(self,  c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        # different messages, wildcard goes in the middle
        assert result_of(g.close) == Error(RuntimeError(mock.ANY)) == result_of(c.close)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_close_outside_try_except(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.close) == result_of(c.close) == Value(None)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


if __name__ == '__main__':
    pytest.main([__file__, '-vv'])
