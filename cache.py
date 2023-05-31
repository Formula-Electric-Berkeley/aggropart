import json
import os
import time


class Cache:
    def __init__(self, filepath, timeout_sec):
        self.filepath = filepath
        self.timeout_sec = timeout_sec
        self.cache = {}


    def get(self, key, updater, force_refresh=False):
        used_cached = False
        refresh = force_refresh or self.is_expired()
        if not refresh and key not in self.cache and os.path.exists(self.filepath):
            with open(self.filepath, 'r') as fp:
                self.cache[key] = json.load(fp)
                used_cached = True

        if key not in self.cache or refresh:
            os.makedirs(self.filepath[:self.filepath.rindex('/')], exist_ok=True)
            updater(self.cache, key)
            with open(self.filepath, 'w') as fp:
                json.dump(self.cache[key], fp, indent=4)
        
        return self.cache[key], used_cached


    def is_expired(self):
        return (time.time() - os.path.getmtime(self.filepath)) > self.timeout_sec