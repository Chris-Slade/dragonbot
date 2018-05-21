import functools
import logging
import re
import sys
import unicodedata

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def not_none(value, default):
    return value if value is not None else default

def get_log_level(level_str):
    try:
        level = getattr(logging, level_str)
        if not isinstance(level, int):
            raise AttributeError('Dummy')
        return level
    except AttributeError:
        return None

def remove_punctuation(text):
    if not hasattr(remove_punctuation, '_tbl'):
        remove_punctuation._tbl = dict.fromkeys(
            i for i in range(sys.maxunicode)
                if unicodedata.category(chr(i)).startswith('P')
        )
    return text.translate(remove_punctuation._tbl)

def normalize_path(path):
    normalized = remove_punctuation(path.strip().casefold())
    return re.sub(r'\s+', '-', normalized)

def split_command(message):
    """Split a command message.

    E.g., split_command("!test foo bar") will return ("!test", "foo bar").
    """
    split = message.content[1:].split(maxsplit=1)
    command = split[0] if len(split) >= 1 else None
    argstr  = split[1] if len(split) >= 2 else None
    return command, argstr

def is_get(number):
    if number in (123, 1234, 12345, 123456, 1234567, 12345678, 123456789):
        return True
    count = str(number)
    if len(count) >= 2 and count[-1] == count[-2]:
        return True

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
        if message.server is None:
            await client.send_message(
                message.channel,
                'This command can only be used in a server context.'
            )
        else:
            await command(self, client, message)
    return wrapper
