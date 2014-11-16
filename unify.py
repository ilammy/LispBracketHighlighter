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

#
# Helper types
#

class _OptionalPattern:
    """An optional pattern for dicts with a default value."""
    def __init__(self, pattern, default):
        self.pattern = pattern
        self.default = default

#
# Combinators
#

def either(*patterns):
    """Matches either of the specified patterns.

    An expression will be against the patterns in the given order. The first
    successful match yields the result. If none of the patterns matches,
    a special ValueError is raised.
    """
    def match_either(expression):
        for pattern in patterns:
            try:
                return unify(expression, pattern)
            except ValueError: # no match
                continue
        else:
            raise ValueError("'%r' does not match any pattern" % expression)

    return match_either


def optional(pattern, default=None):
    """Matches a possibly missing dict key against a pattern.

    If the key is present, its value will be matched against the pattern.
    Otherwise, the default value becomes the match result.
    """
    return _OptionalPattern(pattern, default)

#
# Unification
#

def unify(expression, pattern):
    """Unifies an expression against a pattern.

    To unify means to check the structure and types of the expression and its
    subexpressions, and to replace some subexpressions with default values.

    This unifiction function supports the following expression types:

      * dicts     - JSON objects. They are recursively matched by keys.

      * sequences - JSON arrays. They are recursively matched by elements.

      * literals  - Everything else. They are treated as atomic objects and
                    match literally (in sense of ==).

    Combinations of these expressions are specified with patterns:

      * dict     - Matches a dict.
                   Returns a dict of matched key-value pairs.

      * list     - Matches a sequence of undefined length.
                   Returns a list of matched results.

      * tuple    - Matches a sequence of fixed length.
                   Returns a tuple of matched results.

      * literal  - Matches a literal.
                   Returns this literal.

      * either   - Matches either of the given patterns.
                   Returns the first successful match result.

      * optional - Matches a key of an dict.
                   Returns the match result if the key is present in the dict,
                   and specified default value otherwise.

      * lambda   - Matches a value against an arbitrary predicate.
                   Returns what the predicate returns.
    """
    pass
