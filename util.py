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
