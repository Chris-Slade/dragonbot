import aiohttp
import atexit
import config
import constants
import discord
import functools
import logging
import re
import sys
import unicodedata
import urllib.parse

from datetime import datetime, timedelta

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def get_log_level(level_str):
    try:
        level = getattr(logging, level_str)
        if not isinstance(level, int):
            raise AttributeError('Dummy')
        return level
    except AttributeError:
        return None

def remove_punctuation(text):
    """Remove punctuation and symbols from a string."""
    if not hasattr(remove_punctuation, '_tbl'):
        remove_punctuation._tbl = dict.fromkeys(
            i for i in range(sys.maxunicode)
                if unicodedata.category(chr(i)).startswith('P')
                or unicodedata.category(chr(i)).startswith('S')
        )
    return text.translate(remove_punctuation._tbl)

def normalize_path(path):
    normalized = remove_punctuation(path.strip().casefold())
    return re.sub(r'\s+', '-', normalized)

def split_command(message):
    """Split a command message.

    E.g., split_command("!test foo bar") will return ("!test", "foo bar").
    """
    return _split_command_helper(message.content)

def split_command_clean(message):
    """Split a command message, using the clean content."""
    return _split_command_helper(message.clean_content)

def _split_command_helper(content):
    split = content[1:].split(maxsplit=1)
    command = split[0] if len(split) >= 1 else None
    argstr  = split[1] if len(split) >= 2 else None
    return command, argstr

def is_get(number):
    if number in (123, 1234, 12345, 123456, 1234567, 12345678, 123456789):
        return True
    count = str(number)
    if len(count) >= 2 and count[-1] == count[-2]:
        return True
    return False

def command(command):
    """Perform actions that should be done every time a command is invoked."""
    @functools.wraps(command)
    async def wrapper(client, message):
        assert client is not None, 'Got None for client'
        assert message is not None, 'Got None for message'
        await command(client, message)
    return wrapper

def command_method(command):
    """Perform actions that should be done every time a command is invoked."""
    @functools.wraps(command)
    async def wrapper(self, client, message):
        assert client is not None, 'Got None for client'
        assert message is not None, 'Got None for message'
        await command(self, client, message)
    return wrapper

def server_command_method(command):
    """Only allow this command in a server, not PMs."""
    @functools.wraps(command)
    async def wrapper(self, client,  message):
        assert client is not None, 'Got None for client'
        assert message is not None, 'Got None for message'
        if not hasattr(message, 'guild') or message.guild is None:
            await message.channel.send(
                'This command can only be used in a server context.'
            )
        else:
            await command(self, client, message)
    return wrapper

def ts_to_iso(timestamp):
    """Convert a UNIX timestamp to an ISO-8601-formatted string."""
    return datetime.fromtimestamp(timestamp).isoformat()

def td_str(time_difference):
    """Convert a time difference in seconds to a human-readable string."""
    return str(timedelta(seconds=time_difference))

def create_help_embed(title, description, help_msgs):
    embed = discord.Embed(
        title=title,
        description=description,
        timestamp=datetime.now(),
        color=constants.EMBED_COLOR,
    )
    for help_msg in help_msgs:
        embed.add_field(
            name=help_msg[0].format(prefix=constants.COMMAND_PREFIX),
            value=help_msg[1],
            inline=False
        )
    return embed

def is_embeddable_image_url(string):
    parse = urllib.parse.urlparse(string)
    return parse.scheme and parse.netloc and parse.path \
        and parse.scheme in constants.EMBEDDABLE_IMAGE_SCHEMES \
        and any(parse.path.endswith(ext) for ext in constants.EMBEDDABLE_IMAGE_EXTS)

def log_http_error(logger, response):
    """Log an error from an HTTP request made with aiohttp."""
    logger.warning(
        'Error making %s request on %s: %s - %s',
        response.method,
        response.url,
        response.status,
        response.url
    )

async def get_http_client():
    if not hasattr(config, 'http_client'):
        config.http_client = aiohttp.ClientSession()
        def close_http_client():
            if (
                hasattr(config, 'http_client')
                and hasattr(config.http_client, 'close')
                and not config.http_client.closed
            ):
                logging.info('Closing aiohttp ClientSession (FIXME)')
                # config.http_client.close()
        atexit.register(close_http_client)
    return config.http_client
