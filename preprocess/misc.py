
from contextlib import ExitStack
import datetime
import functools


def function_with_exitstack(idx=0):
    """Decorator for functions requiring contextlib.ExitStack

    The decorator creates an ExitStack object and enters its context before
    calling the decorated function with the ExitStack object into position
    `idx` in the arguments.

        >>> @function_with_exitstack(0)
                def foo(stack, fn):
                    fid = stack.enter_context(open(fn))
                    return fid.read()
        >>> foo("foobar.txt")
        This is the content of foobar.txt

    For usage on a method, use idx > 0. I.e:

        >>> class Foo:
                @function_with_exitstack(idx=1)
                def foo(self, stack):
                    fid = stack.enter_context(self.path.open("r"))
                    return fid.read()
        >>> Foo().foo()
        This is the content of `Foo().path`


    Parameters
    ----------
    idx : int
        Index to insert exitstack

    Returns
    -------
    decorated
        The decorated function
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            with ExitStack() as stack:
                args = list(args)
                args.insert(idx, stack)
                return f(*args, **kwargs)
        return wrapped
    return decorator


def iso_timestamp(tz=None):
    """Return current time in ISO format

    Parameters
    ----------
    tz : :py:class:`~datetime.timezone`
        Timezone for timestamp. If None (default) UTC is assumed.

    Returns
    -------
    str
        Current time in ISO format

    """
    tz = tz if tz is not None else datetime.timezone.utc
    dt = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    return dt.replace("+00:00", "Z")

