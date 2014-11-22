import sublime
import re

from unify import boolean, string, integer, either, optional, unify

from utils import css_colors

#
# Helper matchers
#

def long_hex_triplet(value):
    """Matches and parses full form of hex triplets."""
    triplet = re.match(r'#?([0-9a-fA-F]{6})', string(value))

    if not triplet:
        raise ValueError("'%s' is not a long hex triplet" % value)

    return int(triplet.group(1), 16)


def short_hex_triplet(value):
    """Matches and parses short form of hex triplets."""
    triplet = re.match(r'#?([0-9a-fA-F]{3})', string(value))

    if not triplet:
        raise ValueError("'%s' is not a short hex triplet" % value)

    temp = int(triplet.group(1), 16)
    return (((temp & 0xF00) << 20) | ((temp & 0xF00) << 16) |
            ((temp & 0x0F0) << 12) | ((temp & 0x0F0) <<  8) |
            ((temp & 0x00F) <<  4) | ((temp & 0x00F) <<  0))


def css_color_name(value):
    """Matches and converts CSS3 named colors."""
    color = string(value).lower()

    if color not in css_colors:
        raise ValueError("'%s' is not a CSS color" % color)

    return css_colors[color]


def true_color_integer(value):
    """Matches intergers that encode True Color colors."""
    color = integer(value)

    if not ((0 <= color) and (color < 2**24)):
        raise ValueError("%d is not in True Color 24-bit range" % color)

    return color


def positive_integer(value):
    """Matches positive intergers."""
    value = integer(value)

    if value <= 0:
        raise ValueError("%d is not positive" % value)

    return value

#
# Procedural helpers
#

def either_key(*keys):
    """Asserts that an object contains not more than one of the given keys."""
    def matcher(object):
        defined_keys = \
            filter(lambda key: (key in object) and (object[key] is not None),
                   keys)

        if len(defined_keys) > 1:
            defined_keys = ", ".join(map(repr, defined_keys))
            raise ValueError("cannot use %s simulatenously" % defined_keys)

    return matcher


def unify_color_spec(color, mode):
    """Unifies full and short forms of color specs."""
    foreground, background = None, None

    if color:
        if isinstance(color, dict):
            foreground = color["foreground"]
            background = color["background"]
        else:
            if mode == "brackets":
                foreground = color
            else:
                background = color

    if (foreground is None) and (background is None):
        return None
    else:
        return foreground, background


def unify_color(scope_object):
    """Unifies color specs in single-colored scope settings."""
    scope_object["color"] = \
        unify_color_spec(scope_object["color"], scope_object["mode"])


def unify_colors(scope_object):
    """Unifies color specs in multi-colored scope settings."""
    if scope_object["color"] is not None:
        colors = [scope_object["color"]]
    elif scope_object["colors"] is not None:
        colors = scope_object["colors"]
    else:
        colors = []

    mode = scope_object["mode"]

    scope_object["colors"] = \
        filter(lambda color: color is not None,
            map(lambda color: unify_color_spec(color, mode), colors))

    del scope_object["color"]


def disable_if_no_color(scope_object):
    """Disables scope highlighting if it has no defined colors."""
    if not scope_object["color"]:
        scope_object["enabled"] = False


def disable_if_no_colors(scope_object):
    """Disables scope highlighting if it has no defined colors."""
    if not scope_object["colors"]:
        scope_object["enabled"] = False


def unify_syntax(override_object):
    """Unifies syntax specs in language overrides."""
    syntax = override_object["syntax"]

    if isinstance(syntax, list):
        if not syntax:
            raise ValueError('"syntax" list cannot be empty')
    else:
        syntax = [syntax]

    override_object["syntax"] = syntax


def reformat_overrides(configuration_object):
    """Rearranges the plain list of overrides to be a language-keyed dict."""
    overrides = {}

    for override in configuration_object["overrides"]:
        for syntax in override["syntax"]:
            overrides[syntax] = override
        del override["syntax"]

    configuration_object["overrides"] = overrides


#
# Patterns
#

"""Supported color spec patterns."""
color_spec = \
    either( long_hex_triplet
          , short_hex_triplet
          , css_color_name
          , true_color_integer
          , None
          )


"""Full/short color specs."""
color_pattern = \
    either( {
                "foreground": optional(color_spec),
                "background": optional(color_spec)
            }
          , color_spec
          , None
          )


"""Main configuration file pattern."""
configuration_pattern = \
{
    "enabled":  optional(boolean, True),
    "brackets": [(string, string)],
    "primary":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "__extra__": [unify_color, disable_if_no_color]
    },
    "secondary":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "colors":  optional([color_pattern]),
        "depth limit": optional(positive_integer),
        "__extra__": [either_key("color", "colors"),
            unify_colors, disable_if_no_colors]
    },
    "offside":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "colors":  optional([color_pattern]),
        "depth limit": optional(positive_integer),
        "__extra__": [either_key("color", "colors"),
            unify_colors, disable_if_no_colors]
    },
    "adjacent":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "chirality": optional(either("none", "left", "right", "both"), "none"),
        "__extra__": [unify_color, disable_if_no_color]
    },
    "inconsistent":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "__extra__": [unify_color, disable_if_no_color]
    },
    "scope blacklist": [string],
    "overrides":
    [
        {
            "syntax": either(string, [string]),

            "brackets":            optional([(string, string)]),
            "additional brackets": optional([(string, string)]),

            "scope blacklist":            optional([string]),
            "additional scope blacklist": optional([string]),

            "__extra__": [unify_syntax,
                either_key("brackets", "additional brackets"),
                either_key("scope blacklist", "additional scope blacklist")],

            "enabled": optional(boolean),

            "primary":
            {
                "enabled": optional(boolean),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "__extra__": [unify_color]
            },
            "secondary":
            {
                "enabled": optional(boolean, True),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "colors":  optional([color_pattern]),
                "depth limit": optional(positive_integer),
                "__extra__": [either_key("color", "colors"), unify_colors]
            },
            "offside":
            {
                "enabled": optional(boolean, True),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "colors":  optional([color_pattern]),
                "depth limit": optional(positive_integer),
                "__extra__": [either_key("color", "colors"), unify_colors]
            },
            "adjacent":
            {
                "enabled": optional(boolean),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "chirality": optional(either("none", "left", "right", "both")),
                "__extra__": [unify_color]
            },
            "inconsistent":
            {
                "enabled": optional(boolean),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "__extra__": [unify_color]
            }
        }
    ],
    "__extra__": [reformat_overrides]
}

#
# Configuration processing
#

def extract_and_unify_configuration(sublime_settings):
    """Parses, verifies and unifies LispBracketHighlighter settings.

    Args:
        sublime_settings - a sublime.Settings object to be parsed

    Returns:
        a dict with extracted configuration options and filled in defaults

    Raises:
        ValueError - on parse failures
    """
    settings = {
        'enabled':          sublime_settings.get('enabled',         True),
        'brackets':         sublime_settings.get('brackets',        []),
        'primary':          sublime_settings.get('primary',         {}),
        'secondary':        sublime_settings.get('secondary',       {}),
        'offside':          sublime_settings.get('offside',         {}),
        'adjacent':         sublime_settings.get('adjacent',        {}),
        'inconsistent':     sublime_settings.get('inconsistent',    {}),
        'scope blacklist':  sublime_settings.get('scope blacklist', []),
        'overrides':        sublime_settings.get('overrides',       []),
    }
    return unify(settings, configuration_pattern)
