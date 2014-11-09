import sublime

from heapq import heapify, heappop, heapreplace

from bracket_scopes \
    import is_not_consistent, is_primary_mainline, is_secondary_mainline, \
           is_offside, is_adjacent, scope_bracket_regions, \
           scope_expression_region
#
# Constants
#

class ColorMode:    # enumeration
    NONE = 0
    BRACKETS = 1
    EXPRESSION = 2

class AdjacentMode: # flags
    NONE  = 0
    LEFT  = 1
    RIGHT = 2
    BOTH  = 3

class BracketKind: # enumeration
    PRIMARY = 'primary_mode'
    SECONDARY = 'secondary_mode'
    OFFSIDE = 'offside_mode'
    ADJACENT = 'adjacent_mode'
    INCONSISTENT = 'inconsistent_mode'

BACKGROUND = 'background'
CURRENT_LINE = 'current_line'

OFFSIDE_LIMIT = 'offside_limit'

ADJACENT_SIDE = 'adjacent_side'

class BracketColor:
    PRIMARY = 'primary_color'
    SECONDARY = 'secondary_colors'
    OFFSIDE = 'offside_colors'
    ADJACENT = 'adjacent_color'
    INCONSISTENT = 'inconsistent_color'

TRANSPARENT = -1

#Util
def outer_index(((oi, ii), r, k)): return oi
def inner_index(((oi, ii), r, k)): return ii

#
# Methods
#

# Keeping the extent first is important for not doing any __metashit__
# to make colorable regions have a proper order. The order matters
# because heapq's functions cannot accept keys or comparators.
def _colorable_region(extent, fg_color, bg_color_stack):
    return (extent, fg_color, bg_color_stack)

def _extent(colorable_region): return colorable_region[0]


def color_scopes(scopes, config, cursors, supported_brackets):
    """Splits and transforms the scopes into colorable regions.

    The result of this transform is a list of _visible_ regions,
    exact appearance of which is controlled by the `config` dict.

    Args:
        [scopes] - a sorted list of scopes to get transformed

        {config} - the configuration dict

        [cursors] - a list of current cursors

        [supported_brackets]
            - a list of (left, right) pairs of strings that denote
              the valid kinds of brackets

    Returns:
        [colorable_regions] - a list of resulting colorable regions
    """
    def color_type_of(scope):
        if is_not_consistent(scope, supported_brackets):
            return BracketKind.INCONSISTENT, None

        if is_primary_mainline(scope):
            return BracketKind.PRIMARY, None

        if is_secondary_mainline(scope):
            return BracketKind.SECONDARY, outer_index(scope)

        if is_adjacent(scope, cursors):
            return BracketKind.ADJACENT, None

        if is_offside(scope):
            return BracketKind.OFFSIDE, inner_index(scope)

        assert False, "unclassifiable scope %r" % scope

    def extents_of(scope, mode):
        if mode is ColorMode.NONE:
            return []

        if mode is ColorMode.BRACKETS:
            return list(scope_bracket_regions(scope))

        if mode is ColorMode.EXPRESSION:
            return [scope_expression_region(scope)]

        assert False, "invalid ColorMode %r" % mode

    def suitable(scope, (kind, index)):
        if kind is BracketKind.OFFSIDE:
            return index <= config[OFFSIDE_LIMIT]

        if kind is BracketKind.ADJACENT:
            side = config[ADJACENT_SIDE]
            need_left = side & AdjacentMode.LEFT
            need_right = side & AdjacentMode.RIGHT

            def is_at_left((index, (begin, end), (left, right)), cursor):
                return (begin <= cursor) and (cursor < begin + len(left))

            def is_at_right((index, (begin, end), (left, right)), cursor):
                return (end < cursor) and (cursor <= end + len(right))

            for cursor in cursors:
                if (need_left and is_at_left(scope, cursor)) or \
                   (need_right and is_at_right(scope, cursor)):
                    return True
            else:
                return False

        return True

    def not_nested(scope1, scope2):
        begin1, end1 = scope_expression_region(scope1)
        begin2, end2 = scope_expression_region(scope2)
        return end1 < begin2

    result = []
    bg_scope_stack = []

    for scope in scopes:
        kind, index = fg_color_type = color_type_of(scope)
        if not suitable(scope, fg_color_type):
            continue

        mode = config[kind]
        if mode is ColorMode.NONE:
            continue

        while bg_scope_stack and not_nested(bg_scope_stack[-1], scope):
            bg_scope_stack.pop()

        bg_color_stack = map(color_type_of, bg_scope_stack)

        for extent in extents_of(scope, mode):
            region = _colorable_region(extent, fg_color_type, bg_color_stack)
            result.append(region)

        if mode is ColorMode.EXPRESSION:
            bg_scope_stack.append(scope)

    return result


def split_into_disjoint(regions, lines):
    """Splits a list of colorable regions into disjoint colorable regions.

    This is necessary as Sublime Text does not handle region intersections
    properly, so we have to split them up by ourselves. Splitting by line
    boundaries is necessary to correctly handle bracket and expression
    backgrounds for current lines.

    Args:
        [regions] - a list of colorable regions to be split

        [lines] - a list of (begin, end) region tuples denoting the lines

    Returns:
        [regions] - a sorted list of disjoint colorable regions
    """
    if not regions: return []

    # Throwing in fake zero-length regions to denote the line boundaries. They
    # will be used only for splitting and will get filtered out of the results.
    #
    # Lines are (begin, end) where begin is the point at the start of the line
    # and end is the one at the newline character. The line boundaries are all
    # the beginnings and the trailing end.

    def make_linebreak(point):
        return _colorable_region((point, point), None, None)

    def linebreak((extent, fg_color, bg_color_stack)):
        return (fg_color is None) and (bg_color_stack is None)

    linebreaks = map(make_linebreak, [L[0] for L in lines] + [lines[-1][1]])

    # We make use of the heap property to efficiently split the regions into
    # disjoint parts with a sweeping line algorithm. The resulting region list
    # also gets automagically sorted.

    def heap_min(heap):
        return heap[0]

    def heap_min_next(heap):
        return min(heap[1], heap[2]) if len(heap) > 2 else heap[1]

    regions = regions[:]
    regions.extend(linebreaks)
    heapify(regions)

    # Actually, bracket scopes do not strictly _overlap_. They are _contained_
    # inside each other. But this is assumed and the strict check is omitted.

    def overlap(left, right):
        (begin1, end1), (begin2, end2) = _extent(left), _extent(right)
        return begin2 < end1

    def split(outer, inner):
        def split((begin1, end1), (begin2, end2)):
            return (begin1, begin2), (end2, end1)

        _, fg_color, bg_color_stack = outer
        extent1, extent2 = split(_extent(outer), _extent(inner))

        return _colorable_region(extent1, fg_color, bg_color_stack), \
               _colorable_region(extent2, fg_color, bg_color_stack)

    result = []
    while len(regions) > 1:
        leftmost, next_one = heap_min(regions), heap_min_next(regions)
        # Invariant: leftmost must be disjoint from all other regions

        if overlap(leftmost, next_one):
            leftmost, following = split(leftmost, next_one)
            heapreplace(regions, following)
        else:
            heappop(regions)

        if not linebreak(leftmost):
            result.append(leftmost)

    last_region = regions[0]
    if not linebreak(last_region):
        result.append(last_region)

    return result


def fixup_background(colorable_regions, line_extents):
    """
    TODO
    """
    def contains((begin1, end1), (begin2, end2)):
        return (begin2 <= begin1) and (end1 <= end2)

    def prepend_background((extent, fg_color, bg_color_stack)):
        for line in line_extents:
            if contains(extent, line):
                bg_color_stack = [(CURRENT_LINE, None)] + bg_color_stack
                break
        else:
            bg_color_stack = [(BACKGROUND, None)] + bg_color_stack

        return _colorable_region(extent, fg_color, bg_color_stack)

    return map(prepend_background, colorable_regions)


def infer_region_color((extent, fg_color, bg_color_stack), config):

    def color_of((kind, index)):
        if kind is BracketKind.PRIMARY:
            return config[BracketColor.PRIMARY]

        if kind is BracketKind.SECONDARY:
            colors = config[BracketColor.SECONDARY]
            return colors[(index - 1) % len(colors)]

        if kind is BracketKind.OFFSIDE:
            colors = config[BracketColor.OFFSIDE]
            return colors[(index - 1) % len(colors)]

        if kind is BracketKind.ADJACENT:
            return config[BracketColor.ADJACENT]

        if kind is BracketKind.INCONSISTENT:
            return config[BracketColor.INCONSISTENT]

        if kind is CURRENT_LINE:
            return None, config['background_color']

        if kind is BACKGROUND:
            return None, config['current_line_color']

        assert False, "unknown kind %r" % kind

    fg_colo_, bg_colo_ = color_of(fg_color)

    bg = reversed(bg_color_stack)
    while bg_colo_ == TRANSPARENT:
        _, bg_colo_ = color_of(next(bg))

    return fg_colo_, bg_colo_
