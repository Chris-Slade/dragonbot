import argparse
import asyncio
import atexit
import collections
import discord
import json
import logging
import os
import signal
import sys
import time

from urllib.error import URLError

from command_dispatcher import CommandDispatcher
from emotes import Emotes
from insult import get_insult
from keywords import Keywords
from storage import Storage
from util import split_command, command
import constants
import insult as insult_module
import util

__version__ = '0.20.0'

### ARGUMENTS ###

def getopts():
    """Handle bot arguments."""
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
    parser.add_argument(
        '--version',
        action='store_true',
        help='Print the version of the bot and the discord.py API and exit.'
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
    """Initialize the bot."""
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

    if (opts.version):
        print(version())
        sys.exit(0)

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

    # Add signal handler for restart signal
    def restart(signal, frame):
        global client
        logger.info('Received restart signal')
        try:
            if client.is_logged_in:
                client.logout()
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logger.warning(e)
    signal.signal(signal.SIGUSR1, restart)

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
    cd.register("play", set_current_game, may_use=owner_only)
    cd.register("say", say, may_use=owner_only)
    cd.register("stats", show_stats)
    cd.register("test", test, may_use=owner_only, rw=True)
    cd.register("truth", truth)
    emotes.register_commands(cd, config)
    keywords.register_commands(cd, config)
    command_dispatcher = cd # Make global

    logger.debug(", ".join(cd.known_command_names()))

    stats = collections.defaultdict(int)

    server_emoji = {}

    assert None not in (
        client,
        command_dispatcher,
        config,
        emotes,
        keywords,
        logger,
        opts,
        server_emoji,
        stats
    ), 'Variable was not initialized'

    logger.info('Finished initializing')

def main():
    init()
    logger.info(version())
    logger.info('PID is %d', os.getpid())
    assert version(), "version() should return a non-empty string, but didn't"
    stats['start time'] = time.time()
    try:
        client.run(config['credentials']['token'])
    except Exception:
        logging.error("Exception reached main()")
        return

def version():
    """Get a nicely formatted version string."""
    assert '__version__' in globals(), 'No global __version__ variable'
    return 'DragonBot v{} (discord.py v{}){}{}'.format(
        __version__,
        discord.__version__,
        ' [DEBUG MODE]' if __debug__ else '',
        ' [READ ONLY]' if 'opts' in globals()
            and hasattr(opts, 'read_only')
            and getattr(opts, 'read_only') else '',
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

  {prefix}play <game> <url>
    Set the bot's status as playing the given game. Owner only. The URL can be
    "None".

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

@command
async def truth(client, message):
    """Say the truth."""
    assert None not in (client, message), 'Got None, expected value'
    await client.send_message(message.channel, 'slushrfggts')

@command
async def show_help(client, message):
    """Show help."""
    command, argstr = util.split_command(message)
    if argstr is None:
        await client.send_message(message.channel, help())
    elif argstr.casefold() == 'emotes':
        await client.send_message(message.channel, Emotes.help())
    elif argstr.casefold() == 'keywords':
        await client.send_message(message.channel, Keywords.help())
    else:
        await client.send_message(message.channel, "I don't have help for that.")

@command
async def test(client, message):
    test_message = 'a' * 2500
    await client.send_message(message.channel, test_message)

@command
async def show_stats(client, message):
    """Show session statistics."""
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

@command
async def say(client, message):
    """Say something specified by the !say command."""
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

@command
async def insult(client, message):
    """Handles the !insult commmand."""
    command, name = split_command(message)
    try:
        insult = get_insult(rate_limit=1.5)
        if not (insult.startswith("I ") or insult.startswith("I'm ")):
            insult = insult[0].lower() + insult[1:]
        await client.send_message(
            message.channel,
            "{}, {}".format(name, insult)
        )
    except insult_module.RateLimited:
        await client.send_message(
            message.channel,
            'Requests are being sent too quickly.'
        )
    except URLError as e:
        await client.send_message(
            message.channel,
            'Error retrieving insult from server.'
        )
        logger.warning('Error retrieving insult from server: %s', str(e))

@command
async def set_current_game(client, message):
    """Handles the !play command."""
    command, args = split_command(message)
    try:
        game, url = args.rsplit(maxsplit=1)
    except ValueError:
        await client.send_message(
            message.channel,
            'Need a game and its URL.'
        )
        return
    if url == "None":
        url = None
    game = discord.Game(
        name=game,
        url=url
    )
    try:
        await client.change_presence(game=game)
    except InvalidArgument:
        await client.send_message('Error changing presence')

### EVENT HANDLERS ###

@client.event
async def on_ready():
    """Event handler for becoming ready."""
    global server_emoji
    assert client is not None, 'client is None in on_ready()'
    logger.info('Bot is ready')
    stats['connect time'] = time.time() - stats['start time']

    if 'greetings_server' in config:
        server = client.get_server(config['greetings_server'])
        # Log server and default channel
        logger.info("Logged into server %s", server)
        if server.default_channel is not None:
            logger.info("Default channel is %s", server.default_channel)

        # Collect server emoji
        if server_emoji is None:
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

    if 'presence' in config:
        presence = config['presence']
        if 'playing' in presence:
            playing = config['presence']['playing']
            game = None
            if 'name' in playing:
                name = playing['name']
                url = playing['url'] if 'url' in playing else None
                game = discord.Game(name=name, url=url)
                await client.change_presence(game=game)
                logger.info('Set current game to %s', str(game))
        # TODO: Support other presence options (status, AFK)

@client.event
async def on_message(message):
    """Event handler for messages."""
    stats['messages seen'] += 1
    if message.content.startswith(constants.COMMAND_PREFIX):
        if message.content == constants.COMMAND_PREFIX:
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
    elif message.clean_content.startswith(constants.EMOTE_PREFIX):
        logger.info('Handling emote message "%s"', message.clean_content)
        await emotes.display_emote(client, message)
        stats['emotes seen'] += 1

    # Check for keywords
    await keywords.handle_keywords(client, message)

### RUN ###

if __name__ == "__main__":
    main()
