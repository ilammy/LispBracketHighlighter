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
    },
    "secondary":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "colors":  optional([color_pattern]),
        "depth limit": optional(positive_integer),
    },
    "offside":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "colors":  optional([color_pattern]),
        "depth limit": optional(positive_integer),
    },
    "adjacent":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
        "chirality": optional(either("none", "left", "right", "both"), "none"),
    },
    "inconsistent":
    {
        "enabled": optional(boolean, True),
        "mode":    optional(either("none", "brackets", "expression"), "none"),
        "color":   optional(color_pattern),
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

            "enabled": optional(boolean),

            "primary":
            {
                "enabled": optional(boolean),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern)
            },
            "secondary":
            {
                "enabled": optional(boolean, True),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "colors":  optional([color_pattern]),
                "depth limit": optional(positive_integer),
            },
            "offside":
            {
                "enabled": optional(boolean, True),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "colors":  optional([color_pattern]),
                "depth limit": optional(positive_integer),
            },
            "adjacent":
            {
                "enabled": optional(boolean),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern),
                "chirality": optional(either("none", "left", "right", "both"))
            },
            "inconsistent":
            {
                "enabled": optional(boolean),
                "mode":    optional(either("none", "brackets", "expression")),
                "color":   optional(color_pattern)
            }
        }
    ]
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
