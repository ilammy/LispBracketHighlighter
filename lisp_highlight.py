import sublime
import sublime_plugin

from bracket_scopes \
    import cursors_of_view, expand_cursors_to_regions, merge_adjacent_regions, \
           index_brackets, locate_brackets, merge_bracket_indices, \
           compute_bracket_scopes, filter_consistent_scopes

scan_limit = 100

supported_brackets = [('(', ')'), ('[', ']'), ('#(', ')'),]

class LispSelectionListener(sublime_plugin.EventListener):

    def on_selection_modified(self, view):

        cursors = cursors_of_view(view)
        #print("c: ", cursors)

        expanded_regions = expand_cursors_to_regions(cursors, scan_limit, view)
        #print("xr: ", expanded_regions)

        examined_regions = merge_adjacent_regions(expanded_regions, cursors)
        #print("er: ", examined_regions)

        ####
        #view.erase_regions("key")
        #view.erase_regions("key2")
        ####

        # TODO: For some unknown reason Sublime Text hangs up if the commented
        #       line is used. This absolutely needs to be resolved as the scope
        #       filtering will be one of the key features of the highlighter.
        def no_strings_and_comments(scope):
            #return ("comment" not in scope) and ("string" not in scope)
            return True

        for region, cursors in examined_regions:

            brackets = locate_brackets(view, region, supported_brackets, no_strings_and_comments)
            #print("b: ", brackets)

            ####
            #view.add_regions("key", map(lambda (f, o, t): sublime.Region(o, o + 1), brackets), "comment")
            #view.add_regions("key2", map(lambda c: sublime.Region(c, c + 1), cursors), "string")
            ####

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

            # TODO: apply scope coloring
