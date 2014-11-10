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
