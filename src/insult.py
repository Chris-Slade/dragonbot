"""A module for DragonBot that gives it the ability to insult people in
various ways.
"""

from html.parser import HTMLParser
import random
import time
import urllib
import urllib.request

import config
import constants

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
        return self.insult if self.insult != "" else None

def get_insult(rate_limit=None):
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

def random_insult():
    """Random insults that the bot calls people who fail to use its
    commands properly."""
    return random.choice(config.insults) if config.insults else constants.DEFAULT_INSULT
