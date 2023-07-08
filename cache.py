import json
import os
import time


class Cache:
    def __init__(self, filepath_supplier, timeout_sec):
        self.filepath_supplier = filepath_supplier
        self.timeout_sec = timeout_sec
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

    def is_expired(self, filepath):
        return os.path.exists(filepath) and (time.time() - os.path.getmtime(filepath)) > self.timeout_sec
