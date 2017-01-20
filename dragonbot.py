import argparse
import asyncio
import atexit
import collections
import discord
import json
import logging
import time

from command_dispatcher import CommandDispatcher
from emotes import Emotes
from insult import get_insult
from keywords import Keywords
from storage import Storage
from util import split_command
import constants
import util

__version__ = '0.18.0'

### ARGUMENTS ###

def getopts():
    defaults = {
        'config'     : constants.DEFAULT_CONFIG,
        'emotes'     : constants.DEFAULT_EMOTES,
        'global-log' : constants.DEFAULT_LOG_LEVEL,
        'greet'      : True,
        'keywords'   : constants.DEFAULT_KEYWORDS,
        'log'        : constants.DEFAULT_BOT_LOG_LEVEL,
        'read-only'  : False,
    }
    parser = argparse.ArgumentParser(description='Discord chat bot')
    parser.set_defaults(**defaults)
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Specify the configuration file to use. Defaults to '
            + defaults['config'] + '.'
    )
    parser.add_argument(
        '-e', '--emotes',
        type=str,
        help='Specify the emotes file to use. Defaults to '
            + defaults['emotes'] + '.'
    )
    parser.add_argument(
        '--global-log',
        type=str,
        help='Set the logging level for all modules to the given level. Can be'
            ' one of (from least to most verbose):'
            ' DEBUG, INFO, WARNING, ERROR, CRITICAL.'
            ' Defaults to ' + defaults['global-log'] + '.'
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
        help='Specify the keywords file to use. Defaults to '
            + defaults['keywords'] + '.'
    )
    parser.add_argument(
        '-l', '--log',
        type=str,
        help='Set the logging level for only the main module. Takes the same'
            ' values as `--global-log`. Defaults to ' + defaults['log'] + '.'
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
    global                  \
        client,             \
        command_dispatcher, \
        config,             \
        emotes,             \
        keywords,           \
        logger,             \
        opts,               \
        server_emoji,       \
        stats

    # Get options
    opts = getopts()

    # Initialize logger
    logging.basicConfig(
        level=opts.global_log,
        format=constants.LOG_FORMAT,
        datefmt=constants.DATE_FORMAT
    )
    logger = logging.getLogger('dragonbot')
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

    # Initialize emote module
    # XXX This should be changed so the different sources of the emotes file
    # location have a clearly defined precedence over one another.
    if 'emotes_file' not in config:
        config['emotes_file'] = opts.emotes
    emotes = Emotes(config['emotes_file'])

    # Initialize keywords
    if 'keywords_file' not in config:
        config['keywords_file'] = opts.keywords
    keywords = Keywords(config['keywords_file'])

    # Set up command dispatcher
    owner_only = { config['owner_id'] } # For registering commands as owner-only
    cd = CommandDispatcher(read_only=opts.read_only)
    cd.register("help", show_help)
    cd.register("insult", insult)
    cd.register("say", say, may_use=owner_only)
    cd.register("stats", show_stats)
    cd.register("test", test, may_use=owner_only, rw=True)
    cd.register("truth", truth)
    emotes.register_commands(cd, config)
    keywords.register_commands(cd, config)
    command_dispatcher = cd # Make global

    logger.debug(", ".join(cd.known_command_names()))

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
        return

def version():
    return 'DragonBot v{} (discord.py v{})'.format(
        __version__,
        discord.__version__
    )

def help():
    return """```
{version}
Commands:
  Commands are activated by sending a message beginning with the prefix

  "{prefix}" followed by the name of the command and zero or more
  arguments.

  {prefix}help
    Show this help message.

  {prefix}help <section>
    Show the help section for a submodule. Options are `emotes` and `keywords`.

  {prefix}insult <someone's name>
    Insult someone with a random insult.

  {prefix}say <channel ID> <message>
    Have the bot post a message in a given channel. Owner only.

  {prefix}stats
    Show bot statistics.

  {prefix}test
    For testing and debugging. For the bot owner's use only.

  {prefix}truth
    Tell the truth.
```""".format(version=version(), prefix=constants.COMMAND_PREFIX)

### COMMANDS ###

async def truth(client, message):
    await client.send_message(message.channel, 'slushrfggts')

async def show_help(client, message):
    command, argstr = util.split_command(message)
    if argstr is None:
        await client.send_message(message.channel, help())
    elif argstr.casefold() == 'emotes':
        await client.send_message(message.channel, Emotes.help())
    elif argstr.casefold() == 'keywords':
        await client.send_message(message.channel, Keywords.help())
    else:
        await client.send_message(message.channel, "I don't have help for that.")

async def test(client, message):
    test_message = 'a' * 2500
    await client.send_message(message.channel, test_message)

async def show_stats(client, message):
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

async def say(client, message):
    command, argstr = split_command(message)
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

async def insult(client, message):
    command, name = split_command(message)
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

        stats['commands seen'] += 1

        command, _ = split_command(message)

        if command is None:
            logger.warning('Mishandled command message "%s"', message.content)

        assert command_dispatcher is not None

        try:
            await command_dispatcher.dispatch(client, command, message)
            stats['commands run'] += 1
        except (
            CommandDispatcher.PermissionDenied,
            CommandDispatcher.WriteDenied,
            CommandDispatcher.UnknownCommand
        ) as e:
            await client.send_message(message.channel, str(e))
            logger.info(
                'Exception executing command "%s": %s',
                command,
                str(e)
            )
    elif message.clean_content.startswith('@'):
        logger.info('Handling emote message "%s"', message.clean_content)
        await emotes.display_emote(client, message)
        stats['emotes seen'] += 1

    # Check for keywords
    await keywords.handle_keywords(client, message)

### RUN ###

if __name__ == "__main__":
    main()
