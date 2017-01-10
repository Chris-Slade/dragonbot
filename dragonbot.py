from __future__ import (
    print_function,
    absolute_import,
    unicode_literals,
    division
)
import argparse
import asyncio
import atexit
import discord
import json
import logging
import os
import random
import re
import sys

__version__    = '0.4.1'

### ARGUMENTS ###

def getopts():
    defaults = {
        'config' : 'config.json',
        'emotes' : 'emotes.json',
        'log'    : 'INFO',
    }
    parser = argparse.ArgumentParser(description='Discord chat bot')
    parser.set_defaults(**defaults)
    parser.add_argument(
        '-l', '--log',
        type=str,
        help='The logging level.'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Configuration file to use.'
    )
    parser.add_argument(
        '-e', '--emotes',
        type=str,
        help='Emotes file to use.'
    )
    opts = parser.parse_args()
    try:
        log_level = getattr(logging, opts.log)
        if type(log_level) != int:
            raise AttributeError
        opts.log_level = log_level
    except AttributeError:
        print('Unknown log level, defaulting to INFO')
        opts.log_level = logging.INFO
    return opts

### INITIALIZATION ###

loop   = asyncio.get_event_loop()
client = discord.Client(loop=loop)

def init():
    global client, commands, config, emotes, logger, opts, server_emoji

    # Get options
    opts = getopts()

    # Initialize logger
    logging.basicConfig(
        level=opts.log_level,
        format='%(asctime)-15s %(levelname)s %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Initialize config
    logger.info('Loading config')
    with open(opts.config, 'r', encoding='utf-8') as fh:
        config = json.load(fh)

    # Initialize emotes
    if 'emotes_file' not in config:
        config['emotes_file'] = opts.emotes
    if not os.path.isfile(config['emotes_file']):
        logger.info('Creating new emotes file')
        with open(opts.emotes, 'x') as fh:
            fh.writelines(["{}"])
    with open(config['emotes_file'], 'r', encoding='utf-8') as fh:
        emotes = json.load(fh)

    # Add emote-saving hook
    atexit.register(save_emotes)

    commands = {
        "addemote"    : add_emote,
        "deleteemote" : remove_emote,
        "emotes"      : list_emotes,
        "help"        : help,
        "removeemote" : remove_emote,
        "truth"       : truth,
    }

    logger.info('Finished initializing')

def main():
    init()
    logger.info(version())
    try:
        client.run(config['credentials']['token'])
    except Exception as e:
        logging.error("Caught exception", exc_info=full_exc_info())
        sys.exit(1)

### UTILITY FUNCTIONS ###

def save_emotes():
    logger.info('Saving emotes')
    with open(config['emotes_file'], 'w') as fh:
        json.dump(emotes, fh, indent=4, separators = (',', ' : '))

def version():
    return 'DragonBot v{} (discord.py v{})'.format(
        __version__,
        discord.__version__
    )

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
        emote, url = argstr.rsplit(maxsplit=1)
    except ValueError as e:
        await client.send_message(
            message.channel,
            'Give me a name and a URL, {}.'.format(random_insult())
        )
        return

    emote = emote.casefold()
    if emote == 'everyone':
        await client.send_message(message.channel, 'That name is reserved.')
        return

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
        if type(server_emoji) != dict:
            logger.warning('Expected server_emoji to be initialized')
        emoji = server_emoji['pride']
        await client.send_message(
            message.channel,
            'Added emote! ' + str(emoji) if emoji is not None
            else 'Added emote!'
        )


async def remove_emote(message, argstr):
    if argstr is None:
        await client.send_message(
            message.channel,
            "I can't delete nothing, {}. :tsun:".format(random_insult())
        )
        return

    emote = argstr.casefold()
    if emote in emotes:
        del emotes[emote]
        save_emotes()
        if type(server_emoji) != dict:
            logger.warning('Expected server_emoji to be initialized')
        emoji = server_emotes['pride']
        await client.send_message(
            message.channel,
            'Deleted emote! ' + str(emoji) if emoji is not None
            else 'Deleted emote!'
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
{}
Commands:
    addemote    : Adds an emote. For example:
        `!addemote example http://example.com/emote.png`
        will allow you to use `@example` to have the corresponding URL
        posted by the bot.
    deleteemote : Alias for `removeemote`.
    emotes      : Show a list of known emotes.
    help        : Show this help message.
    insult      : Insult someone. (Not implemented yet.)
    removeemote : Remove an emote.
    test        : For testing and debugging. For the bot owner's use only.
    truth       : Tell the truth.
```'''.format(version())
    )

async def test(message, argstr):
    if message.author.id != config['owner_id']:
        await client.send_message(
            message.channel,
            'Go away, this is for {}.'.format(config['owner_name'])
        )
    else:
        pass

### EVENT HANDLERS ###

@client.event
async def on_ready():
    logger.info('Bot is ready')
    server = client.get_server(config['greetings_server'])
    logger.info(
        "Logged into server {}, default channel is {}"
        .format(server, server.default_channel)
    )
    if server is not None:
        server_emoji = {}
        for emoji in client.get_all_emojis():
            server_emoji[emoji.name] = emoji
        logger.info('Got {} emoji in this server'.format(len(server_emoji)))
        logger.debug(', '.join(server_emoji.keys()))
        if 'pride' in server_emoji:
            await client.send_message(
                server.default_channel,
                "{} {}".format(version(), str(server_emoji['pride']))
            )
        else:
            await client.send_message(
                server.default_channel,
                'DragonBot has arrived!'
            )
    else:
        logger.warning("Couldn't find server")


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
        if emote == 'everyone':
            pass
        elif emote in emotes:
            await client.send_message(message.channel, emotes[emote])
        else:
            await client.send_message("I don't know that emote.")

### RUN ###

if __name__ == "__main__":
    main()
