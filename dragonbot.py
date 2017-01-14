from __future__ import (
    print_function,
    absolute_import,
    unicode_literals,
    division
)
import argparse
import asyncio
import codecs
import collections
import discord
import functools
import json
import logging
import random
import re
import string
import sys
import time

from storage import Storage, KeyExistsError
import dragonbot_util as util

__version__ = '0.11.2'

### ARGUMENTS ###

def getopts():
    defaults = {
        'config'    : 'config.json',
        'emotes'    : 'emotes.json',
        'keywords'  : 'keywords.json',
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
        '-k', '--keywords',
        type=str,
        help='Keywords file to use.'
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
        if isinstance(log_level, int):
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
    global            \
        client,       \
        commands,     \
        config,       \
        emotes,       \
        keywords,     \
        logger,       \
        opts,         \
        server_emoji, \
        stats

    # Get options
    opts = getopts()

    # Initialize logger
    logging.basicConfig(
        level=opts.log_level,
        format='%(asctime)-15s\t%(name)s\t%(levelname)s\t%(message)s'
    )
    logger = logging.getLogger(__name__)

    # Initialize config
    logger.info('Loading config')
    with open(opts.config, 'r', encoding='utf-8') as fh:
        config = json.load(fh)

    # Initialize emotes
    # XXX This should be changed so the different sources of the emotes file
    # location have a clearly defined precedence over one another.
    if 'emotes_file' not in config:
        config['emotes_file'] = opts.emotes
    emotes = Storage(config['emotes_file'])
    logger.info('Loaded {} emotes from disk'.format(len(emotes)))

    # Initialize keywords
    if 'keywords_file' not in config:
        config['keywords_file'] = opts.keywords
    keywords = Storage(config['keywords_file'])
    logger.info('Loaded {} keywords from disk'.format(len(keywords)))

    commands = {
        "addemote"      : add_emote,
        "addkeyword"    : add_keyword,
        "deleteemote"   : remove_emote,
        "deletekeyword" : remove_keyword,
        "emotes"        : list_emotes,
        "help"          : show_help,
        "keywords"      : list_keywords,
        "refreshemotes" : refresh_emotes,
        "removeemote"   : remove_emote,
        "removekeyword" : remove_keyword,
        "say"           : say,
        "stats"         : show_stats,
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
    except Exception:
        logging.error("Exception reached main()")
        sys.exit(1)

### BOT-RELATED UTILITY FUNCTIONS ###

def version():
    return 'DragonBot v{} (discord.py v{})'.format(
        __version__,
        discord.__version__
    )

def random_insult():
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
        if 'insults_file' not in config:
            raise FileNotFoundError('Could not find insults file in config')
        else:
            with open(config['insults_file'], 'r', encoding='utf-8') as fh:
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
    stats['insults picked'] += 1
    return random.choice(random_insult._cache)

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

async def list_stored_items(message, storage, items='items'):
    if len(storage) == 0:
        await client.send_message(
            message.channel,
            "I don't have any {} yet!".format(items)
        )
    item_list = ", ".join(sorted(storage.get_entries()))
    for chunk in util.chunker(item_list, 2000):
        await client.send_message(message.channel, chunk)


async def list_emotes(message, argstr):
    await list_stored_items(message, emotes, 'emotes')

async def list_keywords(message, argstr):
    await list_stored_items(message, keywords, 'keywords')

@not_read_only
async def add_emote(message, argstr):
    try:
        if argstr is None:
            raise ValueError('No arguments')
        pattern = re.compile(
            r'^ \s* \{ \s* ([^{}]+) \s* \} \s* \{ \s* ([^{}]+) \s* \}',
            re.X
        )
        match = pattern.search(argstr)
        if match:
            emote, body = match.group(1, 2)
            emote = emote.strip()
            body = body.strip()
        else:
            raise ValueError('Malformed parameters to !addemote')
    except Exception as e:
        logger.info('Failed to parse !addcommand', exc_info=e)
        await client.send_message(
            message.channel,
            'Give me a name and a URL, {}.'.format(random_insult())
        )
        return

    try:
        emotes.add_entry(emote, body)
        emotes.save()
        logger.info(
            'Emote "{}" added by "{}"'.format(
                emote,
                message.author.name
            )
        )
        stats['emotes added'] += 1
        await client.send_message(
            message.channel,
            'Added emote! ' + str(server_emoji['pride'])
                if 'pride' in server_emoji else 'Added emote!'
        )
    except KeyExistsError:
        await client.send_message(
            message.channel,
            'That emote already exists, {}.'.format(random_insult())
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

    emote = argstr
    try:
        emotes.remove_entry(emote)
        emotes.save()
        logger.info(
            'Emote "{}" deleted by "{}"'.format(
                emote,
                message.author.name
            )
        )
        stats['emotes deleted'] += 1
        await client.send_message(
            message.channel,
            'Deleted emote! ' + str(server_emoji['pride'])
                if 'pride' in server_emoji else 'Deleted emote!'
        )
    except KeyError:
        await client.send_message(
            message.channel,
            "That emote isn't stored, {}. {}".format(
                random_insult(),
                str(server_emoji['tsun']) if 'tsun' in server_emoji else ''
            )
        )

async def truth(message, argstr):
    await client.send_message(message.channel, 'slushrfggts')

async def show_help(message, argstr):
    await client.send_message(
        message.channel,
'''```
{}
Commands:
  addemote      : Adds an emote. For example,
      `!addemote {{example}}{{http://example.com/emote.png}}` will allow
      you to use `@example` to have the corresponding URL posted by the
      bot. Because both emote names and the corresponding strings may
      contain whitespace, both must be surrounded by curly braces, as in
      the example.
  addkeyword    : Add a keyword and a reaction. When the bot sees the keyword
      in a message, it will react with the specified reaction.
  deleteemote   : Alias for `removeemote`.
  deletekeyword : Alias for `removekeyword`.
  emotes        : Show a list of known emotes.
  help          : Show this help message.
  insult        : Insult someone. (Not implemented yet.)
  removeemote   : Remove an emote.
  removekeyword : Remove a keyword.
  say           : Post a message in a given channel. Owner only.
  stats         : Show bot statistics.
  test          : For testing and debugging. For the bot owner's use only.
  truth         : Tell the truth.
```'''.format(version())
    )

@owner_only
async def test(message, argstr):
    logger.info(message.content)
    logger.info(message.clean_content)
    await client.add_reaction(message, 'pride:266322418887294976')

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
        len(emotes),
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
    except ValueError:
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
    emotes.load(config['emotes_file'])
    await client.send_message(message.channel, 'Emotes refreshed!')

@not_read_only
async def add_keyword(message, argstr):
    try:
        name, emote = argstr.split(maxsplit=1)
    except:
        await client.send_message(message.channel, 'Need a keyword and emote.')

    # Try to extract a custom emoji's name and ID
    match = re.match(r'<:([^:]+:\d+)>', emote)
    if match:
        emote = match.group(1)

    # Assume an emoji is correct and just store it
    try:
        keywords.add_entry(name, emote)
        await client.send_message(
            message.channel,
            'Added keyword reaction!'
        )
        logger.info(
            '{} added keyword "{}" -> "{}"'.format(
                message.author.name,
                name,
                emote
            )
        )
    except KeyExistsError:
        await client.send_message(
            message.channel,
            'That keyword already has a reaction, you {}.'.format(
                random_insult()
            )
        )

@not_read_only
async def remove_keyword(message, argstr):
    name = argstr
    try:
        keywords.remove_entry(name)
        await client.send_message(
            message.channel,
            'Removed keyword reaction!'
        )
        logger.info(
            '{} removed keyword "{}"'.format(
                message.author.name,
                name
            )
        )
    except KeyError:
        await client.send_message(
            message.channel,
            "That keyword doesn't exist!"
        )

### EVENT HANDLERS ###

@client.event
async def on_ready():
    global server_emoji
    logger.info('Bot is ready')
    stats['connect time'] = time.time() - stats['start time']
    server = client.get_server(config['greetings_server'])

    if server is not None:
        # Log server and default channel
        logger.info("Logged into server {}".format(server))
        if server.default_channel is not None:
            logger.info("Default channel is {}".format(server.default_channel))

        # Collect server emoji
        server_emoji = {}
        for emoji in client.get_all_emojis():
            server_emoji[emoji.name] = emoji
        logger.info('Got {} emoji in this server'.format(len(server_emoji)))
        logger.debug(', '.join(server_emoji.keys()))
        # Post a greeting
        if opts.greet:
            await client.send_message(
                server.get_channel(config['greetings_channel'])
                    if 'greetings_channel' in config
                    else server.default_channel,
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
        if message.content == '!':
            logger.info('Ignoring null command')
            return
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
        emote = message.clean_content[1:]
        try:
            await client.send_message(message.channel, emotes.get_entry(emote))
            stats['emotes'] += 1
        except KeyError:
            await client.send_message(
                message.channel,
                "I don't know that emote."
            )
    # Check for keywords
    words = util.remove_punctuation(message.clean_content).casefold().split()
    for word in words:
        if word in keywords:
            reaction = keywords.get_entry(word)
            logger.info("Reacting with {}".format(reaction))
            await client.add_reaction(message, reaction)

### RUN ###

if __name__ == "__main__":
    main()
