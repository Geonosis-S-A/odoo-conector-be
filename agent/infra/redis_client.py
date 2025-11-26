"""
Redis client configuration and connection pool management.
"""
import redis
from redis.connection import ConnectionPool
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class RedisClient:
    """Singleton Redis client with connection pooling."""
    
    _instance: Optional['RedisClient'] = None
    _pool: Optional[ConnectionPool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection pool if not already created."""
        if self._pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """Create Redis connection pool."""
        # Intentar usar REDIS_URL primero (Railway, Heroku, etc.)
        redis_url = os.getenv('REDIS_URL')
        
        if redis_url:
            # Usar URL completa de conexión
            self._pool = ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
                max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '10')),
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            connection_info = redis_url.split('@')[-1] if '@' in redis_url else 'Redis URL'
        else:
            # Fallback a variables individuales (desarrollo local)
            host = os.getenv('REDIS_HOST', 'localhost')
            port = int(os.getenv('REDIS_PORT', '6379'))
            password = os.getenv('REDIS_PASSWORD', None)
            db = int(os.getenv('REDIS_DB', '0'))
            max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', '10'))
            
            self._pool = ConnectionPool(
                host=host,
                port=port,
                password=password,
                db=db,
                max_connections=max_connections,
                decode_responses=True,  # Automatically decode responses to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            connection_info = f"{host}:{port}"
        
        # Test connection
        try:
            client = self.get_client()
            client.ping()
            print(f"✅ Redis connected successfully at {connection_info}")
        except redis.ConnectionError as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    def get_client(self) -> redis.Redis:
        """
        Get a Redis client from the connection pool.
        
        Returns:
            redis.Redis: Redis client instance
        """
        return redis.Redis(connection_pool=self._pool)
    
    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
            print("Redis connection pool closed")


# Global instance
_redis_client = None


def get_redis_client() -> redis.Redis:
    """
    Get a Redis client instance (creates singleton if needed).
    
    Returns:
        redis.Redis: Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client.get_client()


def close_redis_connection():
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None

