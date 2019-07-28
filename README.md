# generatorify

[![Build Status](https://travis-ci.org/eric-wieser/generatorify.svg?branch=master)](https://travis-ci.org/eric-wieser/generatorify)
[![codecov](https://codecov.io/gh/eric-wieser/generatorify/branch/master/graph/badge.svg)](https://codecov.io/gh/eric-wieser/generatorify)

Convert a function taking a repeated callback to a generator that pauses at each callback

If a third party provides a function like:
```python
def invoke_with_values(f):
    f(1)
    f(2)
    f(3)
```
But you wish it were written
```python
def iter_values():
    yield 1
    yield 2
    yield 3
```
Then this library lets you pass `yield` as the callback as if it were a real function:
```python
from generatorify import generator_from_callback
values_iter = generator_from_callback(
	lambda yield_: invoke_with_values(yield_)
)
for v in values_iter:
	print(v)
```

For completeness, this also provides an inverse, `callback_from_generator`,
which can be used as
```python
from generatorify import callback_from_generator
invoke_with_values = callback_from_generator(iter_values)
invoke_with_values(print)
```
