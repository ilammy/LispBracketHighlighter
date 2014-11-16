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


class dikt:
    """A convenience wrapper that allows to access dict keys as attributes."""
    def __init__(self, dict):
        self.__dict__['dict'] = dict # avoiding infinite regression

    def __str__(self): return str(self.dict)
    def __repr__(self): return repr(self.dict)

    def __getattr__(self, name):
        if name not in self.dict:
            raise AttributeError("No such attribute '%s'" % name)

        return self.dict[name]

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __setattr__(self, name, value):
        if name not in self.dict:
            raise AttributeError("No such attribute '%s'" % name)

        self.dict[name] = value

    def __setitem__(self, name, value):
        return self.__setattr__(name, value)
