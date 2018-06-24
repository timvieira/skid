#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import environ
from skid import config
from glob import glob
from path import Path


if 'COMP_WORDS' in environ and config.completion:

    def completion():
        cwords = environ['COMP_WORDS'].split()
        #cline = environ['COMP_LINE']
        #cpoint = int(environ['COMP_POINT'])
        cword = int(environ['COMP_CWORD'])

        currword = None if cword >= len(cwords) else cwords[cword]

        if cword < 2:
            # second words is one of the skid commands like 'search' or 'add'
            possible = config.cmd.ALL

        else:

            command = cwords[1]
            #if command == 'rm':
            #possible = config.CACHE.glob('*')
            #else:
            if 1:

                prefix = cwords[-1]
                if len(cwords) == 2:
                    prefix = ''
    
                if prefix.startswith('-'):
    
                    # technically, only available under prefix 'skid search'
                    possible = ['--limit',
                                '--show',
                                '--hide',
                                '--pager',
                                '--format',
                                '--by',
                                '--top',
                                '--no-open',
                                '--note']
    
                else:
                    possible = glob(prefix + '*')
                    possible = [x + '/' if x.isdir() else x for x in map(Path, possible)]
                    if len(possible) == 1 and possible[0].isdir():  # only a directory left
                        possible = possible[0].glob('*')

        if currword:
            possible = [x for x in possible if x.startswith(currword) and len(x) >= len(currword)]

        print(' '.join(possible))

    completion()
    exit(1)
