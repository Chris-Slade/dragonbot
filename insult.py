"""A module for DragonBot that gives it the ability to insult people in
various ways.
"""

import codecs
import json
import random
import time
import urllib
import urllib.request
from html.parser import HTMLParser

class RateLimited(Exception):
    pass

class GetInsult(HTMLParser):
    def __init__(self):
        self.done = False
        self.in_wrap = False
        self.insult = ""
        super().__init__()

    def handle_starttag(self, tag, attrs):
        if self.done: return
        for attr in attrs:
            if attr[0] == 'class' and attr[1] == 'wrap':
                self.in_wrap = True

    def handle_endtag(self, tag):
        if self.done: return
        if self.in_wrap and tag == 'div':
            self.done = True

    def handle_data(self, data):
        if self.done: return
        if self.in_wrap:
            self.insult += data

    def get_insult(self, content):
        self.feed(content)
        self.insult = self.insult.strip().replace("\n", "")
        if self.insult != "":
            return self.insult
        else:
            return None

def get_insult(rate_limit=None):
    assert rate_limit is None or isinstance(rate_limit, int)
    if rate_limit is not None:
        if not hasattr(get_insult, '_last_called'):
            get_insult._last_called = time.time()
        else:
            cur_time = time.time()
            if cur_time - get_insult._last_called < rate_limit:
                raise RateLimited('You are being rate limited')
            else:
                get_insult._last_called = cur_time
    parser = GetInsult()
    content = get_content('http://insultgenerator.org')
    insult = parser.get_insult(content)
    assert insult is not None, \
        'Got None insult. get_insult() should either' \
        ' return something or raise an exception.'
    return insult

def get_content(url):
    return str(urllib.request.urlopen(url).read(), encoding='utf-8')

def random_insult(insults_file='insults.json'):
    """Random insults that the bot calls people who fail to use its
    commands properly.

    These are loaded from a JSON file specified by the `insults_file` in
    `config.json`. They should be given as an object with two fields:
    `encoding`, which optionally specifies the encoding of the insults
    (a parameter to `codecs.decode`), and `insults`, which is an array
    containing the insults.

    The `encoding` field is to allow obfuscation of the insults, e.g.
    with `rot_13`. The strings themselves must be encoded as UTF-8 text,
    in accordance with RFC 7159.
    """
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
