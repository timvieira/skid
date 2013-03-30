# *-- coding: utf-8 -*-
import re

def lastname(name):
    """
    Extract author last name from string `name`.

    TODO: Cover "Lastname, First M."
    TODO: Consider using a name parser

    Ignores roman numeral suffixes.

    >>> print lastname("John Doe VI")
    Doe
    """
    return [w for w in name.strip().split() if not re.match('^[VIX]+$',w)][-1]
