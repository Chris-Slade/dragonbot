import logging
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

def split_command(message):
    """Split a command message.

    E.g., split_command("!test foo bar") will return ("!test", "foo bar").
    """
    split = message.content[1:].split(maxsplit=1)
    command = split[0] if len(split) >= 1 else None
    argstr  = split[1] if len(split) >= 2 else None
    return command, argstr
