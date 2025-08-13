import os
import time
import hashlib
import json
import base64
from pathlib import Path
import uuid

class FileCache:
    def __init__(self, cache_dir: Path | str | None = None, name: str | None = None, max_files: int = 100):
        self.temporary = False
        if cache_dir is None:
            if name is None:
                name = "tempcache-" + str(uuid.uuid1())
                self.temporary = True
            cache_dir = Path.home() / ".cache" / name
        elif isinstance(cache_dir, str):
            cache_dir = Path(cache_dir)

        self.cache_dir : Path = cache_dir 
        self.max_files : int = max_files
        self.cache_dir.mkdir(exist_ok=True, parents=True)

        # Track access times for LRU eviction (using MD5 safe_key as index)
        self._access_times: dict[str, float] = {}
        self._load_existing_files()

    def _load_existing_files(self):
        """Load existing cache files and their access times."""
        for file_path in self.cache_dir.glob("*.json"):
            if file_path.is_file():
                # Extract safe_key from filename (remove .json extension)
                safe_key = file_path.stem
                # Get modification time from file
                mod_time = file_path.stat().st_mtime
                self._access_times[safe_key] = mod_time

    def _get_file_path(self, key: str) -> Path:
        """Generate safe filename from key using hash."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"

    def _evict_oldest_files(self):
        """Remove oldest files until under max_files limit."""
        while len(self._access_times) >= self.max_files:
            # Find oldest file by access time
            oldest_safe_key = min(self._access_times.keys(),
                                key=lambda k: self._access_times[k])

            # Remove file and tracking
            file_path = self.cache_dir / f"{oldest_safe_key}.json"
            if file_path.exists():
                file_path.unlink()
            del self._access_times[oldest_safe_key]

    def add(self, key: str, data: bytes) -> None:
        """Store bytes data with string key to disk."""
        self._evict_oldest_files()

        file_path = self._get_file_path(key)
        
        # Update access time
        current_time = time.time()
        
        # Create JSON structure with key, data, and creation time
        cache_data = {
            "key": key,
            "data": base64.b64encode(data).decode('utf-8'),
            "created_time": current_time
        }
        
        file_path.write_text(json.dumps(cache_data))
        safe_key = hashlib.md5(key.encode()).hexdigest()
        self._access_times[safe_key] = current_time
        os.utime(file_path, (current_time, current_time))

    def get(self, key: str) -> bytes | None:
        """Retrieve cached bytes data by key."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        # Update access time for LRU using file modification time
        current_time = time.time()
        safe_key = hashlib.md5(key.encode()).hexdigest()
        self._access_times[safe_key] = current_time
        os.utime(file_path, (current_time, current_time))

        # Read JSON and decode base64 data
        try:
            cache_data = json.loads(file_path.read_text())
            return base64.b64decode(cache_data["data"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self._get_file_path(key).exists()

    def remove(self, key: str) -> bool:
        """Remove cached item by key. Returns True if removed, False if not found."""
        file_path = self._get_file_path(key)

        if file_path.exists():
            file_path.unlink()
            safe_key = hashlib.md5(key.encode()).hexdigest()
            _ = self._access_times.pop(safe_key, None)
            return True
        return False

    def clear(self) -> None:
        """Remove all cached files."""
        for file_path in self.cache_dir.glob("*.json"):
            file_path.unlink()
        self._access_times.clear()

    def size(self) -> int:
        """Return total bytes of cached data."""
        total_bytes = 0
        for safe_key in self._access_times.keys():
            file_path = self.cache_dir / f"{safe_key}.json"
            if file_path.exists():
                try:
                    cache_data = json.loads(file_path.read_text())
                    data_bytes = base64.b64decode(cache_data["data"])
                    total_bytes += len(data_bytes)
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        return total_bytes

    def keys(self) -> list[str]:
        """Return list of all cached keys."""
        keys = []
        for safe_key in self._access_times.keys():
            file_path = self.cache_dir / f"{safe_key}.json"
            if file_path.exists():
                try:
                    cache_data = json.loads(file_path.read_text())
                    keys.append(cache_data["key"])
                except (json.JSONDecodeError, KeyError):
                    pass
        return keys
