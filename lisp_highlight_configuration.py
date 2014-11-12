from utils import make_enum

ColorMode = make_enum('NONE', 'BRACKETS', 'EXPRESSION')

class AdjacentMode: # flags
    NONE  = 0
    LEFT  = 1
    RIGHT = 2
    BOTH  = 3

RegionColor = make_enum('PRIMARY', 'SECONDARY', 'OFFSIDE', 'ADJACENT',
    'INCONSISTENT', 'BACKGROUND', 'CURRENT_LINE')

def is_transparent(color):
    return color == Configuration.TRANSPARENT_COLOR

class Configuration:

    TRANSPARENT_COLOR = -1

    def __init__(self, config):
        # Temporary hardcoded keys
        self.mode = {}
        self.mode[RegionColor.PRIMARY] = config['primary_mode']
        self.mode[RegionColor.SECONDARY] = config['secondary_mode']
        self.mode[RegionColor.OFFSIDE] = config['offside_mode']
        self.mode[RegionColor.ADJACENT] = config['adjacent_mode']
        self.mode[RegionColor.INCONSISTENT] = config['inconsistent_mode']

        self.offside_limit = config['offside_limit']

        adjacent_side_mode = config['adjacent_side']
        self.adjacent_left = bool(adjacent_side_mode & AdjacentMode.LEFT)
        self.adjacent_right = bool(adjacent_side_mode & AdjacentMode.RIGHT)

        self.color = {}
        self.color[RegionColor.PRIMARY] = config['primary_color']
        self.color[RegionColor.SECONDARY] = config['secondary_colors']
        self.color[RegionColor.OFFSIDE] = config['offside_colors']
        self.color[RegionColor.ADJACENT] = config['adjacent_color']
        self.color[RegionColor.INCONSISTENT] = config['inconsistent_color']
        self.color[RegionColor.BACKGROUND] = config['background_color']
        self.color[RegionColor.CURRENT_LINE] = config['current_line_color']
