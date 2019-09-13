from numpy.ma.core import MaskedConstant


def unpack_masked_constant(value, fill_value=float('nan')):
    if isinstance(value, MaskedConstant):
        return fill_value
    else:
        return value
