import json
import logging
import atexit
import os

class KeyExistsError(Exception):
    pass

class Storage(object):

    def __init__(self, file):
        self.file = file
        self.logger = logging.getLogger(__name__)
        self.load(file)
        atexit.register(self.save)

    def __len__(self):
        return len(self.entries)

    def __contains__(self, key):
        return key in self.entries

    def load(self, file=None):
        if file is None:
            file = self.file
        self.file = file
        if not os.path.isfile(file):
            self.logger.info('Creating new entries file')
            with open(file, 'x') as fh:
                fh.writelines(["{}"])
        with open(file, 'r', encoding='utf-8') as fh:
            self.entries = json.load(fh)

    def save(self):
        self.logger.info('Saving entries')
        with open(self.file, 'w') as fh:
            json.dump(self.entries, fh, indent=4, separators=(',', ' : '))

    def add_entry(self, key, value):
        key = Storage._normalize_key(key)
        if key not in self.entries:
            self.entries[key] = value
        else:
            raise KeyExistsError('Key already exists')

    def remove_entry(self, key):
        if key in self.entries:
            del self.entries[key]
        else:
            raise KeyError('Emote not found')

    def get_entry(self, key):
        key = Storage._normalize_key(key)
        if key in self.entries:
            return self.entries[key]
        else:
            raise KeyError('Emote not found')

    def get_entries(self):
        return self.entries.keys()

    def _normalize_key(key):
        return key.strip().casefold()
