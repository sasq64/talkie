import base64
import hashlib
import json
import os
import time
import uuid
from pathlib import Path


class FileCache:
    def __init__(
        self,
        cache_dir: Path | str | None = None,
        name: str | None = None,
        max_files: int = 100,
        meta: dict[str, str] | None = None,
    ):
        self.temporary = False
        if cache_dir is None:
            if name is None:
                name = "tempcache-" + str(uuid.uuid1())
                self.temporary = True
            cache_dir = Path.home() / ".cache" / name
        elif isinstance(cache_dir, str):
            cache_dir = Path(cache_dir)

        self.cache_dir: Path = cache_dir
        self.max_files: int = max_files
        self.meta: dict[str, str] = meta or {}
        self.cache_dir.mkdir(exist_ok=True, parents=True)

        # Track access times for LRU eviction (using MD5 safe_key as index)
        self._access_times: dict[str, float] = {}
        self._load_existing_files()

    def set_meta(self, meta: dict[str, str]):
        self.meta = meta

    def _load_existing_files(self):
        """Load existing cache files and their access times."""
        for file_path in self.cache_dir.glob("*.json"):
            if file_path.is_file():
                # Extract safe_key from filename (remove .json extension)
                safe_key = file_path.stem
                # Get modification time from file
                mod_time = file_path.stat().st_mtime
                self._access_times[safe_key] = mod_time

    def _merge_metadata(self, meta: dict[str, str] | None = None) -> dict[str, str]:
        """Merge constructor metadata with method-level metadata."""
        if meta is None:
            return self.meta.copy()
        merged = self.meta.copy()
        merged.update(meta)
        return merged

    def _create_cache_key(self, key: str, meta: dict[str, str] | None = None) -> str:
        """Create cache key by combining original key with metadata."""
        merged_meta = self._merge_metadata(meta)
        if not merged_meta:
            return key

        # Sort metadata items for consistent hashing
        meta_str = "&".join(f"{k}={v}" for k, v in sorted(merged_meta.items()))
        return f"{key}|meta:{meta_str}"

    def _get_file_path(self, key: str, meta: dict[str, str] | None = None) -> Path:
        """Generate safe filename from key and metadata using hash."""
        cache_key = self._create_cache_key(key, meta)
        safe_key = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"

    def _evict_oldest_files(self):
        """Remove oldest files until under max_files limit."""
        while len(self._access_times) >= self.max_files:
            # Find oldest file by access time
            oldest_safe_key = min(
                self._access_times.keys(), key=lambda k: self._access_times[k]
            )

            # Remove file and tracking
            file_path = self.cache_dir / f"{oldest_safe_key}.json"
            if file_path.exists():
                file_path.unlink()
            del self._access_times[oldest_safe_key]

    def add(self, key: str, data: bytes, meta: dict[str, str] | None = None) -> None:
        """Store bytes data with string key to disk."""
        self._evict_oldest_files()

        merged_meta = self._merge_metadata(meta)
        file_path = self._get_file_path(key, meta)

        # Update access time
        current_time = time.time()

        # Create JSON structure with key, data, and creation time
        cache_data = {
            "key": key,
            "data": base64.b64encode(data).decode("utf-8"),
            "created_time": current_time,
        }

        # Only include meta field if metadata is not empty
        if merged_meta:
            cache_data["meta"] = merged_meta

        file_path.write_text(json.dumps(cache_data))
        cache_key = self._create_cache_key(key, meta)
        safe_key = hashlib.md5(cache_key.encode()).hexdigest()
        self._access_times[safe_key] = current_time
        os.utime(file_path, (current_time, current_time))

    def get(self, key: str, meta: dict[str, str] | None = None) -> bytes | None:
        """Retrieve cached bytes data by key."""
        file_path = self._get_file_path(key, meta)

        if not file_path.exists():
            return None

        # Update access time for LRU using file modification time
        current_time = time.time()
        cache_key = self._create_cache_key(key, meta)
        safe_key = hashlib.md5(cache_key.encode()).hexdigest()
        self._access_times[safe_key] = current_time
        os.utime(file_path, (current_time, current_time))

        # Read JSON and decode base64 data
        try:
            cache_data = json.loads(file_path.read_text())
            return base64.b64decode(cache_data["data"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def exists(self, key: str, meta: dict[str, str] | None = None) -> bool:
        """Check if key exists in cache."""
        return self._get_file_path(key, meta).exists()

    def remove(self, key: str, meta: dict[str, str] | None = None) -> bool:
        """Remove cached item by key. Returns True if removed, False if not found."""
        file_path = self._get_file_path(key, meta)

        if file_path.exists():
            file_path.unlink()
            cache_key = self._create_cache_key(key, meta)
            safe_key = hashlib.md5(cache_key.encode()).hexdigest()
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
        for safe_key in self._access_times:
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
        for safe_key in self._access_times:
            file_path = self.cache_dir / f"{safe_key}.json"
            if file_path.exists():
                try:
                    cache_data = json.loads(file_path.read_text())
                    keys.append(cache_data["key"])
                except (json.JSONDecodeError, KeyError):
                    pass
        return keys
