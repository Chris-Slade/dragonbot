"""
A module for DragonBot that gives it the ability to insult people in various
ways.
"""

import codecs
import json
import random

def random_insult(insults_file='insults.json'):
    '''
    Random insults that the bot calls people who fail to use its
    commands properly.

    These are loaded from a JSON file specified by the `insults_file` in
    `config.json`. They should be given as an object with two fields:
    `encoding`, which optionally specifies the encoding of the insults
    (a parameter to `codecs.decode`), and `insults`, which is an array
    containing the insults.

    The `encoding` field is to allow obfuscation of the insults, e.g.
    with `rot_13`. The strings themselves must be encoded as UTF-8 text,
    in accordance with RFC 7159.
    '''
    if not hasattr(random_insult, '_cache'):
        with open(insults_file, 'r', encoding='utf-8') as fh:
            obj = json.load(fh)
        if 'insults' not in obj:
            raise ValueError(
                'Malformed insults object, expected "insults" field'
            )
        insults = obj['insults']
        if 'encoding' in obj:
            insults = [
                codecs.decode(insult, obj['encoding'])
                    for insult in obj['insults']
            ]
        random_insult._cache = insults
    return random.choice(random_insult._cache)

