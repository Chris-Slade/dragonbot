from __future__ import (
    print_function,
    absolute_import,
    unicode_literals,
    division
)
import argparse
import asyncio
import atexit
import collections
import discord
import functools
import json
import logging
import os
import random
import re
import sys
import time

__version__ = '0.10.0'

### ARGUMENTS ###

def getopts():
    defaults = {
        'config'    : 'config.json',
        'emotes'    : 'emotes.json',
        'greet'     : True,
        'log'       : 'INFO',
        'ro-emotes' : False,
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
    parser.add_argument(
        '--greet',
        dest='greet',
        action='store_true'
    )
    parser.add_argument(
        '--no-greet',
        dest='greet',
        action='store_false'
    )
    parser.add_argument(
        '--read-only',
        action='store_true'
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
    global client, commands, config, emotes, logger, opts, server_emoji, stats

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
    emotes = load_emotes(config['emotes_file'])

    # Add emote-saving hook
    atexit.register(save_emotes)

    commands = {
        "addemote"      : add_emote,
        "deleteemote"   : remove_emote,
        "emotes"        : list_emotes,
        "help"          : help,
        "say"           : say,
        "stats"         : show_stats,
        "refreshemotes" : refresh_emotes,
        "removeemote"   : remove_emote,
        "test"          : test,
        "truth"         : truth,
    }

    stats = collections.defaultdict(int)

    logger.info('Finished initializing')

def main():
    init()
    logger.info(version())
    stats['start time'] = time.time()
    try:
        client.run(config['credentials']['token'])
    except Exception as e:
        logging.error("Caught exception", exc_info=full_exc_info())
        sys.exit(1)

### UTILITY FUNCTIONS ###

def load_emotes(emotes_file):
    if not os.path.isfile(emotes_file):
        logger.info('Creating new emotes file')
        with open(opts.emotes, 'x') as fh:
            fh.writelines(["{}"])
    with open(emotes_file, 'r', encoding='utf-8') as fh:
        emotes = json.load(fh)
    return emotes

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
    stats['insults picked'] += 1
    return random.choice(insults)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def notNone(value, default):
    return value if value is not None else default

def owner_only(command):
    u"""
    Makes a command usable by the owner only, sending a message if someone else
    tries to call it.
    """
    @functools.wraps(command)
    async def wrapper(message, argstr):
        if message.author.id != config['owner_id']:
            await client.send_message(
                message.channel,
                'Go away, this is for {}.'.format(config['owner_name'])
            )
        else:
            await command(message, argstr)
    return wrapper

def not_read_only(command):
    u"""
    Makes a command respect the --read-only option, returning without executing
    it if the option is enabled.
    """
    @functools.wraps(command)
    async def wrapper(message, argstr):
        if opts.read_only:
            await client.send_message(
                message.channel,
                "I'm in read-only mode."
            )
        else:
            await command(message, argstr)
    return wrapper

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

@not_read_only
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

    if emote in emotes:
        await client.send_message(
            message.channel,
            'That emote already exists, {}.'.format(random_insult())
        )
    else:
        emotes[emote] = url
        save_emotes()
        stats['emotes added'] += 1
        await client.send_message(
            message.channel,
            'Added emote! ' + str(server_emoji['pride'])
                if 'pride' in server_emoji else 'Added emote!'
        )

@not_read_only
async def remove_emote(message, argstr):
    if opts.read_only:
        logger.info('No emote removed, read-only enabled')
        await client.send_message(
            message.channel,
            "I'm in read-only mode."
        )
        return
    if argstr is None:
        await client.send_message(
            message.channel,
            "I can't delete nothing, {}. {}".format(
                random_insult(),
                str(server_emoji['tsun']) if 'tsun' in server_emoji else ''
            )
        )
        return

    emote = argstr.casefold()
    if emote in emotes:
        del emotes[emote]
        save_emotes()
        stats['emotes deleted'] += 1
        await client.send_message(
            message.channel,
            'Deleted emote! ' + str(server_emoji['pride'])
                if 'pride' in server_emoji else 'Deleted emote!'
        )
    else:
        await client.send_message(
            message.channel,
            "That emote isn't stored, {}. {}".format(
                random_insult(),
                str(server_emoji['tsun']) if 'tsun' in server_emoji else ''
            )
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
    say         : Post a message in a given channel. Owner only.
    stats       : Show bot statistics.
    removeemote : Remove an emote.
    test        : For testing and debugging. For the bot owner's use only.
    truth       : Tell the truth.
```'''.format(version())
    )

@owner_only
async def test(message, argstr):
    await client.send_message(message.channel, 'test')

async def show_stats(message, argstr):
    stat_message = """```
Session statistics:
    Uptime:             {:6f}s
    Time to connect:    {:6f}s
    Emotes known:       {}
    Emotes added:       {}
    Emotes removed:     {}
    Messages processed: {}
    Commands called:    {}
    Emotes used:        {}
```""".format(
        time.time() - stats['start time'],
        stats['connect time'],
        len(emotes.keys()),
        stats['emotes added'],
        stats['emotes deleted'],
        stats['messages'],
        stats['commands'],
        stats['emotes'],
    )
    await client.send_message(message.channel, stat_message)

@owner_only
async def say(message, argstr):
    try:
        channel_id, user_message = argstr.split(maxsplit=1)
    except ValueError as e:
        await client.send_message(
            message.channel,
            'Need channel ID and message to send!'
        )
        return
    channel = client.get_channel(channel_id)
    if channel is not None:
        await client.send_message(channel, user_message)
    else:
        await client.send_message(message.channel, "Couldn't find channel.")

@owner_only
async def refresh_emotes(message, argstr):
    global emotes
    emotes = load_emotes(config['emotes_file'])
    await client.send_message(message.channel, 'Emotes refreshed!')

### EVENT HANDLERS ###

@client.event
async def on_ready():
    global server_emoji
    logger.info('Bot is ready')
    stats['connect time'] = time.time() - stats['start time']
    server = client.get_server(config['greetings_server'])
    logger.info(
        "Logged into server {}, default channel is {}"
        .format(server, server.default_channel)
    )
    # Collect server emoji
    if server is not None:
        server_emoji = {}
        for emoji in client.get_all_emojis():
            server_emoji[emoji.name] = emoji
        logger.info('Got {} emoji in this server'.format(len(server_emoji)))
        logger.debug(', '.join(server_emoji.keys()))
        # Post a greeting
        if opts.greet:
            await client.send_message(
                server.default_channel,
                "{} {}".format(
                    version(),
                    server_emoji['pride'] if 'pride' in server_emoji else ''
                )
            )
    else:
        logger.warning("Couldn't find server")
    # Print list of servers and channels
    for server in client.servers:
        print(' '*4, server.name, ' ', server.id)
        for channel in server.channels:
            if channel.type == discord.ChannelType.text:
                print(' '*8, channel.name, ' ', channel.id)

@client.event
async def on_message(message):
    stats['messages'] += 1
    if message.content.startswith('!'):
        logger.info('Handling command message "' + message.content + '"')
        split = message.content[1:].split(maxsplit=1)
        command = split[0] if len(split) >= 1 else None
        argstr  = split[1] if len(split) >= 2 else None

        if command is None:
            logger.warning('Mishandled command message: "{}"'.format(message.content))

        if command in commands:
            stats['commands'] += 1
            try:
                await commands[command](message, argstr)
            except TypeError as e:
                logger.exception(
                    'Failed to execute command "{}"'.format(command),
                    exc_info=e
                )
        else:
            logger.info('Ignoring unknown command "{}"'.format(command))
    elif message.clean_content.startswith('@'):
        logger.info('Handling emote message "' + message.clean_content + '"')
        emote = message.clean_content[1:].casefold()
        if emote == 'everyone':
            pass
        elif emote in emotes:
            stats['emotes'] += 1
            await client.send_message(message.channel, emotes[emote])
        else:
            await client.send_message(
                message.channel,
                "I don't know that emote."
            )

### RUN ###

if __name__ == "__main__":
    main()
