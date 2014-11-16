import sublime
import sublime_plugin

from bracket_scopes \
    import cursors_of_view, expand_cursors_to_regions, merge_adjacent_regions, \
           index_brackets, locate_brackets, merge_bracket_indices, \
           compute_bracket_scopes, current_lines_of_view

from bracket_coloring import * # fix
from lisp_highlight_configuration import * # fix too
from types import * # and this
from scope_colors import * # and this as well
from configuration_unification import * # ugh...
import pprint

scan_limit = 100

supported_brackets = [('(', ')'), ('[', ']'), ('{', '}'),]

class LispSelectionListener(sublime_plugin.EventListener):

    def __init__(self):
        settings = sublime.load_settings('LispBracketHighlighter.sublime-settings')
        pprint.pprint(extract_and_unify_configuration(settings))

    def on_selection_modified(self, view):

        theme_filename = current_sublime_theme_file(view)

        add_or_replace_colored_scopes(
            theme_filename,
            format_sublime_color_scopes([(0xEE8888, 0x88EE88)])
        )

        try:
            print(parse_essential_colors(theme_filename))
        except ValueError:
            print("Fucked up: ")

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

                'primary_color': (0x110000, None),
                'secondary_colors': [(0x220000, None), (0x330000, None)],
                'offside_colors': [(0x440000, 0x004400), (0x550000, 0x005500), (0x660000, 0x006600)],
                'adjacent_color': (0x770000, 0x007700),
                'inconsistent_color': (0x880000, 0x008800)
            })

            rgc = color_scopes(indexed_bracket_scopes, config, cursors, supported_brackets)
            #print("rgc:", rgc)

            lines = current_lines_of_view(view, cursors)
            #print("l:  ", lines)

            dj = split_into_disjoint(rgc, lines)
            #print("dj: ", dj)

            fu = prepend_background(dj, lines)
            #print("fu: ", fu)

            colored_regions = {}
            for region in fu:
                color = compute_span_color(region, config)

                regions = colored_regions.get(color, [])
                regions.append(region.extent)

                colored_regions[color] = regions
            #print("cr: ", colored_regions)

            altogether = []
            for color, regions in colored_regions.iteritems():
                altogether.extend(map(Region.as_sublime_region, regions))

            scope_name = scope_name_for_color(0xEE8888, 0x88EE88)

            view.erase_regions(scope_name)
            view.add_regions(scope_name, altogether, scope_name)
