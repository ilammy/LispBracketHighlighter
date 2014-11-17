from itertools import izip

from utils import repeated

#
# Type matchers
#

def boolean(value):
    """Matches booleans."""
    if not isinstance(value, bool):
        raise ValueError("%r is not a boolean" % value)

    return value


def string(value):
    """Matches strings (both ASCII and Unicode)."""
    if not isinstance(value, str) and not isinstance(value, unicode):
        raise ValueError("%r is not a string" % value)

    return value


def integer(value):
    """Matches integers."""
    if not isinstance(value, int) and not isinstance(value, long):
        raise ValueError("%r is not an integer" % value)

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
            raise ValueError("%r does not match any pattern" % expression)

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

class UnificationFailure(ValueError):
    """Raised when `unify` fails to match an expression against a pattern.

    Fields:
        message - a human-readable string describing the error cause

        stack - a list of dict keys encountered on the way to the error
    """
    def __init__(self, message, stack):
        self.message = message
        self.stack = stack

    def __str__(self):
        stacktrace = " > ".join(self.stack)
        return stacktrace + ": " + self.message


def unify(expression, pattern, stack=[]):
    """Unifies an expression against a pattern.

    To unify means to check the structure and types of the expression and its
    subexpressions, and to replace some subexpressions with default values.

    This unifiction function supports the following expression types:

      * objects   - JSON objects. They are recursively matched by keys.

      * sequences - JSON arrays. They are recursively matched by elements.

      * literals  - Everything else. They are treated as atomic objects and
                    match literally (in sense of ==).

    Combinations of these expressions are specified with patterns:

      * dict     - Matches an object.
                   Returns a dict of matched key-value pairs.

      * list     - Matches a sequence of undefined length.
                   Returns a list of matched results.

      * tuple    - Matches a sequence of fixed length.
                   Returns a tuple of matched results.

      * literal  - Matches a literal.
                   Returns this literal.

      * either   - Matches either of the given patterns.
                   Returns the first successful match result.

      * optional - Matches an optional key of an object.
                   Returns the match result if the key is present,
                   and specified default value otherwise.

      * lambda   - Matches a value against an arbitrary predicate.
                   Returns what the predicate returns.
    """
    if isinstance(pattern, dict):
        return unify_dict(expression, pattern, stack)

    if isinstance(pattern, list):
        return unify_list(expression, pattern, stack)

    if isinstance(pattern, tuple):
        return unify_tuple(expression, pattern, stack)

    if callable(pattern):
        return unify_predicate(expression, pattern, stack)

    # Literal pattern?
    if expression == pattern:
        return pattern

    # Give up
    message = "%r does not match %r" % (expression, pattern)
    raise UnificationFailure(message, stack)

#
# Private for unify
#

def keyable(object):
    """Checks whether an object is an 'object' for `unify`."""
    return hasattr(object, '__getattribute__') \
        or hasattr(object, '__getattr__')


def iterable(object):
    """Checks whether an object is a 'sequence' for `unify`."""
    return hasattr(object, '__iter__')


def unify_dict(object, dict_pattern, stack):
    """Unifies an object.

    Every key of the object must be present in the pattern. Value of every key
    present in the object must match the specified subpattern. If a key is
    missing in the object, it can be replaced with a default value. The defult
    values are either explicitly specified by optional(), or implicitly assumed
    for objects (empty dict) and sequences (empty list). If there is no default
    value then a match failure occurs.
    """
    if not keyable(object) or not iterable(object):
        message = "%r is not an object" % object
        raise UnificationFailure(message, stack)

    mismatched_keys = set(object) - set(dict_pattern)
    if mismatched_keys:
        message = "unexpected keys: " + ", ".join(mismatched_keys)
        raise UnificationFailure(message, stack)

    result = {}

    for key, subpattern in dict_pattern.iteritems():
        optional_key, default_value = False, None

        if isinstance(subpattern, _OptionalPattern):
            optional_key, default_value = True, subpattern.default
            subpattern = subpattern.pattern

        if key in object:
            result[key] = unify(object[key], subpattern, stack + [key])

        elif optional_key:
            result[key] = default_value

        else:
            if isinstance(subpattern, dict):
                result[key] = unify_dict({}, subpattern, stack + [key])

            elif isinstance(subpattern, list):
                result[key] = unify_list([], subpattern, stack + [key])

            else:
                message = "missing required key '%s'" % key
                raise UnificationFailure(message, stack)

    return result


def unify_list(sequence, list_pattern, stack):
    """Unifies a sequence of indefinite length.

    The pattern here describes a sequence of items that must be repeating. For
    example [integer, string] would match [1, "2", 3, "4", 5]. The most common
    option is just one pattern element. There is also a special case of empty
    pattern [] which matches only empty sequences.
    """
    if not iterable(sequence):
        message = "%r is not a sequence" % sequence
        raise UnificationFailure(message, stack)

    if sequence and not list_pattern:
        raise UnificationFailure("%r is not empty" % sequence, stack)

    return [unify(subitem, subpattern, stack)
            for subitem, subpattern
            in izip(sequence, repeated(list_pattern))]


def unify_tuple(sequence, tuple_pattern, stack):
    """Unifies a sequence of fixed length.

    The sequence must have exactly the same length as the pattern and each
    element must match the corresponding subpattern.
    """
    if not iterable(sequence):
        message = "%r is not a sequence" % sequence
        raise UnificationFailure(message, stack)

    # Flat it out
    sequence = tuple(sequence)

    if len(sequence) != len(tuple_pattern):
        message = "%r has incorrect length (expected %d)" % \
                (sequence, len(tuple_pattern))
        raise UnificationFailure(message, stack)

    return tuple(unify(subitem, subpattern, stack)
            for subitem, subpattern 
            in zip(sequence, tuple_pattern))


def unify_predicate(expression, predicate, stack):
    """Unifies an expression against an arbitrary predicate.

    The predicate either returns a unified value, or raises a ValueError that
    describes the reason why the match failed.
    """
    try:
        return predicate(expression)
    except ValueError as match_failure:
        raise UnificationFailure(str(match_failure), stack)
