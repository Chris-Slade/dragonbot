import ahocorasick
import argparse
import asyncio
import atexit
import collections
import discord
import functools
import json
import logging
import re
import string
import sys
import time

from storage import Storage, KeyExistsError
from insult import random_insult, get_insult
import util

__version__ = '0.13.2'

### ARGUMENTS ###

def getopts():
    defaults = {
        'config'     : 'config.json',
        'emotes'     : 'emotes.json',
        'global-log' : 'WARNING',
        'greet'      : True,
        'keywords'   : 'keywords.json',
        'log'        : 'INFO',
        'read-only'  : False,
    }
    parser = argparse.ArgumentParser(description='Discord chat bot')
    parser.set_defaults(**defaults)
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Specify the configuration file to use.'
    )
    parser.add_argument(
        '-e', '--emotes',
        type=str,
        help='Specify the emotes file to use.'
    )
    parser.add_argument(
        '--global-log',
        type=str,
        help='Set the logging level for all modules to the given level. Can be'
            ' one of (from least to most verbose):'
            ' DEBUG, INFO, WARNING, ERROR, CRITICAL'
    )
    parser.add_argument(
        '--greet',
        dest='greet',
        action='store_true',
        help='Tell the bot to issue a greeting to the greeting channel given'
            ' in the configuration file.'
    )
    parser.add_argument(
        '--no-greet',
        dest='greet',
        action='store_false',
        help='Tell the bot not to issue a greeting.'
    )
    parser.add_argument(
        '-k', '--keywords',
        type=str,
        help='Specify the keywords file to use.'
    )
    parser.add_argument(
        '-l', '--log',
        type=str,
        help='Set the logging level for only the main module. Takes the same'
            ' values as `--global-log`.'
    )
    parser.add_argument(
        '--read-only',
        action='store_true',
        help='Run the bot in read-only mode, preventing functions that access'
            ' the disk from doing so.'
    )
    opts = parser.parse_args()

    opts.global_log = util.get_log_level(getattr(opts, 'global-log'))
    if getattr(opts, 'global-log') is None:
        opts.global_log = util.get_log_level(defaults['global-log'])
    opts.log = util.get_log_level(getattr(opts, 'log'))
    if getattr(opts, 'log') is None:
        opts.log = util.get_log_level(defaults['log'])

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
        level=opts.global_log,
        format=' | '.join([
            '%(asctime)s',
            '%(levelname)s',
            '%(module)s:%(funcName)s:%(lineno)d',
            '%(message)s'
        ]),
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(opts.log)
    logger.info(
        'Set logging level to %s, global level to %s',
        opts.log,
        opts.global_log
    )

    def log_exit():
        logger.info('Exiting')
    atexit.register(log_exit)

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
    logger.info('Loaded %d emotes from disk', len(emotes))

    # Initialize keywords
    if 'keywords_file' not in config:
        config['keywords_file'] = opts.keywords
    keywords = Storage(config['keywords_file'])
    logger.info('Loaded %d keywords from disk', len(keywords))

    commands = {
        "addemote"      : add_emote,
        "addkeyword"    : add_keyword,
        "deleteemote"   : remove_emote,
        "deletekeyword" : remove_keyword,
        "emotes"        : list_emotes,
        "help"          : show_help,
        "insult"        : insult,
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
    item_list = ", ".join(sorted(storage))
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
        emotes[emote] = body
        emotes.save()
        logger.info(
            'Emote "%s" added by "%s"',
            emote,
            message.author.name
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
        del emotes[emote]
        emotes.save()
        logger.info(
            'Emote "%s" deleted by "%s"',
            emote,
            message.author.name
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
  insult        : Insult someone.
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
    stats['uptime']         = time.time() - stats['start time']
    stats['emotes known']   = len(emotes)
    stats['keywords known'] = len(keywords)

    sb = ["```Session statistics:"]

    longest = max(len(_) for _ in stats)
    stat_fmt = '\t{:<' + str(longest + 1) + '}: {:>7}'

    for stat in sorted(stats.keys()):
        sb.append(stat_fmt.format(stat.title(), stats[stat]))
    sb.append("```")
    stat_message = "\n".join(sb)
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
    if name in keywords:
        keywords[name].append(emote)
    else:
        keywords[name] = [emote]
    keywords.save()
    await do_keyword_reactions(message=None, update_automaton=True)
    await client.send_message(
        message.channel,
        'Added keyword reaction!'
    )
    logger.info(
        '%s added keyword "%s" -> "%s"',
        message.author.name,
        name,
        emote
    )

@not_read_only
async def remove_keyword(message, argstr):
    name = argstr
    try:
        del keywords[name]
        keywords.save()
        await do_keyword_reactions(message=None, update_automaton=True)
        await client.send_message(
            message.channel,
            'Removed keyword reaction!'
        )
        logger.info(
            '%s removed keyword "%s"',
            message.author.name,
            name
        )
    except KeyError:
        await client.send_message(
            message.channel,
            "That keyword doesn't exist!"
        )

async def insult(message, argstr):
    name = argstr
    insult = get_insult()
    if insult is None:
        await client.send_message(
            message.channel,
            "Error retrieving insult."
        )
    else:
        await client.send_message(
            message.channel,
            "{}: {}".format(name, insult)
        )

async def do_keyword_reactions(message=None, update_automaton=False):
    try:
        getattr(do_keyword_reactions, '_automaton')
    except AttributeError:
        update_automaton = True

    if update_automaton:
        # Make a new Aho-Corasick automaton
        do_keyword_reactions._automaton = ahocorasick.Automaton(str)
        # Add each keyword
        for keyword in keywords:
            do_keyword_reactions._automaton.add_word(keyword, keyword)
        # Finalize the automaton for searching
        do_keyword_reactions._automaton.make_automaton()

    # In case we were called just to update the automaton
    if message is None:
        return

    content = message.clean_content.casefold()
    for index, keyword in do_keyword_reactions._automaton.iter(content):
        reactions = keywords[keyword]
        logging.debug(
            'Got reactions [%s] for keyword "%s"',
            ", ".join(reactions) if reactions is not None else "None",
            keyword
        )
        for reaction in reactions:
            logger.info('Reacting with "%s"', reaction)
            try:
                await client.add_reaction(message, reaction)
            except discord.HTTPException as e:
                logger.exception(
                    'Error reacting to keyword "%s" with "%s"',
                    keyword,
                    reaction
                )
        stats['keywords seen'] += 1

### EVENT HANDLERS ###

@client.event
async def on_ready():
    global server_emoji
    logger.info('Bot is ready')
    stats['connect time'] = time.time() - stats['start time']
    server = client.get_server(config['greetings_server'])

    if server is not None:
        # Log server and default channel
        logger.info("Logged into server %s", server)
        if server.default_channel is not None:
            logger.info("Default channel is %s", server.default_channel)

        # Collect server emoji
        server_emoji = {}
        for emoji in client.get_all_emojis():
            server_emoji[emoji.name] = emoji
        logger.info('Got %d emoji in this server', len(server_emoji))
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
        logger.info('Server: %s %s', server.name, server.id)
        for channel in server.channels:
            if channel.type == discord.ChannelType.text:
                logger.info('Channel: %s %s', channel.name, channel.id)

@client.event
async def on_message(message):
    stats['messages seen'] += 1
    if message.content.startswith('!'):
        if message.content == '!':
            logger.info('Ignoring null command')
            return
        logger.info('Handling command message "%s"', message.content)
        split = message.content[1:].split(maxsplit=1)
        command = split[0] if len(split) >= 1 else None
        argstr  = split[1] if len(split) >= 2 else None

        if command is None:
            logger.warning('Mishandled command message "%s"', message.content)

        if command in commands:
            stats['commands seen'] += 1
            try:
                await commands[command](message, argstr)
            except TypeError as e:
                logger.exception(
                    'Failed to execute command "%s"',
                    command,
                    exc_info=e
                )
        else:
            logger.info('Ignoring unknown command "%s"', command)
    elif message.clean_content.startswith('@'):
        logger.info('Handling emote message "%s"', message.clean_content)
        emote = message.clean_content[1:]
        try:
            await client.send_message(message.channel, emotes[emote])
            stats['emotes seen'] += 1
        except KeyError:
            await client.add_reaction(message, '❔')

    # Check for keywords
    await do_keyword_reactions(message)

### RUN ###

if __name__ == "__main__":
    main()
