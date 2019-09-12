
ISO_CODES = set(['lt', 'bg', 'sw', 'so', 'tl'])
MATERIAL2ISO = {
    '2S': 'bg',
    '2s': 'bg',
    '2B': 'lt',
    '2b': 'lt',
    '1A': 'sw',
    '1a': 'sw',
    '1B': 'tl',
    '1b': 'tl',
    '1S': 'so',
    '1s': 'so',
}

ISO2MATERIAL = {
    'lt': '2B',
    'bg': '2S',
    'sw': '1A',
    'tl': '1B',
    'so': '1S',
}

def is_iso(code):
    return code.lower() in ISO_CODES

def get_iso(code):
    if is_iso(code):
        return code.lower()
    elif code in MATERIAL2ISO:
        return MATERIAL2ISO
    else:
        raise RuntimeError("{} is not a valid iso language code".format(code))

def get_material(code):
    code = code.lower()
    if code in ISO2MATERIAL:
        return ISO2MATERIAL[code]
    else:
        raise RuntimeError(
            "{} is not a valid MATERIAL language code".format(code))
