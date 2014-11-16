def make_enum(*names):
    """Constructs a new enumeration type for the given list of values."""
    class enum_type:
        def __init__(self, name): self.name = name
        def __str__(self): return self.name
        def __repr__(self): return self.name

        def __eq__(self, other):
            return (self is other)

        def __hash__(self):
            return hash((self.name, enum_type))

    enums = dict(zip(names, map(enum_type, names)))
    return type('Enum', (), enums)
