import sys


def test_env_decorator(value=None):
    # prevent functions from executing when running tests
    def inner_func(func):
        def wrapper(*args, **kwargs):
            if "test" in sys.argv:
                return value
            return func(*args, **kwargs)

        return wrapper

    return inner_func
