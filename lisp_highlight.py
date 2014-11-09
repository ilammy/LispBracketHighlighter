import sublime
import sublime_plugin

from bracket_scopes \
    import cursors_of_view, expand_cursors_to_regions, merge_adjacent_regions, \
           index_brackets, locate_brackets, merge_bracket_indices, \
           compute_bracket_scopes, filter_consistent_scopes, \
           primary_mainline_scope, secondary_mainline_scopes, offside_scopes, \
           adjacent_scopes, scope_bracket_regions, scope_expression_region

from bracket_coloring import * # fix
from lisp_highlight_configuration import * # fix too

scan_limit = 100

supported_brackets = [('(', ')'), ('[', ']'), ('{', '}'),]

class LispSelectionListener(sublime_plugin.EventListener):

    def on_selection_modified(self, view):

        cursors = cursors_of_view(view)
        #print("c: ", cursors)

        expanded_regions = expand_cursors_to_regions(cursors, scan_limit, view)
        #print("xr: ", expanded_regions)

        examined_regions = merge_adjacent_regions(expanded_regions, cursors)
        #print("er: ", examined_regions)

        def no_strings_and_comments(scope):
            return ("comment" not in scope) and ("string" not in scope)

        for region, cursors in examined_regions:

            brackets = locate_brackets(view, region, supported_brackets, no_strings_and_comments)
            #print("b: ", brackets)

            per_cursor_indices = [index_brackets(brackets, cursor) for cursor in cursors]
            #print("pci: ", per_cursor_indices)

            merged_indices = merge_bracket_indices(per_cursor_indices)
            #print("mi: ", merged_indices)

            indexed_bracket_scopes = compute_bracket_scopes(brackets, merged_indices)
            #print("ibs: ", indexed_bracket_scopes)

            consistent_scopes, inconsistent_scopes = \
                filter_consistent_scopes(indexed_bracket_scopes, supported_brackets)
            #print("cs: ", consistent_scopes)
            #print("is: ", inconsistent_scopes)

            config = Configuration({
                'primary_mode': ColorMode.EXPRESSION,
                'secondary_mode': ColorMode.EXPRESSION,
                'offside_mode': ColorMode.BRACKETS,
                'offside_limit': 2,
                'adjacent_mode': ColorMode.EXPRESSION,
                'adjacent_side': AdjacentMode.BOTH,
                'invalid_mode': ColorMode.NONE,
                'inconsistent_mode': ColorMode.NONE,

                'background_color': (None, 0x123456),
                'current_line_color': (None, 0x789ABC),

                'primary_color': (0x110000, Configuration.TRANSPARENT_COLOR),
                'secondary_colors': [(0x220000, Configuration.TRANSPARENT_COLOR), (0x330000, Configuration.TRANSPARENT_COLOR)],
                'offside_colors': [(0x440000, 0x004400), (0x550000, 0x005500), (0x660000, 0x006600)],
                'adjacent_color': (0x770000, 0x007700),
                'inconsistent_color': (0x880000, 0x008800)
            })

            rgc = color_scopes(indexed_bracket_scopes, config, cursors, supported_brackets)
            #print("rgc:", rgc)

            def as_tuple(region):
                return region.begin(), region.end()

            # can improve by merging consecutive lines
            lines = [as_tuple(view.line(cursor)) for cursor in cursors]

            dj = split_into_disjoint(rgc, lines)
            #print("dj: ", dj)

            fu = prepend_background(dj, lines)
            print("fu: ", fu)

            colored_regions = {}
            for region in fu:
                color = compute_region_color(region, config)

                regions = colored_regions.get(color, [])
                regions.append(extent(region))

                colored_regions[color] = regions

            print("cr: ", colored_regions)

            print ('----')

