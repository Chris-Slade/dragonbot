import json
import logging
import atexit
import os

class KeyExistsError(Exception):
    pass

def _normalize_key(key):
    return key.strip().casefold()

class Storage(dict):
    """A subclass of dict with additional methods for storing and
    retrieving the mappings to and from JSON files, respectively.
    """

    def __init__(self, file):
        self.file = file
        self.logger = logging.getLogger(__name__)
        self.load(file)
        atexit.register(self.save)
        super().__init__()

    def load(self, file=None):
        if file is None:
            file = self.file
        self.file = file
        if not os.path.isfile(file):
            self.logger.info('Creating new entries file "%s"', self.file)
            with open(file, 'x') as fh:
                fh.writelines(["{}"])
        with open(file, 'r', encoding='utf-8') as fh:
            self.clear()
            self.update(json.load(fh)) # Add all entries from file
        logging.info('Loaded entries from "%s"', self.file)

    def save(self):
        self.logger.info('Saving entries')
        if (
            len(self) == 0
            and os.path.isfile(self.file)
            and os.path.getsize(self.file) <= 2
        ):
            self.logger.warn(
                'Refusing to overwrite file "%s" with empty Storage',
                self.file
            )
            return

        with open(self.file, 'w') as fh:
            json.dump(
                self,
                fh,
                indent=4,
                separators=(',', ' : '),
                sort_keys=True
            )

    def __setitem__(self, key, value):
        key = _normalize_key(key)
        self.logger.info('Set "%s" to "%s"', key, value)
        return super().__setitem__(key, value)

    def __getitem__(self, key):
        key = _normalize_key(key)
        return super().__getitem__(key)

    def __delitem__(self, key):
        key = _normalize_key(key)
        self.logger.info('Deleted "%s"', key)
        return super().__delitem__(key)
