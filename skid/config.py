#!/usr/bin/env python
# -*- coding: utf-8 -*-

from path import path
ROOT = path('~/.skid').expand()    # feel free to use environment variables

# test skid repository
#ROOT = path('~/.skid-test').expand()    # feel free to use environment variables

CACHE = ROOT / 'marks'
REMOTE = 'login.clsp.jhu.edu:~/papers'

LIMIT = 10

if not ROOT.exists():
    ROOT.mkdir()

if not CACHE.exists():
    CACHE.mkdir()

# enable bash completion
#  need to add "complete -F _optcomplete skid" to bashrc
completion = True

# commands
CMDS = [AUTHORS, PUSH, UPDATE, RM, ADD, TAGS,
        LEXICON, TITLE, SIMILAR, LS, SEARCH, KEY, SCHOLAR] = \
    'authors push update rm add tags lexicon title similar ls search key scholar'.split()
