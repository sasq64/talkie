import pytest
import tempfile
import shutil
import time
import json
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

    def test_constructor_metadata(self, temp_cache):
        """Test metadata set at constructor level."""
        temp_dir = tempfile.mkdtemp()
        try:
            cache = FileCache(cache_dir=temp_dir, meta={"version": "1.0", "source": "test"})
            
            # Add data without method-level metadata
            cache.add("key1", b"data1")
            
            # Should be able to retrieve with same constructor metadata
            assert cache.get("key1") == b"data1"
            assert cache.exists("key1")
            
            # Should not be retrievable with different metadata
            assert cache.get("key1", {"version": "2.0"}) is None
            assert not cache.exists("key1", {"version": "2.0"})
            
        finally:
            shutil.rmtree(temp_dir)

    def test_method_metadata(self, temp_cache):
        """Test metadata passed to individual methods."""
        key = "test_key"
        data = b"test data"
        meta = {"user": "alice", "type": "image"}
        
        # Add with metadata
        temp_cache.add(key, data, meta)
        
        # Should retrieve with same metadata
        assert temp_cache.get(key, meta) == data
        assert temp_cache.exists(key, meta)
        
        # Should not retrieve without metadata or with different metadata
        assert temp_cache.get(key) is None
        assert temp_cache.get(key, {"user": "bob"}) is None
        assert not temp_cache.exists(key)
        assert not temp_cache.exists(key, {"user": "bob"})

    def test_metadata_merging(self, temp_cache):
        """Test that method metadata overrides constructor metadata."""
        temp_dir = tempfile.mkdtemp()
        try:
            cache = FileCache(cache_dir=temp_dir, meta={"version": "1.0", "env": "test"})
            
            key = "merge_key"
            data = b"merge data"
            method_meta = {"env": "prod", "user": "alice"}  # env overrides constructor
            
            # Add with method metadata that overrides constructor
            cache.add(key, data, method_meta)
            
            # Expected merged metadata: {"version": "1.0", "env": "prod", "user": "alice"}
            expected_meta = {"version": "1.0", "env": "prod", "user": "alice"}
            assert cache.get(key, method_meta) == data
            assert cache.exists(key, method_meta)
            
            # Should not retrieve with just constructor metadata
            assert cache.get(key) is None
            
        finally:
            shutil.rmtree(temp_dir)

    def test_metadata_creates_different_cache_entries(self, temp_cache):
        """Test that same key with different metadata creates different entries."""
        key = "same_key"
        data1 = b"data with meta1"
        data2 = b"data with meta2"
        data3 = b"data without meta"
        
        meta1 = {"type": "image", "format": "png"}
        meta2 = {"type": "text", "format": "json"}
        
        # Add same key with different metadata
        temp_cache.add(key, data1, meta1)
        temp_cache.add(key, data2, meta2)
        temp_cache.add(key, data3)  # No metadata
        
        # Should retrieve different data based on metadata
        assert temp_cache.get(key, meta1) == data1
        assert temp_cache.get(key, meta2) == data2
        assert temp_cache.get(key) == data3
        
        # All should exist independently
        assert temp_cache.exists(key, meta1)
        assert temp_cache.exists(key, meta2)
        assert temp_cache.exists(key)

    def test_metadata_in_json_storage(self, temp_cache):
        """Test that metadata is stored in JSON when present and omitted when empty."""
        key1 = "key_with_meta"
        key2 = "key_without_meta"
        data = b"test data"
        meta = {"user": "alice", "type": "test"}
        
        # Add with metadata
        temp_cache.add(key1, data, meta)
        # Add without metadata  
        temp_cache.add(key2, data)
        
        # Check the JSON files directly
        file_with_meta = temp_cache._get_file_path(key1, meta)
        file_without_meta = temp_cache._get_file_path(key2)
        
        # Parse JSON content
        data_with_meta = json.loads(file_with_meta.read_text())
        data_without_meta = json.loads(file_without_meta.read_text())
        
        # File with metadata should have meta field
        assert "meta" in data_with_meta
        assert data_with_meta["meta"] == meta
        
        # File without metadata should not have meta field
        assert "meta" not in data_without_meta

    def test_metadata_remove_operations(self, temp_cache):
        """Test remove operations with metadata."""
        key = "remove_key"
        data = b"data to remove"
        meta = {"temp": "true", "user": "test"}
        
        # Add with metadata
        temp_cache.add(key, data, meta)
        assert temp_cache.exists(key, meta)
        
        # Remove with correct metadata should work
        assert temp_cache.remove(key, meta) is True
        assert not temp_cache.exists(key, meta)
        
        # Add again and try removing with wrong metadata
        temp_cache.add(key, data, meta)
        assert temp_cache.remove(key, {"wrong": "meta"}) is False
        assert temp_cache.exists(key, meta)  # Should still exist
        
        # Remove with no metadata when entry has metadata should fail
        assert temp_cache.remove(key) is False
        assert temp_cache.exists(key, meta)  # Should still exist

    def test_empty_metadata_handling(self, temp_cache):
        """Test handling of empty metadata."""
        key = "empty_meta_key"
        data = b"test data"
        
        # Empty dict should be treated as no metadata
        temp_cache.add(key, data, {})
        assert temp_cache.get(key) == data
        assert temp_cache.get(key, {}) == data
        assert temp_cache.exists(key)
        assert temp_cache.exists(key, {})
        
        # Check JSON doesn't have meta field
        file_path = temp_cache._get_file_path(key)
        cache_data = json.loads(file_path.read_text())
        assert "meta" not in cache_data

    def test_metadata_with_constructor_and_empty_method(self, temp_cache):
        """Test constructor metadata with empty method metadata."""
        temp_dir = tempfile.mkdtemp()
        try:
            cache = FileCache(cache_dir=temp_dir, meta={"version": "1.0"})
            
            key = "test_key"
            data = b"test data"
            
            # Add with empty method metadata - should use constructor metadata
            cache.add(key, data, {})
            
            # Should retrieve with constructor metadata
            assert cache.get(key) == data
            assert cache.get(key, {}) == data
            assert cache.exists(key)
            
        finally:
            shutil.rmtree(temp_dir)
