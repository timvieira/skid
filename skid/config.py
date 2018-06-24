#!/usr/bin/env python
# -*- coding: utf-8 -*-

from path import Path
ROOT = Path('~/.skid').expand()    # feel free to use environment variables

# test skid repository
#ROOT = Path('~/skid-test').expand()    # feel free to use environment variables

CACHE = ROOT / 'marks'
LIMIT = 10

if not ROOT.exists():
    ROOT.mkdir()

if not CACHE.exists():
    CACHE.mkdir()

# enable bash completion
#  need to add "complete -F _optcomplete skid" to bashrc
completion = True

# commands
class cmd:
    ALL = [add, authors, drop, key, lexicon, ls, rm, scholar, similar, search, tags, title, update] = \
          'add, authors, drop, key, lexicon, ls, rm, scholar, similar, search, tags, title, update'.split(', ')
