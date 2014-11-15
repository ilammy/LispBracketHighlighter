import xml.etree.ElementTree as xml

def parse(filename):
    """
    """
    document = xml.parse(filename)
    plist = document.getroot()

    if plist.tag != 'plist':
        raise ValueError("Expected <plist> root, got <%s>" % plist.tag)
    if len(plist) == 0:
        raise ValueError("Expected <dict>, got empty <plist>")

    main_dict = plist[0]
    if main_dict.tag != 'dict':
        raise ValueError("Expected <dict>, got <%s>" % main_dict.tag)

    return main_dict


def dict_get(dict, key):
    """
    """
    if dict.tag != 'dict':
        raise ValueError("<%s> is not a <dict>" % dict.tag)

    # xml.etree.ElementTree.Element iteration is shitty :(

    i, lim = 0, len(dict)
    while i < lim:
        element = dict[i]

        if element.tag != 'key':
            raise ValueError('Expected <key>, got <%s>' % element.tag)

        if element.text == key:
            if (i + 1) == lim:
                raise ValueError("Missing value for key '%s'" % key)
            else:
                return dict[i + 1]

        i += 2

    return None


def make_dict():
    """
    """
    return xml.Element('dict')


def dict_add_key(dict, key, value):
    """
    """
    key_element = xml.Element('key')
    key_element.text = key

    dict.append(key_element)
    dict.append(value)


def array_get(array, index):
    """
    """
    if array.tag != 'array':
        raise ValueError("<%s> is not an <array>" % array.tag)

    if len(array) <= index:
        raise ValueError("Array has no index %d (only %d elements)" \
                         % (index, len(array)))

    return array[index]


def string_value(string):
    """
    """
    if string.tag != 'string':
        raise ValueError("<%s> is not a <string>" % string.tag)

    return string.text


def make_string(string):
    """
    """
    string_element = xml.Element('string')
    string_element.text = string
    return string_element
