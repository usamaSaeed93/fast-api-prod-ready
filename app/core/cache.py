import redis
import json
from typing import Any, Optional, Union, List
from datetime import timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.cache.url,
            max_connections=settings.cache.max_connections,
            decode_responses=True
        )
        self.key_prefix = settings.cache.key_prefix
        self.default_ttl = settings.cache.default_ttl
    
    def _get_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        try:
            full_key = self._get_key(key)
            value = self.redis_client.get(full_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            full_key = self._get_key(key)
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value)
            return self.redis_client.setex(full_key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            full_key = self._get_key(key)
            return bool(self.redis_client.delete(full_key))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        try:
            full_key = self._get_key(key)
            return bool(self.redis_client.exists(full_key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        try:
            full_key = self._get_key(key)
            return self.redis_client.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None
    
    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        try:
            full_key = self._get_key(key)
            return self.redis_client.decrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache decrement error: {e}")
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        try:
            full_key = self._get_key(key)
            return bool(self.redis_client.expire(full_key, ttl))
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False
    
    def get_ttl(self, key: str) -> Optional[int]:
        try:
            full_key = self._get_key(key)
            return self.redis_client.ttl(full_key)
        except Exception as e:
            logger.error(f"Cache TTL error: {e}")
            return None
    
    def flush_pattern(self, pattern: str) -> int:
        try:
            full_pattern = self._get_key(pattern)
            keys = self.redis_client.keys(full_pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache flush pattern error: {e}")
            return 0
    
    def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        try:
            full_keys = [self._get_key(key) for key in keys]
            values = self.redis_client.mget(full_keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
            return result
        except Exception as e:
            logger.error(f"Cache get multiple error: {e}")
            return {}
    
    def set_multiple(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        try:
            ttl = ttl or self.default_ttl
            pipe = self.redis_client.pipeline()
            for key, value in mapping.items():
                full_key = self._get_key(key)
                serialized_value = json.dumps(value)
                pipe.setex(full_key, ttl, serialized_value)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set multiple error: {e}")
            return False
    
    def health_check(self) -> bool:
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False


cache_manager = CacheManager()


def cache_key(*args, **kwargs) -> str:
    key_parts = []
    for arg in args:
        key_parts.append(str(arg))
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    return ":".join(key_parts)


def cached(ttl: int = 3600, key_func: Optional[callable] = None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                cache_key_str = cache_key(func.__name__, *args, **kwargs)
            
            cached_result = cache_manager.get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.set(cache_key_str, result, ttl)
            return result
        
        return wrapper
    return decorator
