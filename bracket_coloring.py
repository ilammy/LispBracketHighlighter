import sublime

from heapq import heapify, heappop, heapreplace

from lisp_highlight_configuration \
    import ColorMode, RegionColor, Configuration, is_transparent

from types import Region, Scope, ColorableSpan


def color_scopes(scopes, config, cursors, supported_brackets):
    """Splits and transforms the scopes into colorable regions.

    The result of this transform is a list of _visible_ regions,
    exact appearance of which is controlled by the `config`.

    Args:
        [scopes] - a sorted list of scopes to get transformed

        config - the Configuration to use

        [cursors] - a list of current cursors

        [supported_brackets]
            - a list of (left, right) pairs of strings that denote
              the valid kinds of brackets

    Returns:
        [colorable_regions] - a list of resulting colorable regions
    """
    def color_type_of(scope):
        if scope.is_not_consistent_with(supported_brackets):
            return RegionColor.INCONSISTENT, None

        if scope.is_primary_mainline():
            return RegionColor.PRIMARY, None

        if scope.is_secondary_mainline():
            return RegionColor.SECONDARY, scope.outer_index

        if scope.is_adjacent_to(cursors):
            return RegionColor.ADJACENT, None

        if scope.is_offside():
            return RegionColor.OFFSIDE, scope.inner_index

    def extents_of(scope, mode):
        if mode is ColorMode.NONE:
            return []

        if mode is ColorMode.BRACKETS:
            return list(scope.bracket_regions())

        if mode is ColorMode.EXPRESSION:
            return [scope.expression_region()]

    def suitable(scope, (kind, index)):
        if kind is RegionColor.OFFSIDE:
            return index <= config.offside_limit

        if kind is RegionColor.ADJACENT:
            need_left = config.adjacent_left
            need_right = config.adjacent_right

            for cursor in cursors:
                if (need_left and scope.left_bracket.contains(cursor)) or \
                   (need_right and scope.right_bracket.contains(cursor)):
                    return True
            else:
                return False

        return True

    def touching(left_scope, right_scope):
        left_region = left_scope.expression_region()
        right_region = right_scope.expression_region()
        return left_region.touches(right_region)

    result = []
    bg_scope_stack = []

    for scope in scopes:
        kind, index = fg_color_type = color_type_of(scope)
        if not suitable(scope, fg_color_type):
            continue

        mode = config.mode[kind]
        if mode is ColorMode.NONE:
            continue

        while bg_scope_stack and not touching(bg_scope_stack[-1], scope):
            bg_scope_stack.pop()

        bg_color_stack = map(color_type_of, bg_scope_stack)

        for extent in extents_of(scope, mode):
            region = ColorableSpan(extent, fg_color_type, bg_color_stack)
            result.append(region)

        if mode is ColorMode.EXPRESSION:
            bg_scope_stack.append(scope)

    return result


def split_into_disjoint(spans, lines):
    """Splits a list of colorable spans into disjoint colorable spans.

    This is necessary as Sublime Text does not handle region intersections
    properly, so we have to split them up by ourselves. Splitting by line
    boundaries is necessary to correctly handle bracket and expression
    backgrounds for current lines.

    Args:
        [spans] - a list of colorable spans to be split

        [lines] - a list of regions denoting the lines

    Returns:
        [spans] - a sorted list of disjoint colorable spans
    """
    if not spans: return []

    # Throwing in fake zero-length spans to denote the line boundaries. They
    # will be used only for splitting and will get filtered out of the results.
    #
    # Lines are (begin, end) where begin is the point at the start of the line
    # and end is the one at the newline character. The line boundaries are all
    # the beginnings and the trailing end.

    def make_linebreak(point):
        return ColorableSpan(Region(point, point), None, None)

    def linebreak(span):
        return (span.foreground is None) and (span.background_stack is None)

    linebreaks = map(make_linebreak, [L.begin for L in lines] + [lines[-1].end])

    # We make use of the heap property to efficiently split the spans into
    # disjoint parts with a sweeping line algorithm. The resulting span list
    # also gets automagically sorted.

    def heap_min(heap):
        return heap[0]

    def heap_min_next(heap):
        return min(heap[1], heap[2]) if len(heap) > 2 else heap[1]

    spans = spans[:]
    spans.extend(linebreaks)
    heapify(spans)

    def overlap(left_span, right_span):
        return left_span.extent.overlaps(right_span.extent)

    def left_touch(span1, span2):
        return span1.extent.begin == span2.extent.begin

    def trim(inner_span, outer_span):
        extent = Region(inner_span.extent.end, outer_span.extent.end)
        foreground = outer_span.foreground
        background_stack = outer_span.background_stack

        return ColorableSpan(extent, foreground, background_stack)

    def split(outer_span, inner_span):
        extent1 = Region(outer_span.extent.begin, inner_span.extent.begin)
        extent2 = Region(inner_span.extent.end, outer_span.extent.end)
        foreground = outer_span.foreground
        background_stack = outer_span.background_stack

        return ColorableSpan(extent1, foreground, background_stack), \
               ColorableSpan(extent2, foreground, background_stack)

    result = []
    while len(spans) > 1:
        leftmost, next_one = heap_min(spans), heap_min_next(spans)
        # Invariant: leftmost must be disjoint from all other spans

        if overlap(leftmost, next_one):
            if left_touch(leftmost, next_one):
                # LL...... -> LL......
                # NNNNN...    ..FFF...
                following = trim(leftmost, next_one)
                heappop(spans)
                heapreplace(spans, following)
            else:
                # LLLLLLL. -> LL...FF.
                # ..NNN...    ..NNN...
                leftmost, following = split(leftmost, next_one)
                heapreplace(spans, following)
        else:
            # LLL.....
            # ....NNN.
            heappop(spans)

        if not linebreak(leftmost):
            result.append(leftmost)

    last_span = spans[0]
    if not linebreak(last_span):
        result.append(last_span)

    return result


def prepend_background(spans, line_extents):
    """Prepends proper terminating background to colorable spans.

    It is necessary to ensure that each colorable span has at least something
    in its background color stack, and that this something is not transparent.
    This will be either a 'current line' background for spans that are located
    in the same line as the cursor or a normal background for everything else.

    Args:
        [spans] - a list of colorable spans to update

        [line_extents] - a list of regions denoting the cursors' lines

    Returns:
        [spans] - a list of updated colorable spans
    """
    def prepend_background(span):
        current_line_color = [(RegionColor.CURRENT_LINE, None)]
        background_color = [(RegionColor.BACKGROUND, None)]

        background_stack = span.background_stack

        for line in line_extents:
            if line.contains(span.extent):
                background_stack = current_line_color + background_stack
                break
        else:
            background_stack = background_color + background_stack

        return ColorableSpan(span.extent, span.foreground, background_stack)

    return map(prepend_background, spans)


def compute_span_color(span, config):
    """Determines the exact color of a span, with transparency removed.

    Args:
        span - a colorable span to be colored

        config - the Configuration to use for picking colors

    Returns:
        (fg, bg) - a tuple of resulting merged color
    """
    def color_of((kind, index)):
        color = config.color[kind]
        if isinstance(color, list):
            color = color[(index - 1) % len(color)]
        return color

    foreground, background = color_of(span.foreground)

    underlying_background = reversed(span.background_stack)
    while is_transparent(background):
        _, background = color_of(next(underlying_background))

    return foreground, background
