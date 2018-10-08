from abc import ABC, abstractmethod
from collections import UserDict
import atexit
import config
import json
import logging
import os

class KeyExistsError(RuntimeError):
    pass

def _normalize_key(key):
    return key.strip().casefold()

def storage_injector(store_type, store_id):
    storage_args = { 'store_type' : store_type, 'store_id' : store_id }
    if config.storage_dir:
        return FileStorage(**storage_args)
    if config.mongodb_uri:
        return MongoStorage(**storage_args)
    return None

class Storage(ABC, UserDict):
    """A subclass of UserDict with additional methods for storing and
    retrieving the mappings to and from JSON files, respectively.
    """

    # pylint: disable=unused-argument
    def __init__(self, store_type, store_id):
        super().__init__()
        self.store_type = store_type
        self.store_id = store_id
        self.logger = logging.getLogger('dragonbot.' + __name__)
        atexit.register(self.save)

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def save(self):
        pass

    def __setitem__(self, key, value):
        key = _normalize_key(key)
        self.logger.debug('Set "%s" to "%s"', key, value)
        return super().__setitem__(key, value)

    def __getitem__(self, key):
        key = _normalize_key(key)
        return super().__getitem__(key)

    def __delitem__(self, key):
        key = _normalize_key(key)
        if key in self:
            self.logger.info('Deleted "%s"', key)
            return super().__delitem__(key)
        raise KeyError(f'Key "{key}" does not exist.')

    def __contains__(self, key):
        key = _normalize_key(key)
        return super().__contains__(key)

    def as_text_list(self):
        return ", ".join(sorted(self))


class FileStorage(Storage):
    """Storage object for flat-JSON-file storage."""

    def __init__(self, store_type, store_id):
        super().__init__(store_type, store_id)
        server_dir = os.path.join(
            config.storage_dir,
            str(store_id)
        )
        self.file = os.path.join(server_dir, f'{store_type}.json')
        try:
            os.mkdir(server_dir)
        except FileExistsError:
            pass
        self.load()

    def load(self):
        if not os.path.isfile(self.file):
            self.logger.info('Creating new entries file "%s"', self.file)
            with open(self.file, 'x') as fh:
                fh.writelines(["{}"])
        with open(self.file, 'r', encoding='utf-8') as fh:
            self.clear()
            self.update(json.load(fh)) # Add all entries from file
        self.logger.info(
            '[%d] Loaded %d %s(s) from "%s"',
            self.store_id,
            len(self),
            self.store_type,
            self.file
        )

    def save(self):
        self.logger.info('Saving %s for %s', self.store_type, self.store_id)
        if (
            not self.data
            and os.path.isfile(self.file)
            and os.path.getsize(self.file) >= 2
        ):
            self.logger.warning(
                'Refusing to overwrite file "%s" with empty FileStorage',
                self.file
            )
            return

        with open(self.file, 'w') as fh:
            json.dump(
                self.data,
                fh,
                indent=4,
                separators=(',', ' : '),
                sort_keys=True
            )

class MongoStorage(Storage):
    def __init__(self, store_type, store_id):
        super().__init__(store_type, store_id)
        self.db = config.mongo.get_default_database()
        self.load()

    def load(self):
        collection = self.db[self.store_type]
        stored = collection.find_one({ '_id' : self.store_id })
        if stored is None:
            self.logger.info('No document found for %s', self.store_id)
            stored = collection.insert_one({
                '_id' : self.store_id,
                'values' : {}
            })
            self.logger.info('Created document with ID %s', stored.inserted_id)
        else:
            self.logger.info('Loaded document for %s', self.store_id)
            if 'values' not in stored:
                raise ValueError(f'Invalid document in database: {stored}');
            self.clear()
            self.update(stored['values'])
            self.logger.info(
                '[%d] Loaded %d %s(s) from database',
                self.store_id,
                len(self),
                self.store_type
            )

    def save(self):
        self.logger.info('Saving entries')
        if not self.data:
            self.logger.warning(
                'Refusing to overwrite document with empty MongoStorage'
            )
            return
        collection = self.db[self.store_type]
        result = collection.update_one(
            { '_id' : self.store_id },
            { '$set': { 'values' : self.data } }
        )
        if result.matched_count == 0:
            self.logger.warning(
                'Failed to match document in %s with _id %s',
                self.store_type,
                self.store_id
            )
        if result.modified_count == 0:
            self.logger.warning(
                'Failed to update document in %s with _id %s',
                self.store_type,
                self.store_id
            )
        else:
            self.logger.info(
                'Updated document in %s with _id %s',
                self.store_type,
                self.store_id
            )
