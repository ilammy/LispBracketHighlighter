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
