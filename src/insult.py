"""A module for DragonBot that gives it the ability to insult people in
various ways.
"""

import random
import urllib
import logging

import config
import constants
import util

async def get_insult(who = None):
    if who:
        query_params = urllib.parse.urlencode({ 'who' : who })
        url = f'{constants.INSULT_API_URL}?{query_params}'
    else:
        url = constants.INSULT_API_URL
    client = await util.get_http_client()
    rsp = await client.get(url)
    if rsp.status != 200:
        util.log_http_error(logging, rsp)
        # Try again, this time without the parameter
        rsp2 = await client.get(constants.INSULT_API_URL)
        if rsp2.status == 200:
            return await rsp2.text()
        # Otherwise return nothing
        return None
    return await rsp.text()

def random_insult():
    """Random insults that the bot calls people who fail to use its
    commands properly."""
    return random.choice(config.insults) if config.insults else constants.DEFAULT_INSULT
