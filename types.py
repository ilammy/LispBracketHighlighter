import sublime

#
# Regions
#

class Region:
    """A region of text in a sublime.View.

    This a companion of sublime.Region that is never reversed.

    Fields:
        begin, end - the starting and the ending points of this region
    """
    def __init__(self, begin, end):
        assert (begin <= end)
        self.begin = begin
        self.end = end

    def as_sublime_region(self):
        """Converts this region to sublime.Region."""
        return sublime.Region(self.begin, self.end)

    def overlaps(self, other):
        """True if this regions overlaps the other one."""
        assert (self <= other)
        return (other.begin < self.end)

    def touches(self, other):
        """True if this regions overlaps or touches the other one."""
        assert (self <= other)
        return (other.begin <= self.end)


def span(from_region, to_region):
    """Returns a region spanning both given regions."""
    assert (from_region <= to_region)
    return Region(from_region.begin, to_region.end)

#
# Brackets
#

class Bracket:
    """A bracket found in text.

    Do not construct brackets directly, use LeftBracket and RightBracket.

    Fields:
        point - the point in the text of the beginning of the bracket

        kind - textual representation of the bracket
    """
    _LEFT, _RIGHT = 0, 1

    def __init__(self, type, point, kind):
        assert (type == Bracket._LEFT) or (type == Bracket._RIGHT)
        self._type = type

        self.point = point
        self.kind = kind

    def is_left(self):
        """True if this bracket is a left one, False otherwise."""
        return self._type == Bracket._LEFT

    def is_right(self):
        """True if this bracket is a right one, False otherwise."""
        return self._type == Bracket._RIGHT

    def region(self):
        """Returns a region delimiting this bracket."""
        return Region(self.point, self.point + len(self.kind))

    def contains(self, point):
        """True is the point is inside the bracket.

        A point is 'inside' a bracket if it points to one of the bracket's
        characters, but does not touch the 'inside' of the expression region
        delimited by a bracket pair.
        """
        begin, end = self.point, self.point + len(self.kind)
        if self.is_left():
            return (begin <= point) and (point < end)
        else:
            return (begin < point) and (point <= end)

    def inside_point(self):
        """Returns the inside point of this bracket.

        An inside point is a point of the character that touches the 'inside'
        of the expression region delimited by a bracket pair.

        For example:

            <%       %>
             ^       ^
        """
        if self.is_left():
            return self.point + len(self.kind) - 1
        else:
            return self.point


def LeftBracket(point, kind):
    """Constructs a left Bracket of a given kind a given point."""
    return Bracket(Bracket._LEFT, point, kind)


def RightBracket(point, kind):
    """Constructs a right Bracket of a given kind a given point."""
    return Bracket(Bracket._RIGHT, point, kind)

#
# Scopes
#

class Scope:
    """A scope in text delimited by a pair of matching brackets.

    Scopes determine the nature and the nesting level of a pair of brackets.
    The nature of indices is documented in bracket_scopes.index_brackets.

    Indices determine the scope type. There are five types of scopes:

        1. Primary mainline - immediately enclosing scope of the cursor point.
           There can be at most one primary mainline scope.

        2. Secondary mainline - immediately enclosing scopes of the primary
           mainline scope or the other secondary mainline scope. There can be
           only one secondary mainline scope of each nesting depth.

        3. Offside - other, non-mainline scopes. They also have their own
           nesting depth.

        4. Adjacent - the scope delimited by the brackets adjacent to the
           cursor. Adjacent means that the cursor must not be inside the scope.
           There can be at most one such scope.

        5. Inconsistent - scopes with brackets that do not match.

    Fields:
        index - the index of this scope, a tuple of (outer, inner) numbers that
                are also available separately via outer_index and inner_index

        left_bracket - the left bracket of this scope, instance of Bracket

        right_bracket - the right bracket of this scope, instance of Bracket
    """
    def __init__(self, index, left_bracket, right_bracket):
        assert left_bracket.is_left() and right_bracket.is_right()

        self.index = self.outer_index, self.inner_index = index

        self.left_bracket = left_bracket
        self.right_bracket = right_bracket

    def bracket_regions(self):
        """Constructs a pair of regions bound to the brackets of this scope."""
        return self.left_bracket.region(), self.right_bracket.region()

    def expression_region(self):
        """Constructs a region bound to the extent of this scope."""
        return span(self.left_bracket.region(), self.right_bracket.region())

    def is_not_consistent_with(self, bracket_pairs):
        """False is this scope is consistent w.r.t. the given set of brackets.

        Args:
            [bracket_pairs] - a set of (left, right) pairs of bracket kinds
                that are considered valid and consistent
        """
        bracket_pair = self.left_bracket.kind, self.right_bracket.kind
        return bracket_pair not in bracket_pairs

    def is_primary_mainline(self):
        """True is this scope is a primary mainline scope."""
        return (self.inner_index == 0) and (self.outer_index == 0)

    def is_secondary_mainline(self):
        """True is this scope is a secondary mainline scope."""
        return (self.inner_index == 0) and (self.outer_index != 0)

    def is_offside(self):
        """True is this scope is an offside scope."""
        return self.inner_index > 0

    def is_adjacent_to(self, cursors):
        """True is this scope is adjacent to any of the given cursors.

        Args:
            [cursors] - a list of cursor points for adjacency test
        """
        def is_an_endpoint(cursor):
            return self.left_bracket.contains(cursor) or \
                   self.right_bracket.contains(cursor)

        for cursor in cursors:
            if is_an_endpoint(cursor):
                return True
        else:
            return False
