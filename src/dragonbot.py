import argparse
import asyncio
import atexit
import codecs
import collections
import datetime
import discord
import json
import logging
import os
import signal
import sys
import time

from pymongo import MongoClient
from urllib.error import URLError

from command_dispatcher import CommandDispatcher
from emotes import Emotes
from insult import get_insult
from keywords import Keywords
from storage import storage_injector
from util import split_command, command
import config
import constants
import insult as insult_module
import util

__version__ = '3.1.1'

### ARGUMENTS ###

def getopts():
    """Handle bot arguments."""
    env_opts = {
        'global_log_level' : 'DRAGONBOT_GLOBAL_LOG_LEVEL',
        'greet'            : 'DRAGONBOT_GREET',
        'insults'          : 'DRAGONBOT_INSULTS',
        'insults_file'     : 'DRAGONBOT_INSULTS_FILE',
        'log_level'        : 'DRAGONBOT_LOG_LEVEL',
        'mongodb_uri'      : 'DRAGONBOT_MONGODB_URI',
        'owner_id'         : 'DRAGONBOT_OWNER_ID',
        'presence'         : 'DRAGONBOT_PRESENCE',
        'read_only'        : 'DRAGONBOT_READ_ONLY',
        'storage_dir'      : 'DRAGONBOT_STORAGE_DIR',
        'token'            : 'DRAGONBOT_TOKEN',
    }
    defaults = {
        'global_log_level' : os.getenv(env_opts['global_log_level'], default='WARNING'),
        'greet'        : os.environ.get(env_opts['greet']) == 'True',
        'insults'      : os.environ.get(env_opts['insults']),
        'insults_file' : os.environ.get(env_opts['insults_file']),
        'log_level'    : os.getenv(env_opts['log_level'], default='INFO'),
        'mongodb_uri'  : os.environ.get(env_opts['mongodb_uri']),
        'owner_id'     : os.environ.get(env_opts['owner_id']),
        'presence'     : os.environ.get(env_opts['presence']),
        'read_only'    : os.environ.get(env_opts['read_only']) == 'True',
        'storage_dir'  : os.environ.get(env_opts['storage_dir']),
        'token'        : os.environ.get(env_opts['token']),
    }

    parser = argparse.ArgumentParser(description='Discord chat bot')
    parser.set_defaults(**defaults)
    parser.add_argument(
        '--global-log-level',
        choices=constants.LOG_LEVELS,
        help='Set the logging level for all modules to the given level.'
            ' Environment variable: ' + env_opts['global_log_level']
    )
    parser.add_argument(
        '--greet',
        dest='greet',
        action='store_true',
        help='Tell the bot to issue a greeting to the greeting channel given'
            ' in the configuration file. (Deprecated.)'
            ' Environment variable: ' + env_opts['greet']
    )
    parser.add_argument(
        '--no-greet',
        dest='greet',
        action='store_false',
        help='Tell the bot not to issue a greeting. (Deprecated.)'
            ' Environment variable: ' + env_opts['greet']
    )
    parser.add_argument(
        '--insults',
        type=str,
        help='Random insults to select from when insulting users.'
            ' This option should be set to a JSON object with two fields:'
            ' "encoding", which optionally specifies the encoding of the'
            ' insults (a parameter to `codecs.decode`), and "insults," which'
            ' is an array containing the insults.'
            ' The "encoding" field is to allow obfuscation of the insults,'
            ' e.g. with `rot_13`. The strings themselves must be encoded as'
            ' UTF-8 text, in accordance with RFC 7159.'
            ' If that is not present, only a single default insult will be used.'
            ' See also the --insults-file option.'
            ' Environment variable: ' + env_opts['insults']
    )
    parser.add_argument(
        '--insults-file',
        type=str,
        help='Like the --insults option, but takes a filename from which to'
            ' read the insults.'
    )
    parser.add_argument(
        '-l', '--log-level',
        choices=constants.LOG_LEVELS,
        help='Set the logging level for only the main module. Takes the same'
            ' values as `--global-log-level`.'
            ' Environment variable: ' + env_opts['log_level']
    )
    parser.add_argument(
        '--mongodb-uri',
        type=str,
        help='Connection URI for MongoDB. If provided, MongoDB will be used'
            ' instead of flat files for storage.'
    )
    parser.add_argument(
        '--owner-id',
        type=int,
        help='The unique snowflake of the owner. This user is permitted to use'
            ' owner-only commands. Required.'
            ' Environment variable: ' + env_opts['owner_id']
    )
    parser.add_argument(
        '--presence',
        type=str,
        help="The bot's presence, given as JSON."
            ' Environment variable: ' + env_opts['presence']
    )
    parser.add_argument(
        '--read-only',
        action='store_true',
        help='Run the bot in read-only mode, preventing functions that access'
            ' the disk or database from doing so.'
            ' Environment variable: ' + env_opts['read_only']
    )
    parser.add_argument(
        '--storage-dir',
        type=str,
        help='If using flat-file storage, the directory in which the files'
            ' will be saved. If it does not exist, it will be created.'
            ' Environment variable: ' + env_opts['storage_dir']
    )
    parser.add_argument(
        '--token',
        type=str,
        help='The authentication token to use for this bot. Required.'
            ' Environment variable: ' + env_opts['token']
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help='Print the version of the bot and the discord.py API and exit.'
    )
    opts = parser.parse_args()

    # Since we allow env-var fallbacks, we can't use argparse's built-in
    # "required" functionality.
    for required_arg in ['token', 'owner_id']:
        if required_arg not in opts or getattr(opts, required_arg) is None:
            print(f'Error: Argument "{required_arg}" is required.', file=sys.stderr)
            sys.exit(1)

    # Parse --presence option
    if opts.presence is not None:
        opts.presence = _parse_json_opt(opts, 'presence')

    # Load insults
    if opts.insults and opts.insults_file:
        print('You cannot give both --insults and --insults-file.')
        sys.exit(1)
    elif opts.insults:
        opts.insults = _get_insults(_parse_json_opt(opts, 'insults'))
    elif opts.insults_file:
        with open(opts.insults_file, 'r', encoding='utf-8') as fh:
            opts.insults = _get_insults(json.load(fh))

    if opts.storage_dir and opts.mongodb_uri:
        print('You cannot give both --storage-dir and --mongodb-uri.')
        sys.exit(1)
    elif not opts.storage_dir and not opts.mongodb_uri:
        print('You must specify either --storage-dir or --mongodb-uri.')
        sys.exit(1)

    opts.global_log_level = util.get_log_level(opts.global_log_level)
    opts.log_level = util.get_log_level(opts.log_level)

    # Initialize settings module
    for name, val in vars(opts).items():
        setattr(config, name, val)

    config.initialized = True
    return config

def _parse_json_opt(opts, arg):
    try:
        return json.loads(getattr(opts, arg))
    except json.JSONDecodeError as e:
        print(f'{arg} option is not valid JSON: ' + e.msg + '\n')
        sys.exit(1)

def _get_insults(insults):
    if 'insults' not in insults:
        raise ValueError('Malformed insults object, expected "insults" field')
    if 'encoding' in insults:
        insults['insults'] = [
            codecs.decode(insult, insults['encoding'])
                for insult in insults['insults']
        ]
    return insults['insults']

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
        stats

    # Get options
    getopts()
    assert config.initialized, 'Settings were not initialized'

    if (config.version):
        print(version())
        sys.exit(0)

    # Initialize logger
    logging.basicConfig(
        level=config.global_log_level,
        format=constants.LOG_FORMAT,
        datefmt=constants.DATE_FORMAT
    )
    logger = logging.getLogger('dragonbot')
    logger.setLevel(config.log_level)
    logger.info(
        'Set logging level to %s, global level to %s',
        config.log_level,
        config.global_log_level,
    )

    def log_exit():
        logger.info('Exiting')
    atexit.register(log_exit)

    # Add signal handler for restart signal. Ignore signal and frame args.
    def restart(_signal, _frame):
        global client
        logger.info('Received restart signal')
        try:
            if client.is_logged_in:
                client.logout()
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logger.warning(e)
    signal.signal(signal.SIGUSR1, restart)

    # Initialize storage directory if needed
    if config.storage_dir:
        logger.info('Creating storage directory %s', config.storage_dir)
        os.makedirs(config.storage_dir, exist_ok=True)
    # Otherwise initialize a Mongo client
    elif config.mongodb_uri:
        logger.info('Initializing Mongo client')
        config.mongo = MongoClient(config.mongodb_uri)

        def mongo_cleanup():
            logger.info('Closing MongoDB connection(s)')
            config.mongo.close()
        atexit.register(mongo_cleanup)

    # Initialize emote and keyword modules
    logger.info('Initializing Emotes module')
    emotes = Emotes()
    logger.info('Initializing Keywords module')
    keywords = Keywords()

    # Set up command dispatcher
    assert config.owner_id is not None, 'No owner ID configured'
    owner_only = { int(config.owner_id) } # For registering commands as owner-only
    cd = CommandDispatcher(read_only=config.read_only)
    cd.register("config", show_config, may_use=owner_only)
    cd.register("help", show_help)
    cd.register("insult", insult)
    cd.register("play", set_current_game, may_use=owner_only)
    cd.register("purge", purge, may_use=owner_only)
    cd.register("say", say, may_use=owner_only)
    cd.register("stats", show_stats)
    cd.register("test", test, may_use=owner_only, rw=True)
    cd.register("truth", truth)
    cd.register("version", version_command)
    emotes.register_commands(cd)
    keywords.register_commands(cd)
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
        client.run(config.token)
    except Exception:
        logging.exception("Exception reached main()")
        return

def version():
    """Get a nicely formatted version string."""
    assert '__version__' in globals(), 'No global __version__ variable'
    return 'DragonBot v{} (discord.py v{}){}{}'.format(
        __version__,
        discord.__version__,
        ' [DEBUG MODE]' if __debug__ else '',
        ' [READ ONLY]' if config.read_only else '',
    )

def help_message():
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
    await message.channel.send(embed=discord.Embed(title='slushrfggts'))

@command
async def version_command(_client, message):
    """Say the bot's version."""
    await message.channel.send(version())

@command
async def show_help(_client, message):
    """Show help."""
    _command, argstr = util.split_command(message)
    if argstr is None:
        await message.channel.send(help_message())
    elif argstr.casefold() == 'emotes':
        await message.channel.send(Emotes.help())
    elif argstr.casefold() == 'keywords':
        await message.channel.send(Keywords.help())
    else:
        await message.channel.send("I don't have help for that.")

@command
async def show_config(_client, message):
    """Show the current bot configuration."""
    dm_channel = message.author.dm_channel
    if dm_channel is None:
        await message.author.create_dm()
        dm_channel = message.author.dm_channel
    embed = discord.Embed(
        title='Configuration',
        description='The current bot configuration.',
        timestamp=datetime.datetime.now(),
    )
    for name, val in sorted(vars(config).items()):
        if name.startswith('_'):
            continue
        if name in ('token', 'mongodb_uri', 'mongo'):
            val = '<hidden>'
        embed.add_field(name=name, value=val, inline=False)
    embed.set_footer(text=version())
    await dm_channel.send(embed=embed)

@command
async def test(_client, message):
    test_message = 'a' * 2500
    await message.channel.send(test_message)

@command
async def show_stats(_client, message):
    """Show session statistics."""
    stats['uptime']         = time.time() - stats['start time']
    stats['emotes known']   = emotes.count_emotes()
    stats['keywords known'] = keywords.count_keywords()

    embed = discord.Embed(
        title='Session Statistics',
        description='Statistics collected since Dragonbot was last started',
        timestamp=datetime.datetime.now(),
    )
    for field in [
        [ 'Start time',     util.ts_to_iso(stats['start time']), True ],
        [ 'Connect time',   util.td_str(stats['connect time']),  True ],
        [ 'Uptime',         util.td_str(stats['uptime']),        True ],
        [ 'Avg. latency',   util.td_str(client.latency),         True ],
        [ 'Messages seen',  stats['messages seen'],              True ],
        [ 'Commands seen',  stats['commands seen'],              True ],
        [ 'Emotes known',   stats['emotes known'],               True ],
        [ 'Keywords known', stats['keywords known'],             True ],
    ]:
        embed.add_field(name=field[0], value=field[1], inline=(field[2] or False))
    embed.set_footer(text=version())
    await message.channel.send(embed=embed)

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
async def insult(_client, message):
    """Handles the !insult commmand."""
    _command, name = split_command(message)
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
    _command, args = split_command(message)
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
    except discord.InvalidArgument:
        await message.channel.send('Error changing presence.')

@command
async def purge(_client, message):
    """Handles the !purge command."""
    _command, args = split_command(message)
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
            config.greet and hasattr(server, 'default_channel')
            and server.default_channel is not None
        ):
            await server.default_channel.send(version())

        emotes.add_server(server, storage_injector('emotes', server.id))
        keywords.add_server(server, storage_injector('keywords', server.id))

    if config.presence is not None:
        presence = config.presence
        if 'playing' in presence:
            playing = presence['playing']
            game = None
            if 'name' in playing:
                name = playing['name']
                url = playing['url'] if 'url' in playing else None
                game = discord.Game(name=name, url=url)
                await client.change_presence(activity=game)
                logger.info('Set current game to %s', str(game))
        # TODO: Support other presence options (status, AFK)

@client.event
async def on_guild_join(server):
    global emotes, keywords, logger
    logger.info('Initializing storage for new server "%s"', server)
    emotes.add_server(server, storage_injector('emotes', server.id))
    keywords.add_server(server, storage_injector('keywords', server.id))

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
