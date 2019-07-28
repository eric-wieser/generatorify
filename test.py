from unittest import mock
from collections import namedtuple
import weakref

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

# verify the helpers work
assert Value(1) == Value(1)
assert Value(1) != Value(2)
assert Error(ValueError()) == Error(ValueError())
assert Error(ValueError()) != Error(TypeError())
assert Value(1) != Error(1)
assert not (Value(1) == Error(1))


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

    @pytest.fixture(params=['direct', 'roundtrip'])
    def c(self, request):
        return request.getfixturevalue("c_{}".format(request.param))


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


class TestReturnImmediately(ComparisonTest):
    """ Test that return behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        return 2
        yield  # pragma: no cover

    @staticmethod
    def callback(m, yield_):
        m.one()
        return 2

    def test(self, c, g, c_m, g_m):
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


class TestReceive(ComparisonTest):
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

    def test_send(self, c, g, c_m, g_m):
        # first send call must be non-none
        assert result_of(g.send, "not none") == result_of(c.send, "not none") == Error(TypeError(mock.ANY))
        assert g_m.method_calls == c_m.method_calls == []

        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.send, 'a') == result_of(c.send, 'a') == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.send, 'b') == result_of(c.send, 'b') == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_throw_before_first(self, c, g, c_m, g_m):
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Error(ValueError())
        assert g_m.method_calls == c_m.method_calls == []
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls == []

    def test_close_before_first(self, c, g, c_m, g_m):
        assert result_of(g.close) == result_of(c.close) == Value(None)
        assert g_m.method_calls == c_m.method_calls == []
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls == []

    def test_throw(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Error(ValueError())
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_close(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.close) == result_of(c.close) == Value(None)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestCatchAndContinue(ComparisonTest):
    """ Test that catch behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        try:
            yield 1
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test

        # not caught
        yield 2
        m.three()

    @staticmethod
    def callback(m, yield_):
        m.one()
        # caught and continued
        try:
            yield_(1)
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test

        yield_(2)
        m.three()

    def test_throw(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Value(2)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_close(self,  c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        # different messages, wildcard goes in the middle
        assert result_of(g.close) == Error(RuntimeError(mock.ANY)) == result_of(c.close)
        assert g_m.method_calls == c_m.method_calls

        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestCatchAndRaise(ComparisonTest):
    """ Test that catch behaves just like a generator """
    @staticmethod
    def generator(m):
        m.one()
        try:
            yield 1
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test
            raise OSError()

    @staticmethod
    def callback(m, yield_):
        m.one()
        # caught and continued
        try:
            yield_(1)
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test
            raise OSError()

    def test_throw(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Error(OSError())
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_close(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.close) == result_of(c.close) == Error(OSError())
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.close) == result_of(c.close) == Value(None)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls


class TestCatchAndReturn(ComparisonTest):
    @staticmethod
    def generator(m):
        m.one()
        try:
            yield 1
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test
            return 3

    @staticmethod
    def callback(m, yield_):
        m.one()
        # caught and continued
        try:
            yield_(1)
        except BaseException as e:
            m.two(Error(e))  # Error(e) makes equality work in the test
            return 3

    def test_throw(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.throw, ValueError) == result_of(c.throw, ValueError) == Error(StopIteration(3,))
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

    def test_close(self, c, g, c_m, g_m):
        assert result_of(next, g) == result_of(next, c) == Value(1)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(g.close) == result_of(c.close) == Value(None)
        assert g_m.method_calls == c_m.method_calls
        assert result_of(next, g) == result_of(next, c) == Error(StopIteration())
        assert g_m.method_calls == c_m.method_calls

# no fixture here, they make checking reference too hard
def test_no_circular_references():
    def invoke_with_values(f):
        f(1)
        f(2)  # pragma: no cover
        f(3)  # pragma: no cover
    values_iter = generatorify.generator_from_callback(
        lambda yield_: invoke_with_values(yield_)
    )
    next(values_iter)

    wr = weakref.ref(values_iter)
    del values_iter

    assert wr() is None


if __name__ == '__main__':
    pytest.main([__file__, '-vv', '-s'])  # pragma: no cover
