import sublime

from bisect import bisect_left

#
# Cursors and regions
#

def cursors_of_view(view):
    """Locates points of all cursors of the view.

    Args:
        view - an instance of sublime.View where to look for cursors

    Returns:
        [point] - a list of cursor points
    """
    return [region.begin() for region in view.sel() if region.empty()]


def expand_cursors_to_regions(cursors, amount, view):
    """Computes the vicinities of the cursors.

    Args:
        [cursors] - a list of cursors that will be centers of the regions

        amount - radius (in points) of the desired regions

        view - the sublime.View the cursors are from

    Returns:
        [(begin, end)] - a list of regions (as tuples of points)
                         that correspond to the cursors
    """
    view_size = (0, view.size() - 1)

    def clamp_expand(cursor, amount, (left, right)):
        begin, end = cursor - amount, cursor + amount
        if begin < left: begin = left
        if end > right: end = right
        return begin, end

    return [clamp_expand(cursor, amount, view_size) for cursor in cursors]


def merge_adjacent_regions(regions, cursors):
    """Merges overlapping regions and computes the cursors contained in them.

    Args:
        [regions] - a list of regions obtained by expanding the cursors

        [cursors] - a list of cursors that are the centers of the regions

    Returns:
        [((begin, end), [cursors])]
            - a list of tuples of disjoint regions and their contained cursors
    """
    if not regions: return []

    def intersect((b1, e1), (b2, e2)): return (e1 >= b2)
    def merge((b1, e1), (b2, e2)): return (b1, e2)

    current_region = regions[0]
    current_cursors = set([cursors[0]])

    result = []

    for next_region, next_cursor in zip(regions[1:], cursors[1:]):
        if intersect(current_region, next_region):
            current_region = merge(current_region, next_region)
            current_cursors.add(next_cursor)
        else:
            result.append((current_region, list(current_cursors)))
            current_region = next_region
            current_cursors = set([next_cursor])

    result.append((current_region, list(current_cursors)))
    return result

#
# Brackets
#

# Brackets are represented as (type, point, kind) tuples
#   type  - 0 for left brackets, 1 for right ones
#   point - a point in the view where the bracket is located
#   kind  - textual representation of the bracket

_LEFT_BRACKET = 0
_RIGHT_BRACKET = 1

def _left_bracket(point, kind): return (_LEFT_BRACKET, point, kind)
def _right_bracket(point, kind): return (_RIGHT_BRACKET, point, kind)

def _is_left(bracket): return bracket[0] == _LEFT_BRACKET
def _is_right(bracket): return bracket[0] == _RIGHT_BRACKET


def locate_brackets(view, (begin, end), supported_brackets, suitable_scope):
    """Locates all brackets in the specified region of the view.

    Args:
        view - a sublime.View to scan for brackets

        begin, end - the exact region in the view to scan through

        [supported_brackets]
            - a list of (left_bracket, right_bracket) tuples of strings
              that specify textual representation of the brackets

        suitable_scope
            - a predicate of signature (scope) that tells whether
              the given scope should be checked for brackets
    Returns:
        [bracket] - a list of brackets that were found
    """
    def substring_matches_at(point, haystack, needle):
        region = sublime.Region(point, point + len(needle))
        return haystack.substr(region) == needle

    # We assume that brackets match unambiguously: i.e., a bracket must not be
    # a prefix of some other bracket (though, they may be textually equal).

    brackets = []

    point = begin
    while point < end:

        if suitable_scope(view.scope_name(point)):

            for left, right in supported_brackets:

                if substring_matches_at(point, view, left):
                    brackets.append(_left_bracket(point, left))
                    point += len(left) - 1
                    break

                if substring_matches_at(point, view, right):
                    brackets.append(_right_bracket(point, right))
                    point += len(right) - 1
                    break

        point += 1

    return brackets

#
# Indexing
#

def index_brackets(brackets, cursor):
    """Assigns nesting indices to brackets relative to the given cursor.

    Nesting index is a tuple of (outer_nesting_level, inner_nesting_level)
    which are integers that describe how deeply the given bracket is nested
    inside the text.

    A picture is worth a thousand of words, so here is an explanation of
    the principle by which the brackets get their indices. Consider the
    following bracket expression, the cursor is marked with a vertical bar:

        ((()((())()(|())(()(()))))())

    The brackets here receive the following indices:

        ( ( ( ) ( ( ( ) ) ( ) ( ( ) ) ( ( ) ( ( ) ) ) ) ) ( ) )     bracket
                               |
        3 2 1 1 1 0 0 0 0 0 0 0 - - 0 0 0 0 0 0 0 0 0 1 2 2 2 3     outer
        0 0 1 1 0 1 2 2 1 1 1 0 1 1 0 1 2 2 2 3 3 2 1 0 0 1 1 0     inner

    which may be a bit confusing... until you arrage the brackets like this,
    trying to guess their nesting level:

        (                      |                              )
          (                    |                        ) ( )
            ( ) (              |                      )
                  (     ) ( ) (|    ) (             )
                    ( )        |( )     ( ) (     )
                               |              ( )  
    
    Then, by considering the 'distance' of the bracket pair from the cursor,
    we can divide the brackets into layers:
                                                                  outer   inner
        (                      |                              )     3       0
        - - - - - - - - - - - -|- - - - - - - - - - - - - - - -         
          (                    |                        )           2       0
                               |                          ( )               1
        - - - - - - - - - - - -|- - - - - - - - - - - - - - - -         
                (              |                      )             1       0
            ( )                |                                            1
        - - - - - - - - - - - -|- - - - - - - - - - - - - - - -         
                              (|    )                               0       0
                  (     ) ( )  |      (             )                       1
                    ( )        |        ( ) (     )                         2
                               |              ( )                           3
        - - - - - - - - - - - -|- - - - - - - - - - - - - - - -         
                               |( )                                -1       1

    Now you can see a few simple patterns here:

      - matching brackets have matching indices

      - for each outer index level there is at most one bracket pair with
        zero inner index, it is called 'mainline' that contains the cursor

      - inner index tells how many nesting levels should be crossed to get
        from this bracket to the mainline bracket of the same outer index

      - outer index tells how many mainline bracket pairs should be crossed
        from outside the expression to get to the nesting level of the cursor

    Args:
        [brackets] - a list of brackets to index

        cursor - the cursor which is used as a kernel

    Returns:
        [indices] - a list of indices assigned to brackets
    """
    def cursor_insertion_index(cursor, brackets):
        """Returns the index of the bracket immediately following the cursor."""
        # The bracket with the index returned will the first bracket that is
        # located to the right of the cursor's point. Special arrangements
        # need to be done for multicharacter left brackets to ensure that
        # they are treated by bisect_left as 'located to the left' only
        # when they are _entirely_ located to the left of the cursor.
        def bracket_point((type, point, kind)):
            if type == _RIGHT_BRACKET:
                return point
            else:
                return point + len(kind) - 1

        return bisect_left(map(bracket_point, brackets), cursor)

    cii = cursor_insertion_index(cursor, brackets)

    def index_left(brackets, cii):
        """Indexes brackets located to the left of the cursor."""
        left_indices = []
        outer_depth = -1
        next_depth = 0

        for left_bracket in map(_is_left, reversed(brackets[0:cii])):
            inner_depth = next_depth

            if left_bracket:
                if next_depth == 0:
                    outer_depth += 1
                else:
                    next_depth -= 1
            else:
                next_depth += 1
                inner_depth += 1

            left_indices.append((outer_depth, inner_depth))

        left_indices.reverse()
        return left_indices

    def index_right(brackets, cii):
        """Indexes brackets located to the right of the cursor."""
        right_indices = []
        outer_depth = -1
        next_idepth = 0

        for right_bracket in map(_is_right, brackets[cii:]):
            inner_depth = next_idepth

            if right_bracket:
                if next_idepth == 0:
                    outer_depth += 1
                else:
                    next_idepth -= 1
            else:
                next_idepth += 1
                inner_depth += 1

            right_indices.append((outer_depth, inner_depth))

        return right_indices

    return index_left(brackets, cii) + index_right(brackets, cii)


def merge_bracket_indices(per_cursor_indices):
    """Merges indices assigned to brackets from several cursors.

    The reasonable way to combine indices from two different cursors is
    to take a minimum; because index of a bracket is the amount of nesting
    levels that need to be crossed to get from the bracket to the cursor.
    Therefore, it's pretty logical to take the shortest available path.

    The only peculiarity is the outer index -1 that should not be considered
    lesser than index 0. Conversely, -1 should be treated as +Infinity because
    it marks brackets that are unreachable along the shortest path between the
    cursor and the outside of the bracket expression.

    Args:
        [per_cursor_indices]
            - a list of index lists assigned to the same bracket set
              over a set of cursors
    Returns:
        [indices] - the resulting flattened index list for the brackets
    """
    def outer_min(o1, o2):
        return max(o1, o2) if (o1 == -1) or (o2 == -1) else min(o1, o2)

    def index_minimum(((o1, i1), (o2, i2))):
        return outer_min(o1, o2), min(i1, i2)

    def merge_indices(current_min, next):
        return map(index_minimum, zip(current_min, next))

    return reduce(merge_indices, per_cursor_indices)

#
# Scopes
#

# Bracket scopes are represented as (index, region, kinds) tuples
#   index  - nesting index of the bracket pair
#   region - a pair of points of the left and right brackets
#   kinds  - a pair of string representations of the brackets

def _bracket_scope(index, left_bracket, right_bracket):
    _, left_point, left_kind = left_bracket
    _, right_point, right_kind = right_bracket
    return index, (left_point, right_point), (left_kind, right_kind)

def _index(scope): return scope[0]
def _outer_index(scope): return scope[0][0]
def _inner_index(scope): return scope[0][1]


def scope_bracket_regions((index, (begin, end), (left, right))):
    """Constructs sublime.Regions bound to the brackets of the scope.

    Args:
        scope - the scope in question

    Returns:
        left, right - a pair of sublime.Region objects that delimit
                      the brackets of the scope
    """
    return sublime.Region(begin, begin + len(left)), \
           sublime.Region(end,   end   + len(right))


def scope_expression_region((index, (begin, end), (left, right))):
    """Constructs a sublime.Region bound to the extents of the scope.

    Args:
        scope - the scope in question

    Returns:
        expression_scope
            - the sublime.Region object that delimits the scope
              (the inside of the scope as well as its brackets)
    """
    return sublime.Region(begin, end + len(right))


def compute_bracket_scopes(brackets, indices):
    """Computes bracket scopes from brackets and their indices.

    A pair of 'matching' brackets form a scope. Brackets match when they are
    the left and right one, and have the same index. Each bracket can belong
    to at most one scope. A bracket can belong to no scope if the region does
    not include the corresponding matching bracket.

    Args:
        [brackets] - a list of brackets where the scopes are to be found

        [indices] - a list of indices of the corresponding brackets

    Returns:
        [scopes] - the resulting list of bracket scopes
    """
    def indices_equal((o1, i1), (o2, i2)):
        return (o1 == o2) and (i1 == i2)

    scopes = []

    indexed_brackets = zip(indices, brackets)

    for i, (left_index, left_bracket) in enumerate(indexed_brackets):
        if _is_right(left_bracket): continue

        remaining_brackets = enumerate(indexed_brackets[i+1:], i+1)
        for j, (right_index, right_bracket) in remaining_brackets:
            if _is_left(right_bracket): continue

            if indices_equal(left_index, right_index):
                scopes.append(_bracket_scope(left_index, left_bracket, right_bracket))
                break

    return scopes

#
# Scope filters
#

def filter_consistent_scopes(scopes, supported_brackets):
    """Partitions scopes in two sets by consistency.

    A scope is consistent when its left and right brackets form a consistent
    pair of brackets that are supported, e.g., ( and ) but not #[ and ).

    Args:
        [scopes] - a list of scopes to be partitioned

        [supported_brackets] - a list of allowed bracket pairs

    Returns:
        [consistent], [inconsistent] - the resulting partitioned scopes
    """
    def partition(predicate, sequence):
        true, false = [], []
        for element in sequence:
            (true if predicate(element) else false).append(element)
        return true, false

    def is_consistent((index, range, bracket_pair)):
        return bracket_pair in supported_brackets

    return partition(is_consistent, scopes)


def primary_mainline_scope(scopes):
    """Locates the primary mainline scope in a list of scopes.

    Args:
        [scopes] - a list of scopes to be examined

    Returns:
        [scope] - the primary mainline scope (as a list, empty if not found)
    """
    return filter(lambda scope: _index(scope) == (0, 0), scopes)


def secondary_mainline_scopes(scopes):
    """Locates the secondary mainline scopes in a list of scopes.

    Args:
        [scopes] - a list of scopes to be examined

    Returns:
        [scopes] - a list of secondary mainline scopes
    """
    return filter(lambda scope: _inner_index(scope) == 0, scopes)


def offside_scopes(scopes):
    """Locates the offside scopes in a list of scopes.

    Args:
        [scopes] - a list of scopes to be examined

    Returns:
        [scopes] - a list of offside scopes
    """
    return filter(lambda scope: _inner_index(scope) > 0, scopes)


def adjacent_scopes(scopes, cursors):
    """Locates the scopes that are adjacent to the given set of cursors.

    Args:
        [scopes] - a list of scopes to be examined

        [cursors] - a list of cursor points to be tested for adjacency

    Returns:
        [scopes] - a list of adjacent scopes
    """
    # Endpoints are points that touch the scope's brackets, but not its inside.
    # E.g., for a scope like this: <<<< ... >>>>, the endpoints would be these:
    # [<<<<) ... (>>>>], with brackets inclusive and parentheses exclusive.
    def endpoints((index, (begin, end), (left, right))):
        return range(begin, begin + len(left)) + \
               range(end + 1, end + len(right) + 1)

    result = []
    for scope, endpoints in zip(scopes, map(endpoints, scopes)):
        for cursor in cursors:
            if cursor in endpoints:
                result.append(scope)
                break
    return result
