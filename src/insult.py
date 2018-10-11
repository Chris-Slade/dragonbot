"""A module for DragonBot that gives it the ability to insult people in
various ways.
"""

import random
import urllib
import logging

import config
import constants
import util

async def get_insult(who):
    query_params = urllib.parse.urlencode({ 'who' : who })
    url = f'{constants.INSULT_API_URL}?{query_params}'
    client = await util.get_http_client()
    rsp = await client.get(url)
    if rsp.status != 200:
        util.log_http_error(logging, rsp)
        return None
    return await rsp.text()

def random_insult():
    """Random insults that the bot calls people who fail to use its
    commands properly."""
    return random.choice(config.insults) if config.insults else constants.DEFAULT_INSULT
