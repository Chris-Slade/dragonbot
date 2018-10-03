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

__version__ = '2.1.1'

### ARGUMENTS ###

def getopts():
    """Handle bot arguments."""
    defaults = {
        'config'     : constants.DEFAULT_CONFIG,
        'env_config' : constants.DEFAULT_ENV_CONFIG,
        'global_log' : constants.DEFAULT_LOG_LEVEL,
        'greet'      : True,
        'log'        : constants.DEFAULT_BOT_LOG_LEVEL,
        'read_only'  : False,
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
        '-e', '--env-config',
        type=str,
        help='Load the configuration as JSON from the given environment'
             ' variable, rather than using a configuration file.'
             ' This option overrides --config.'
    )
    parser.add_argument(
        '--global-log',
        type=str,
        help='Set the logging level for all modules to the given level. Can be'
            ' one of (from least to most verbose):'
            ' DEBUG, INFO, WARNING, ERROR, CRITICAL.'
            ' Defaults to ' + defaults['global_log'] + '.'
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

    opts.global_log = util.get_log_level(opts.global_log)
    opts.log = util.get_log_level(opts.log)

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
    if opts.env_config and opts.env_config in os.environ:
        logger.info('Loading config from environment')
        config = json.loads(os.environ[opts.env_config])
    else:
        if opts.env_config:
            logger.info(
                'Environment config variable %s not present.'
                ' Falling back on config file',
                opts.env_config
            )
        logger.info('Loading config from %s', opts.config)
        with open(opts.config, 'r', encoding='utf-8') as fh:
            config = json.load(fh)

    # Initialize storage directory if needed
    if 'storage_dir' not in config:
        logger.warning('No storage directory specified, defaulting to ./storage/')
        config['storage_dir'] = './storage/'
    logger.info('Creating storage directory %s', config['storage_dir'])
    os.makedirs(config['storage_dir'], exist_ok=True)

    # Initialize emote and keyword modules
    logger.info('Initializing Emotes module')
    emotes = Emotes()
    logger.info('Initializing Keywords module')
    keywords = Keywords()

    # Set up command dispatcher
    owner_only = { int(config['owner_id']) } # For registering commands as owner-only
    cd = CommandDispatcher(read_only=opts.read_only)
    cd.register("help", show_help)
    cd.register("insult", insult)
    cd.register("play", set_current_game, may_use=owner_only)
    cd.register("purge", purge, may_use=owner_only)
    cd.register("say", say, may_use=owner_only)
    cd.register("stats", show_stats)
    cd.register("test", test, may_use=owner_only, rw=True)
    cd.register("truth", truth)
    cd.register("version", version_command)
    emotes.register_commands(cd, config)
    keywords.register_commands(cd, config)
    command_dispatcher = cd # Make global

    logger.debug(", ".join(cd.known_command_names()))

    stats = collections.defaultdict(int)

    assert None not in (
        client,
        command_dispatcher,
        config,
        emotes,
        keywords,
        logger,
        opts,
        stats
    ), 'Variable was not initialized'

    logger.info('Finished pre-login initialization')

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

  {prefix}purge <@user> <count>
    Purges up to <count> messages from the mentioned <@user>. <count> must be
    at least 2 but no more than 100. Deleted messages cannot be older than 14
    days. Subject to the limitations imposed by the Discord API.

  {prefix}say <channel ID> <message>
    Have the bot post a message in a given channel. Owner only.

  {prefix}stats
    Show bot statistics.

  {prefix}test
    For testing and debugging. For the bot owner's use only.

  {prefix}truth
    Tell the truth.

  {prefix}version
    Say the bot's version.
```""".format(version=version(), prefix=constants.COMMAND_PREFIX)

### COMMANDS ###

@command
async def truth(client, message):
    """Say the truth."""
    assert None not in (client, message), 'Got None, expected value'
    await message.channel.send('slushrfggts')

@command
async def version_command(client, message):
    """Say the bot's version."""
    await message.channel.send(version())

@command
async def show_help(client, message):
    """Show help."""
    command, argstr = util.split_command(message)
    if argstr is None:
        await message.channel.send(help())
    elif argstr.casefold() == 'emotes':
        await message.channel.send(Emotes.help())
    elif argstr.casefold() == 'keywords':
        await message.channel.send(Keywords.help())
    else:
        await message.channel.send("I don't have help for that.")

@command
async def test(client, message):
    test_message = 'a' * 2500
    await message.channel.send(test_message)

@command
async def show_stats(client, message):
    """Show session statistics."""
    stats['uptime']         = time.time() - stats['start time']
    stats['emotes known']   = emotes.count_emotes()
    stats['keywords known'] = keywords.count_keywords()

    sb = ["```Session statistics:"]

    longest = max(len(_) for _ in stats)
    stat_fmt = '\t{:<' + str(longest + 1) + '}: {:>7}'

    for stat in sorted(stats.keys()):
        sb.append(stat_fmt.format(stat.title(), stats[stat]))
    sb.append("```")
    stat_message = "\n".join(sb)
    await message.channel.send(stat_message)

@command
async def say(client, message):
    """Say something specified by the !say command."""
    command, argstr = split_command(message)
    if command is None or argstr is None:
        await message.channel.send('Nothing to say.')
        return
    try:
        channel_id, user_message = argstr.split(maxsplit=1)
        channel_id = int(channel_id)
    except ValueError:
        await message.channel.send('Need channel ID and message to send.')
        return
    channel = client.get_channel(channel_id)
    if channel is not None:
        await channel.send(user_message)
    else:
        await message.channel.send("Couldn't find channel.")

@command
async def insult(client, message):
    """Handles the !insult commmand."""
    command, name = split_command(message)
    try:
        insult = get_insult(rate_limit=1.5)
        if not (insult.startswith("I ") or insult.startswith("I'm ")):
            insult = insult[0].lower() + insult[1:]
        await message.channel.send("{}, {}".format(name, insult))
    except insult_module.RateLimited:
        await message.channel.send('Requests are being sent too quickly.')
    except URLError as e:
        await message.channel.send('Error retrieving insult from server.')
        logger.warning('Error retrieving insult from server: %s', str(e))

@command
async def set_current_game(client, message):
    """Handles the !play command."""
    command, args = split_command(message)
    try:
        game, url = args.rsplit(maxsplit=1)
    except ValueError:
        await message.channel.send('Need an activity and its URL.')
        return
    if url == "None":
        url = None
    game = discord.Game(name=game, url=url)
    try:
        await client.change_presence(activity=game)
        await message.channel.send('Changed presence.')
    except InvalidArgument:
        await message.channel.send('Error changing presence.')

@command
async def purge(client, message):
    """Handles the !purge command."""
    command, args = split_command(message)
    try:
        user, count = args.split(maxsplit=1)
    except ValueError:
        await message.channel.send('Need a name and a count.')
        return
    try:
        count = int(count)
    except ValueError:
        await message.channel.send('Count must be an integer.')
        return

    if count > 100:
        await message.channel.send("Can't delete more than 100 messages.")
        return
    if count < 2:
        await message.channel.send("Can't delete fewer than 2 messages.")
        return

    delete_me = []
    async for message in message.channel.history(limit=1000):
        if message.author.mention == user:
            delete_me.append(message)
        if len(delete_me) >= count:
            break
    if delete_me:
        try:
            await message.channel.delete_messages(delete_me)
            await message.channel.send(
                'Deleted {} messages'.format(len(delete_me))
            )
        except discord.Forbidden:
            await message.channel.send("I'm not allowed to do that.")
        except discord.HTTPException as e:
            await message.channel.send(
                'An error occurred' + (': ' + e.text if e.text else "") + '.'
            )
            logger.exception('Error deleting messages')
        except Exception:
            logger.exception('Error deleting messages')
    else:
        await message.channel.send(
            "I don't see any messages from that user in the recent history."
        )

### EVENT HANDLERS ###

@client.event
async def on_ready():
    """Event handler for becoming ready."""
    global emotes, keywords
    assert client is not None, 'client is None in on_ready()'
    logger.info('Bot is ready')
    stats['connect time'] = time.time() - stats['start time']

    if 'servers' in config:
        # Log server and default channel
        for server in client.guilds:
            logger.info("Logged into server %s %s", server, server.id)
            if (
                hasattr(server, 'default_channel')
                and server.default_channel is not None
            ):
                logger.info("Default channel is %s", server.default_channel)
            for channel in server.channels:
                if isinstance(channel, discord.TextChannel):
                    logger.info('\tChannel: %s %s', channel.name, channel.id)

            if (
                opts.greet and hasattr(server, 'default_channel')
                and server.default_channel is not None
            ):
                await server.default_channel.send(version())

            emotes.add_server(server, config['storage_dir'])
            keywords.add_server(server, config['storage_dir'])
    else:
        logger.warning("Couldn't find servers")

    if 'presence' in config:
        presence = config['presence']
        if 'playing' in presence:
            playing = config['presence']['playing']
            game = None
            if 'name' in playing:
                name = playing['name']
                url = playing['url'] if 'url' in playing else None
                game = discord.Game(name=name, url=url)
                await client.change_presence(activity=game)
                logger.info('Set current game to %s', str(game))
        # TODO: Support other presence options (status, AFK)

@client.event
async def on_message(message):
    """Event handler for messages."""
    stats['messages seen'] += 1

    # Don't process the bot's messages
    if message.author.id == client.user.id:
        return

    if message.content.startswith(constants.COMMAND_PREFIX):
        if message.content == constants.COMMAND_PREFIX:
            logger.info('Ignoring null command')
            return
        logger.info(
            '[%s] Handling command message "%s" from user %s',
            message.guild,
            message.content,
            message.author
        )

        stats['commands seen'] += 1

        command, _ = split_command(message)

        if command is None:
            logger.warning(
                '[%s] Mishandled command message "%s" from %s',
                message.guild,
                message.content,
                message.author
            )

        assert command_dispatcher is not None

        try:
            await command_dispatcher.dispatch(client, command, message)
            stats['commands run'] += 1
        except (
            CommandDispatcher.PermissionDenied,
            CommandDispatcher.WriteDenied,
            CommandDispatcher.UnknownCommand
        ) as e:
            await message.channel.send(str(e))
            logger.info(
                '[%s] Exception executing command "%s" from %s: %s',
                message.guild,
                command,
                message.author,
                str(e)
            )
    elif message.clean_content.startswith(constants.EMOTE_PREFIX):
        logger.info(
            '[%s] Handling emote message "%s" from %s',
            message.guild,
            message.clean_content,
            message.author
        )
        await emotes.display_emote(client, message)
        stats['emotes seen'] += 1

    # Check for keywords
    await keywords.handle_keywords(client, message)

### RUN ###

if __name__ == "__main__":
    main()
