"""
Redis-based checkpointer for LangGraph conversations with TTL support.
"""
import json
import pickle
import base64
import os
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from agent.infra.redis_client import get_redis_client
import redis


class RedisCheckpointer(BaseCheckpointSaver):
    """
    Redis-based checkpoint saver with automatic TTL (Time To Live).
    
    This checkpointer stores conversation states in Redis with automatic expiration
    to prevent memory leaks. Conversations are automatically deleted after the TTL
    expires, or can be manually deleted when the user closes the chat dialog.
    """
    
    def __init__(self, ttl_hours: Optional[int] = None):
        """
        Initialize Redis checkpointer.
        
        Args:
            ttl_hours: Time to live in hours (default from env or 2 hours)
        """
        super().__init__()
        self.redis_client = get_redis_client()
        self.ttl_seconds = (ttl_hours or int(os.getenv('REDIS_TTL_HOURS', '2'))) * 3600
        self.prefix = "langgraph:checkpoint"
    
    def _make_key(self, thread_id: str, checkpoint_id: str) -> str:
        """
        Generate Redis key for a checkpoint.
        
        Args:
            thread_id: Conversation thread ID
            checkpoint_id: Unique checkpoint ID
            
        Returns:
            str: Redis key
        """
        return f"{self.prefix}:{thread_id}:{checkpoint_id}"
    
    def _make_thread_key(self, thread_id: str) -> str:
        """
        Generate Redis key pattern for a thread.
        
        Args:
            thread_id: Conversation thread ID
            
        Returns:
            str: Redis key pattern
        """
        return f"{self.prefix}:{thread_id}:*"
    
    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[dict] = None,
    ) -> RunnableConfig:
        """
        Save a checkpoint to Redis with TTL.
        
        Args:
            config: Configuration containing thread_id
            checkpoint: Checkpoint to save
            metadata: Checkpoint metadata
            
        Returns:
            RunnableConfig: Updated configuration
        """
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        checkpoint_id = checkpoint.get("id", "")
        
        print(f"📝 Saving checkpoint for thread {thread_id}, checkpoint {checkpoint_id}")
        
        # Serialize checkpoint and metadata
        try:
            serialized_checkpoint = self._serialize_checkpoint(checkpoint)
            data = {
                "checkpoint": serialized_checkpoint,
                "metadata": json.dumps(metadata) if metadata else "{}"
            }
            
            # Save to Redis with TTL
            key = self._make_key(thread_id, checkpoint_id)
            self.redis_client.hset(key, mapping=data)
            self.redis_client.expire(key, self.ttl_seconds)
            
            print(f"✅ Checkpoint saved successfully: {key}")
        except Exception as e:
            print(f"❌ Error saving checkpoint: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return config
    
    def get_tuple(self, config: RunnableConfig):
        """
        Get checkpoint tuple (required by LangGraph).
        
        Args:
            config: Configuration containing thread_id
            
        Returns:
            CheckpointTuple or None
        """
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        
        print(f"🔍 get_tuple called for thread {thread_id}")
        
        try:
            # Find all checkpoints for this thread
            pattern = self._make_thread_key(thread_id)
            keys = list(self.redis_client.scan_iter(match=pattern))
            
            if not keys:
                print(f"ℹ️  No existing checkpoints found for thread {thread_id}")
                return None
            
            print(f"📦 Found {len(keys)} checkpoint(s) for thread {thread_id}")
            
            # Get the most recent checkpoint
            latest_key = max(keys)
            
            data = self.redis_client.hgetall(latest_key)  # type: ignore
            if not data:
                print(f"⚠️  Checkpoint key exists but no data: {latest_key}")
                return None
            
            # Deserialize
            checkpoint = self._deserialize_checkpoint(data.get("checkpoint", ""))  # type: ignore
            metadata_str = data.get("metadata", "{}")  # type: ignore
            metadata = json.loads(metadata_str) if metadata_str else {}  # type: ignore
            
            print(f"✅ Checkpoint tuple loaded successfully from {latest_key}")
            
            # Return tuple format expected by LangGraph
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,  # type: ignore
                parent_config=None
            )
            
        except Exception as e:
            print(f"❌ Error in get_tuple: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """
        Retrieve the latest checkpoint for a thread from Redis.
        
        Args:
            config: Configuration containing thread_id
            
        Returns:
            Optional[Checkpoint]: Latest checkpoint or None
        """
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        
        print(f"🔍 Loading checkpoint for thread {thread_id}")
        
        try:
            # Find all checkpoints for this thread
            pattern = self._make_thread_key(thread_id)
            keys = list(self.redis_client.scan_iter(match=pattern))
            
            if not keys:
                print(f"ℹ️  No existing checkpoints found for thread {thread_id}")
                return None
            
            print(f"📦 Found {len(keys)} checkpoint(s) for thread {thread_id}")
            
            # Get the most recent checkpoint
            # Keys are in format: langgraph:checkpoint:{thread_id}:{checkpoint_id}
            # We want the one with the highest checkpoint_id (most recent)
            latest_key = max(keys)
            
            data = self.redis_client.hgetall(latest_key)  # type: ignore
            if not data:
                print(f"⚠️  Checkpoint key exists but no data: {latest_key}")
                return None
            
            # Deserialize and return
            checkpoint = self._deserialize_checkpoint(data.get("checkpoint", ""))  # type: ignore
            print(f"✅ Checkpoint loaded successfully from {latest_key}")
            return checkpoint
            
        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def list(
        self,
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:  # type: ignore
        """
        List checkpoints for a thread.
        
        Args:
            config: Configuration containing thread_id
            filter: Filter criteria (not used in this implementation)
            before: Return checkpoints before this config
            limit: Maximum number of checkpoints to return
            
        Yields:
            CheckpointTuple: Checkpoint tuples for the thread
        """
        if not config:
            return
        
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        pattern = self._make_thread_key(thread_id)
        
        # Get all checkpoint keys for this thread
        keys = sorted(self.redis_client.scan_iter(match=pattern), reverse=True)
        
        count = 0
        for key in keys:
            if limit and count >= limit:
                break
            
            data = self.redis_client.hgetall(key)  # type: ignore
            if data:
                checkpoint = self._deserialize_checkpoint(data.get("checkpoint", "{}"))  # type: ignore
                
                if before and checkpoint["id"] >= before:
                    continue
                
                yield checkpoint
                count += 1
    
    def delete(self, thread_id: str) -> int:
        """
        Delete all checkpoints for a conversation thread.
        
        This should be called when the user closes the chat dialog.
        
        Args:
            thread_id: Conversation thread ID to delete
            
        Returns:
            int: Number of keys deleted
        """
        pattern = self._make_thread_key(thread_id)
        keys = list(self.redis_client.scan_iter(match=pattern))
        
        if keys:
            deleted = self.redis_client.delete(*keys)
            print(f"🗑️  Deleted {deleted} checkpoints for thread {thread_id}")
            return int(deleted) if deleted else 0  # type: ignore
        
        return 0
    
    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> str:
        """
        Serialize checkpoint using pickle and base64.
        
        Args:
            checkpoint: Checkpoint to serialize
            
        Returns:
            str: Base64 encoded pickle string
        """
        try:
            # Use pickle for better serialization of complex objects
            pickled = pickle.dumps(checkpoint)
            # Encode to base64 for Redis string storage
            encoded = base64.b64encode(pickled).decode('utf-8')
            return encoded
        except Exception as e:
            print(f"❌ Error serializing checkpoint: {e}")
            import traceback
            traceback.print_exc()
            # Return empty dict as fallback
            return base64.b64encode(pickle.dumps({})).decode('utf-8')
    
    def _deserialize_checkpoint(self, data: str) -> Any:
        """
        Deserialize checkpoint from base64 pickle string.
        
        Args:
            data: Base64 encoded pickle string
            
        Returns:
            Any: Deserialized checkpoint (dict or Checkpoint object)
        """
        try:
            # Decode from base64
            decoded = base64.b64decode(data.encode('utf-8'))
            # Unpickle the checkpoint
            checkpoint = pickle.loads(decoded)
            return checkpoint
        except Exception as e:
            print(f"❌ Error deserializing checkpoint: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        Store intermediate writes (required by LangGraph).
        
        Args:
            config: Configuration containing thread_id
            writes: Sequence of (channel, value) writes
            task_id: Unique task identifier
            task_path: Task execution path
        """
        # For this implementation, we don't need to store intermediate writes
        # They will be included in the checkpoint when put() is called
        pass
    
    def get_conversation_count(self) -> int:
        """
        Get the total number of active conversations.
        
        Returns:
            int: Number of unique conversation threads
        """
        pattern = f"{self.prefix}:*"
        keys = list(self.redis_client.scan_iter(match=pattern))
        
        # Extract unique thread_ids
        thread_ids = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 3:
                thread_ids.add(parts[2])
        
        return len(thread_ids)
    
    def extend_ttl(self, thread_id: str) -> int:
        """
        Extend the TTL for all checkpoints in a thread (sliding window).
        
        Args:
            thread_id: Conversation thread ID
            
        Returns:
            int: Number of keys updated
        """
        pattern = self._make_thread_key(thread_id)
        keys = list(self.redis_client.scan_iter(match=pattern))
        
        count = 0
        for key in keys:
            self.redis_client.expire(key, self.ttl_seconds)
            count += 1
        
        return count

