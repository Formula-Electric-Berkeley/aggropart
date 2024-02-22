import json
import os
import time

import common


common.init_env()


class Cache:
    def __init__(self, filepath_supplier, timeout_sec=os.environ['CACHE_TIMEOUT_SEC']):
        self.filepath_supplier = filepath_supplier
        # Default timeout is 4 hours, superceded by .env timeout
        self._timeout_sec = int(timeout_sec) if timeout_sec and len(timeout_sec) != 0 else 14400
        self.cache = {}

    def get(self, key, updater, force_refresh=False):
        used_cached = False
        filepath = self.filepath_supplier(key)
        refresh = force_refresh or self.is_expired(filepath)

        if not refresh and key not in self.cache and os.path.exists(filepath):
            with open(filepath, 'r') as fp:
                self.cache[key] = json.load(fp)
                used_cached = True

        if key not in self.cache or refresh:
            os.makedirs(filepath[:filepath.rindex('/')], exist_ok=True)
            updater(self.cache, key)
            with open(filepath, 'w') as fp:
                json.dump(self.cache[key], fp, indent=4)

        return self.cache[key], used_cached
    
    def set_timeout(self, timeout_sec):
        self._timeout_sec = int(timeout_sec)

    def is_expired(self, filepath):
        return os.path.exists(filepath) and (time.time() - os.path.getmtime(filepath)) > self._timeout_sec
