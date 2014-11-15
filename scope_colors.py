import sublime
import re

def compute_possible_scope_colors(color_pairs):
    """Computes all possible colors resulting from transparent backgrounds.

    Args:
        [(fg, bg)] - a list of color tuples to be processed

    Returns:
        [(fg, bg)] - a list of resulting color tuples
    """
    # We can do a better job at determining exact colors, but this is not a hot
    # spot, and writing tons of colored scopes into a configuration file is not
    # a problem as well. So we have clear conscience while going an easy way:

    foregrounds = set([])
    backgrounds = set([])

    for foreground, background in color_pairs:
        foregrounds.add(foreground)
        backgrounds.add(background)

    foregrounds.discard(None)
    backgrounds.discard(None)

    return [(fg, bg) for fg in foregrounds for bg in backgrounds]


def format_sublime_color_scopes(color_pairs):
    """Transforms a list of color tuples into Sublime's XML format for scopes.

    Args:
        [(fg, bg)] - a list of color tuples to be transformed

    Returns:
        xml-string - a string with colors serialized into scope descriptions
    """
    result = ""
    for foreground, background in color_pairs:
        scope_name = scope_name_for_color(foreground, background)
        result += """
            <dict>
                <key>scope</key>
                <string>%s</string>
                <key>settings</key>
                <dict>
                    <key>foreground</key>
                    <string>#%06X</string>
                    <key>background</key>
                    <string>#%06X</string>
                </dict>
            </dict>""" % (scope_name, foreground, background)
    return result


def scope_name_for_color(foreground, background):
    """Returns a name of Sublime scope that has the specified color."""
    return "lisp_highlight.%06X.%06X" % (foreground, background)


def current_sublime_theme_file(view):
    """Returns a path to the theme file used by Sublime for the given view."""
    basedir = sublime.packages_path() # $SUBLIME_INSTALL_DIR/Data/Packages
    color_scheme = view.settings().get('color_scheme') # Packages/...
    return basedir[:-8] + color_scheme


def add_or_replace_colored_scopes(theme_filename, serialized_scopes):
    """Updates a theme file with colored scopes.

    Args:
        theme_filename - the path to the theme file to update

        serialized_scopes - a string with new colored scopes serialized in XML
    """
    # Theme files (usually) have reasonable size and should fit into RAM.

    with open(theme_filename, 'r') as theme_file:
        theme_file_contents = theme_file.read()

    in_pattern = r'(?:<!--LispHighlight-->.*<!--/LispHighlight-->)?\s*</array>'
    out_pattern = '<!--LispHighlight-->%s\n<!--/LispHighlight-->\n\t</array>'

    matcher = re.compile(in_pattern, re.DOTALL)

    theme_file_contents = \
        matcher.sub(out_pattern % serialized_scopes, theme_file_contents)

    with open(theme_filename, 'w') as theme_file:
        theme_file.write(theme_file_contents)


def parse_essential_colors(theme_filename):
    """Extract essential colors from a theme file.

    The essential colors are: text color, background color, and current line
    background color.

    Args:
        theme_filename - the path to the theme file to examine

    Returns:
        (text, background, current_line)
            - the extracted colors, as 24-bit integers, None if missing

    Raises:
        ValueError - on parse failures
    """
    def compile(pattern): return re.compile(pattern, re.DOTALL)

    toplevel_settings = compile(r'<array>.*?<key>settings</key>')
    toplevel_settings_limit = compile(r'</dict>')

    foreground = compile(r'<key>foreground</key>.*?<string>#([0-9A-Fa-f]{6})</string>')
    background = compile(r'<key>background</key>.*?<string>#([0-9A-Fa-f]{6})</string>')
    lhighlight = compile(r'<key>lineHighlight</key>.*?<string>#([0-9A-Fa-f]{6})</string>')

    # Theme files (usually) have reasonable size and should fit into RAM.

    with open(theme_filename, 'r') as theme_file:
        theme_file_contents = theme_file.read()

    start = toplevel_settings.search(theme_file_contents)
    if not start:
        raise ValueError("Could not locate toplevel settings start")
    start = start.end()

    end = toplevel_settings_limit.search(theme_file_contents, start)
    if not end:
        raise ValueError("Could not locate toplevel settings end")
    end = end.start()

    fg = foreground.search(theme_file_contents, start, end)
    bg = background.search(theme_file_contents, start, end)
    lh = lhighlight.search(theme_file_contents, start, end)

    if fg: fg = int(fg.group(1), 16)
    if bg: bg = int(bg.group(1), 16)
    if lh: lh = int(lh.group(1), 16)

    return fg, bg, lh
