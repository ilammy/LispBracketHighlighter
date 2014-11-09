def make_enum(*names):
    class enum_type:
        def __init__(self, name): self.name = name
        def __str__(self): return self.name
        def __repr__(self): return self.name

    enums = dict(zip(names, map(enum_type, names)))
    return type('Enum', (), enums)
