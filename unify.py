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
    class UnificationFailure(ValueError):
        def __init__(self, message, stack):
            self.message = message
            self.stack = stack

        def __str__(self):
            stacktrace = " > ".join(self.stack)
            return stacktrace + ": " + self.message

    def keyable(object):  return hasattr(object, '__getattribute__')
    def iterable(object): return hasattr(object, '__iter__')
    def callable(object): return hasattr(object, '__call__')

    def unify_dict(expression, pattern, stack):
        if not keyable(expression) or not iterable(expression):
            message = "'%r' is not an object" % expression
            raise UnificationFailure(message, stack)

        mismatched_keys = set(expression) - set(pattern)
        if mismatched_keys:
            message = "unexpected keys: %s" % ", ".join(mismatched_keys)
            raise UnificationFailure(message, stack)

        result = {}

        for key, subpattern in pattern.iteritems():
            optional_key, default_value = False, None

            if isinstance(subpattern, _OptionalPattern):
                optional_key, default_value = True, subpattern.default
                subpattern = subpattern.pattern

            if key in expression:
                result[key] = unify(expression[key], subpattern, stack + [key])

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

    def unify_list(expression, pattern, stack):
        if not iterable(expression):
            message = "'%r' is not a sequence" % expression
            raise UnificationFailure(message, stack)

        def infinite_zip(subitems, subpatterns):
            subpatterns_iter = iter(subpatterns)

            for subitem in subitems:
                try:
                    subpattern = next(subpatterns_iter)
                except StopIteration:
                    subpatterns_iter = iter(subpatterns)
                    try:
                        subpattern = next(subpatterns_iter)
                    except StopIteration:
                        message = "sequence is not empty"
                        raise UnificationFailure(message, stack)

                yield subitem, subpattern

        result = []

        for subitem, subpattern in infinite_zip(expression, pattern):
            result.append(unify(subitem, subpattern, stack))

        return result

    def unify_tuple(expression, pattern, stack):
        if not iterable(expression):
            message = "'%r' is not a sequence" % expression
            raise UnificationFailure(message, stack)

        def strict_zip(subitems, subpatterns):
            subpatterns_iter = iter(subpatterns)

            for subitem in subitems:
                try:
                    subpattern = next(subpatterns_iter)
                except StopIteration:
                    message = "too many values: %r" % subitems
                    raise UnificationFailure(message, stack)

                yield subitem, subpattern

            try:
                next(subpatterns_iter)
            except StopIteration:
                pass
            else:
                message = "too few values: %r" % subitems
                raise UnificationFailure(message, stack)

        result = []

        for subitem, subpattern in strict_zip(expression, pattern):
            result.append(unify(subitem, subpattern, stack))

        return tuple(result)

    def unify_predicate(expression, pattern, stack):
        try:
            return pattern(expression)
        except ValueError as match_failure:
            raise UnificationFailure(str(match_failure), stack)

    def unify(expression, pattern, stack):
        if isinstance(pattern, dict):
            return unify_dict(expression, pattern, stack)

        if isinstance(pattern, list):
            return unify_list(expression, pattern, stack)

        if isinstance(pattern, tuple):
            return unify_tuple(expression, pattern, stack)

        if callable(pattern):
            return unify_predicate(expression, pattern, stack)

        if expression == pattern:
            return pattern

        message = "'%r' does not match '%r'" % (expression, pattern)
        raise UnificationFailure(message, stack)

    try:
        return unify(expression, pattern, [])
    except UnificationFailure as failure:
        raise ValueError(str(failure))
