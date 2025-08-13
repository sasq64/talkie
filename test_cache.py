import pytest
import tempfile
import shutil
import time
from pathlib import Path
from cache import FileCache


@pytest.fixture
def temp_cache():
    """Create a temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp()
    cache = FileCache(cache_dir=temp_dir, max_files=3)
    yield cache
    # Cleanup
    shutil.rmtree(temp_dir)


class TestFileCache:
    
    def test_init_creates_directory(self, temp_cache):
        """Test that cache directory is created on initialization."""
        assert temp_cache.cache_dir.exists()
        assert temp_cache.cache_dir.is_dir()
    
    def test_add_and_get_basic(self, temp_cache):
        """Test basic add and get functionality."""
        key = "test_key"
        data = b"test data"
        
        temp_cache.add(key, data)
        retrieved_data = temp_cache.get(key)
        
        assert retrieved_data == data
    
    def test_get_nonexistent_key(self, temp_cache):
        """Test that getting a nonexistent key returns None."""
        result = temp_cache.get("nonexistent")
        assert result is None
    
    def test_exists(self, temp_cache):
        """Test the exists method."""
        key = "test_key"
        data = b"test data"
        
        assert not temp_cache.exists(key)
        
        temp_cache.add(key, data)
        assert temp_cache.exists(key)
    
    def test_remove(self, temp_cache):
        """Test removing cached items."""
        key = "test_key"
        data = b"test data"
        
        temp_cache.add(key, data)
        assert temp_cache.exists(key)
        
        result = temp_cache.remove(key)
        assert result is True
        assert not temp_cache.exists(key)
        
        # Test removing nonexistent key
        result = temp_cache.remove("nonexistent")
        assert result is False
    
    def test_clear(self, temp_cache):
        """Test clearing all cached items."""
        temp_cache.add("key1", b"data1")
        temp_cache.add("key2", b"data2")
        
        assert temp_cache.size() > 0
        
        temp_cache.clear()
        assert temp_cache.size() == 0
        assert not temp_cache.exists("key1")
        assert not temp_cache.exists("key2")
    
    def test_size(self, temp_cache):
        """Test the size method reports total bytes."""
        assert temp_cache.size() == 0
        
        temp_cache.add("key1", b"a" * 10)
        s1 = temp_cache.size()
        assert s1 >= 10
        
        temp_cache.add("key2", b"b" * 15)
        s2 = temp_cache.size()
        assert s2 >= s1 + 15
        
        temp_cache.remove("key1")
        s3 = temp_cache.size()
        assert s3 <= s2 - 10
    
    def test_keys(self, temp_cache):
        """Test the keys method."""
        assert temp_cache.keys() == []
        
        temp_cache.add("key1", b"data1")
        temp_cache.add("key2", b"data2")
        
        keys = temp_cache.keys()
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys
    
    def test_max_bytes_eviction(self, temp_cache):
        """Oldest files should be evicted when total size exceeds max_bytes."""
        temp_cache.clear()
        base = b"x" * 4000
        temp_cache.add("key1", base)
        time.sleep(0.01)
        temp_cache.add("key2", base)
        time.sleep(0.01)
        temp_cache.add("key3", base)
        assert temp_cache.exists("key1")
        assert temp_cache.exists("key2")
        assert temp_cache.exists("key3")
        time.sleep(0.01)
        temp_cache.add("key4", base)
        assert not temp_cache.exists("key1")
        assert temp_cache.exists("key2")
        assert temp_cache.exists("key3")
        assert temp_cache.exists("key4")
    
    def test_lru_behavior_on_get(self, temp_cache):
        """Accessing a file updates its LRU position for size-based eviction."""
        base = b"x" * 4000
        temp_cache.add("key1", base)
        time.sleep(0.01)
        temp_cache.add("key2", base)
        time.sleep(0.01)
        temp_cache.add("key3", base)
        time.sleep(0.01)
        temp_cache.get("key1")
        time.sleep(0.01)
        temp_cache.add("key4", base)
        assert temp_cache.exists("key1")
        assert not temp_cache.exists("key2")
        assert temp_cache.exists("key3")
        assert temp_cache.exists("key4")
    
    def test_binary_data_handling(self, temp_cache):
        """Test handling of various binary data types."""
        # Test with different types of binary data
        test_cases = [
            ("text", b"Hello, World!"),
            ("empty", b""),
            ("binary", bytes([0, 1, 255, 128, 64])),
            ("unicode", "🌟 Unicode! 🚀".encode('utf-8')),
        ]
        
        for key, data in test_cases:
            temp_cache.add(key, data)
            retrieved = temp_cache.get(key)
            assert retrieved == data
    
    def test_key_collision_safety(self, temp_cache):
        """Test that different keys don't collide even with similar content."""
        temp_cache.add("key1", b"same data")
        temp_cache.add("key2", b"same data")
        
        assert temp_cache.get("key1") == b"same data"
        assert temp_cache.get("key2") == b"same data"
        
        temp_cache.remove("key1")
        assert not temp_cache.exists("key1")
        assert temp_cache.exists("key2")
    
    def test_persistence_across_instances(self):
        """Test that cache files persist on disk across FileCache instances."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create first cache instance and add data
            cache1 = FileCache(cache_dir=temp_dir, max_files=100)
            cache1.add("persistent_key", b"persistent_data")
            
            # Verify file exists on disk
            cache_files = list(Path(temp_dir).glob("*.json"))
            assert len(cache_files) == 1
            
            # Create second cache instance and verify data can still be retrieved
            cache2 = FileCache(cache_dir=temp_dir, max_files=100)
            data = cache2.get("persistent_key")
            
            assert data == b"persistent_data"
            assert cache2.exists("persistent_key")
            # Note: size() will be 0 initially since we don't load existing files on startup
            # but the data is still accessible via get()
        
        finally:
            shutil.rmtree(temp_dir)
    
    def test_special_characters_in_keys(self, temp_cache):
        """Test handling of special characters in keys."""
        special_keys = [
            "key with spaces",
            "key/with/slashes",
            "key\\with\\backslashes",
            "key:with:colons",
            "key|with|pipes",
            "key<with>brackets",
            "key\"with\"quotes",
        ]
        
        for key in special_keys:
            data = f"data for {key}".encode()
            temp_cache.add(key, data)
            retrieved = temp_cache.get(key)
            assert retrieved == data
