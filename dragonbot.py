from __future__ import (
    print_function,
    absolute_import,
    unicode_literals,
    division
)
import asyncio
import atexit
import discord
import json
import logging
import os
import random
import re
import sys

__version__    = '0.1.1'
CONFIG_FILE    = 'config.json'
EMOTES_FILE    = 'emotes.json'
COMMANDS_FILE  = 'commands.json'
SAVE_DELAY     = 5 * 60
client         = None
commands       = None
config         = None
emotes         = None
logger         = None

### INITIALIZATION ###

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize config
logger.info('Loading config')
with open(CONFIG_FILE, 'r', encoding='utf-8') as fh:
    config = json.load(fh)

# Initialize emotes
if 'emotes_file' not in config:
    config['emotes_file'] = EMOTES_FILE
if not os.path.isfile(config['emotes_file']):
    logger.info('Creating new emotes file')
    with open(EMOTES_FILE, 'x') as fh:
        fh.writelines(["{}"])
with open(config['emotes_file'], 'r', encoding='utf-8') as fh:
    emotes = json.load(fh)

### MAIN ###
loop = asyncio.get_event_loop()
client = discord.Client(loop=loop)

logger.info('DragonBot v{} (discord.py v{})'.format(
        __version__,
        discord.__version__
    )
)

# Add client cleanup hook
def cleanup():
    print('Logging out')
    if client.is_logged_in:
        client.logout()

atexit.register(cleanup)

# Add emote-saving hook
def save_emotes():
    logger.info('Saving emotes')
    with open(config['emotes_file'], 'w') as fh:
        json.dump(emotes, fh, indent=4, separators = (',', ' : '))

atexit.register(save_emotes)

### UTILITY FUNCTIONS ###

def random_insult():
    insults = [
        '<insults go here>'
    ]
    return random.choice(insults)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

### COMMANDS ###

async def list_emotes(message, argstr):
    if len(emotes) == 0:
        await client.send_message(
            message.channel,
            "I don't know any emotes yet!"
        )
        return

    emote_list = ", ".join(sorted(emotes))
    for chunk in chunker(emote_list, 2000):
        await client.send_message(message.channel, chunk)

async def add_emote(message, argstr):
    try:
        if argstr is None:
            raise ValueError('No arguments')
        emote, url = argstr.split(maxsplit=1)
    except ValueError as e:
        await client.send_message(
            message.channel,
            'Give me a name and a URL, {}.'.format(random_insult())
        )
        return

    emote = emote.casefold()
    regex = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    if emote in emotes:
        await client.send_message(
            message.channel,
            'That emote already exists, {}.'.format(random_insult())
        )
    elif not regex.search(url):
        await client.send_message(
            message.channel,
            "That doesn't appear to be a valid URL, {}.".format(random_insult())
        )
    else:
        emotes[emote] = url
        save_emotes()
        await client.send_message(message.channel, 'Added emote!')

async def remove_emote(message, argstr):
    if argstr is None:
        await client.send_message(
            message.channel,
            "I can't delete nothing, {}.".format(random_insult())
        )
        return

    emote = argstr.casefold()
    if emote in emotes:
        del emotes[emote]
        save_emotes()
        await client.send_message(
            message.channel,
            "Deleted emote!"
        )
    else:
        await client.send_message(
            message.channel,
            "That emote isn't stored, {}.".format(random_insult())
        )

async def truth(message, argstr):
    await client.send_message(message.channel, 'slushrfggts')

async def help(message, argstr):
    await client.send_message(
        message.channel,
'''```
DragonBot v{} (discord.py v{})
    Commands:
        addemote    : Adds an emote. For example:
            `!addemote example http://example.com/emote.png`
            will allow you to use `@example` to have the corresponding URL
            posted by the bot.
        deleteemote : Alias for `removeemote`.
        emotes      : Show a list of known emotes.
        help        : Show this help message.
        insult      : Insult someone.
        removeemote : Remove an emote.
        truth       : Tell the truth.
```'''.format(__version__, discord.__version__)
    )

commands = {
    "addemote"    : add_emote,
    "deleteemote" : remove_emote,
    "emotes"      : list_emotes,
    "help"        : help,
    "removeemote" : remove_emote,
    "truth"       : truth,
}

### EVENT HANDLERS ###

@client.event
async def on_ready():
    logger.info('Bot is ready')

@client.event
async def on_message(message):
    if message.content.startswith('!'):
        logger.info('Handling command message "' + message.content + '"')
        split = message.content[1:].split(maxsplit=1)
        command = split[0] if len(split) >= 1 else None
        argstr  = split[1] if len(split) >= 2 else None

        if command is None:
            logger.warning('Mishandled command message: "{}"'.format(message.content))

        if command in commands:
            await commands[command](message, argstr)
        else:
            logger.info('Ignoring unknown command "{}"'.format(command))
    elif message.content.startswith('@'):
        logger.info('Handling emote message "' + message.content + '"')
        emote = message.content[1:]
        if emote in emotes:
            await client.send_message(message.channel, emotes[emote])
        else:
            await client.send_message("I don't know that emote.")

### RUN ###

try:
    client.run(config['credentials']['token'])
except Exception as e:
    logging.error("Caught exception", exc_info=full_exc_info())
    sys.exit(1)
