import sublime
import sublime_plugin

from bracket_scopes \
    import cursors_of_view, expand_cursors_to_regions, merge_adjacent_regions, \
           index_brackets, locate_brackets, merge_bracket_indices, \
           compute_bracket_scopes, filter_consistent_scopes, \
           primary_mainline_scope, secondary_mainline_scopes, offside_scopes, \
           adjacent_scopes, scope_bracket_regions, scope_expression_region

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

        view.erase_regions("pm")
        view.erase_regions("sm")
        view.erase_regions("os")
        view.erase_regions("aj")
        view.erase_regions("iv")

        def no_strings_and_comments(scope):
            return ("comment" not in scope) and ("string" not in scope)

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

            pm_scope = primary_mainline_scope(consistent_scopes)

            sm_scopes = secondary_mainline_scopes(consistent_scopes)

            os_scopes = offside_scopes(consistent_scopes)

            aj_scopes = adjacent_scopes(consistent_scopes, cursors)

            def flatten(scope_pairs):
                res = []
                for a, b in scope_pairs:
                    res.append(a)
                    res.append(b)
                return res

            view.add_regions("pm", flatten(map(scope_bracket_regions, pm_scope)), "string")

            view.add_regions("sm", flatten(map(scope_bracket_regions, sm_scopes)), "comment")

            view.add_regions("os", flatten(map(scope_bracket_regions, os_scopes)), "constant.numeric")

            view.add_regions("aj", map(scope_expression_region, aj_scopes), "entity.name.class")

            view.add_regions("iv", flatten(map(scope_bracket_regions, inconsistent_scopes)), "invalid")
