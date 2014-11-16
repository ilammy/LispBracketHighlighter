#
# Type matchers
#

def boolean(value):
    """Matches booleans."""
    if not isinstance(value, bool):
        raise ValueError("'%r' is not a boolean" % value)

    return value


def string(value):
    """Matches strings (both ASCII and Unicode)."""
    if not isinstance(value, str) and not isinstance(value, unicode):
        raise ValueError("'%r' is not a string" % value)

    return value


def integer(value):
    """Matches integers."""
    if not isinstance(value, int) and not isinstance(value, long):
        raise ValueError("'%r' is not an integer" % value)

    return value


def either():
    pass

def optional():
    pass
