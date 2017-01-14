import json
import logging
import atexit
import os

class Emotes(object):
    class EmoteExistsError(Exception):
        pass

    def __init__(self, emotes_file):
        self.emotes_file = emotes_file
        self.logger = logging.getLogger(__name__)
        self.load_emotes(emotes_file)
        atexit.register(self.save_emotes)

    def __len__(self):
        return len(self.emotes)

    def __contains__(self, key):
        return key in self.emotes

    def load_emotes(self, emotes_file=None):
        if emotes_file is None:
            emotes_file = self.emotes_file
        self.emotes_file = emotes_file
        if not os.path.isfile(emotes_file):
            self.logger.info('Creating new emotes file')
            with open(emotes_file, 'x') as fh:
                fh.writelines(["{}"])
        with open(emotes_file, 'r', encoding='utf-8') as fh:
            self.emotes = json.load(fh)

    def save_emotes(self):
        self.logger.info('Saving emotes')
        with open(self.emotes_file, 'w') as fh:
            json.dump(self.emotes, fh, indent=4, separators=(',', ' : '))

    def add_emote(self, key, value):
        key = Emotes._normalize_key(key)
        if key not in self.emotes:
            self.emotes[key] = value
        else:
            raise Emotes.EmoteExistsError('Emote already exists')

    def remove_emote(self, key):
        if key in self.emotes:
            del self.emotes[key]
        else:
            raise KeyError('Emote not found')

    def get_emote(self, key):
        key = Emotes._normalize_key(key)
        if key in self.emotes:
            return self.emotes[key]
        else:
            raise KeyError('Emote not found')

    def get_emotes(self):
        return self.emotes.keys()

    def _normalize_key(key):
        return key.strip().casefold()
