"""
Kafka Topic Management

This module handles Kafka topic operations including creation, deletion, and metadata retrieval.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from confluent_kafka import KafkaError
from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource, ResourceType

from .config import KafkaConfig, TOPIC_CONFIGS

logger = logging.getLogger(__name__)


class TopicManager:
    """
    Manages Kafka topic operations
    
    This class provides methods for creating, deleting, and managing Kafka topics
    with proper configuration and error handling.
    """
    
    def __init__(self, config: KafkaConfig, admin_client: AdminClient):
        """
        Initialize the topic manager
        
        Args:
            config: Kafka configuration
            admin_client: Kafka admin client
        """
        self.config = config
        self.admin_client = admin_client
        
        # Statistics
        self._stats = {
            "topics_created": 0,
            "topics_deleted": 0,
            "topics_listed": 0,
            "last_error": None,
        }
    
    async def create_topic(self, topic_name: str, num_partitions: int, 
                          replication_factor: int, config_overrides: Optional[Dict[str, str]] = None) -> bool:
        """
        Create a topic
        
        Args:
            topic_name: Name of the topic to create
            num_partitions: Number of partitions
            replication_factor: Replication factor
            config_overrides: Optional topic configuration overrides
            
        Returns:
            True if topic was created successfully
        """
        try:
            # Check if topic already exists
            if await self._topic_exists(topic_name):
                logger.info(f"Topic {topic_name} already exists")
                return True
            
            # Get base topic config
            base_config = self._get_topic_config(topic_name)
            
            # Apply overrides
            if config_overrides:
                base_config.update(config_overrides)
            
            # Create topic
            new_topic = NewTopic(
                topic=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                config=base_config
            )
            
            # Submit creation request
            futures = self.admin_client.create_topics([new_topic])
            
            # Wait for completion
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._wait_for_topic_creation, futures, topic_name)
            
            self._stats["topics_created"] += 1
            logger.info(f"Successfully created topic {topic_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")
            self._stats["last_error"] = str(e)
            return False
    
    async def delete_topic(self, topic_name: str) -> bool:
        """
        Delete a topic
        
        Args:
            topic_name: Name of the topic to delete
            
        Returns:
            True if topic was deleted successfully
        """
        try:
            # Check if topic exists
            if not await self._topic_exists(topic_name):
                logger.info(f"Topic {topic_name} does not exist")
                return True
            
            # Submit deletion request
            futures = self.admin_client.delete_topics([topic_name])
            
            # Wait for completion
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._wait_for_topic_deletion, futures, topic_name)
            
            self._stats["topics_deleted"] += 1
            logger.info(f"Successfully deleted topic {topic_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete topic {topic_name}: {e}")
            self._stats["last_error"] = str(e)
            return False
    
    async def list_topics(self) -> List[str]:
        """
        List all topics
        
        Returns:
            List of topic names
        """
        try:
            loop = asyncio.get_event_loop()
            cluster_metadata = await loop.run_in_executor(None, self.admin_client.list_topics)
            
            topic_names = list(cluster_metadata.topics.keys())
            self._stats["topics_listed"] += 1
            
            return topic_names
            
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            self._stats["last_error"] = str(e)
            return []
    
    async def get_topic_metadata(self, topic_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a topic
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            Topic metadata dictionary or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            cluster_metadata = await loop.run_in_executor(None, self.admin_client.list_topics, topic_name)
            
            if topic_name not in cluster_metadata.topics:
                return None
            
            topic_metadata = cluster_metadata.topics[topic_name]
            
            # Get topic configuration
            config_resource = ConfigResource(ResourceType.TOPIC, topic_name)
            config_futures = self.admin_client.describe_configs([config_resource])
            config_result = await loop.run_in_executor(None, self._wait_for_config_result, config_futures, topic_name)
            
            # Build metadata dictionary
            metadata = {
                "name": topic_name,
                "partitions": len(topic_metadata.partitions),
                "replication_factor": len(topic_metadata.partitions[0].replicas) if topic_metadata.partitions else 0,
                "partition_details": [],
                "config": config_result,
                "error": topic_metadata.error,
            }
            
            # Add partition details
            for partition_id, partition in topic_metadata.partitions.items():
                partition_info = {
                    "id": partition_id,
                    "leader": partition.leader,
                    "replicas": partition.replicas,
                    "in_sync_replicas": partition.isrs,
                    "error": partition.error,
                }
                metadata["partition_details"].append(partition_info)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get topic metadata for {topic_name}: {e}")
            self._stats["last_error"] = str(e)
            return None
    
    async def create_required_topics(self) -> bool:
        """
        Create all required topics for the system
        
        Returns:
            True if all topics were created successfully
        """
        required_topics = [
            ("debate-events", "Debate lifecycle events"),
            ("decision-events", "Decision events"),
            ("evolution-events", "System evolution events"),
            ("webhook-events", "Webhook notification events"),
            ("metrics-events", "System metrics events"),
        ]
        
        success_count = 0
        
        for topic_suffix, description in required_topics:
            topic_name = self.config.get_topic_name(topic_suffix)
            
            logger.info(f"Creating topic {topic_name} ({description})")
            
            success = await self.create_topic(
                topic_name=topic_name,
                num_partitions=self.config.num_partitions,
                replication_factor=self.config.replication_factor
            )
            
            if success:
                success_count += 1
                # Also create dead letter topic
                dead_letter_topic = self.config.get_dead_letter_topic_name(topic_suffix)
                await self.create_topic(
                    topic_name=dead_letter_topic,
                    num_partitions=1,  # Dead letter topics typically have single partition
                    replication_factor=self.config.replication_factor
                )
        
        logger.info(f"Created {success_count}/{len(required_topics)} required topics")
        return success_count == len(required_topics)
    
    async def _topic_exists(self, topic_name: str) -> bool:
        """Check if a topic exists"""
        try:
            loop = asyncio.get_event_loop()
            cluster_metadata = await loop.run_in_executor(None, self.admin_client.list_topics, topic_name)
            return topic_name in cluster_metadata.topics
        except Exception:
            return False
    
    def _get_topic_config(self, topic_name: str) -> Dict[str, str]:
        """Get topic configuration based on topic name"""
        # Extract topic suffix from full topic name
        topic_suffix = topic_name.replace(f"{self.config.topic_prefix}.", "")
        
        # Get base config for this topic type
        base_config = TOPIC_CONFIGS.get(topic_suffix, {})
        
        # Add default configurations
        default_config = {
            "min.insync.replicas": str(max(1, self.config.replication_factor // 2 + 1)),
            "unclean.leader.election.enable": "false",
            "compression.type": "producer",
        }
        
        # Merge configurations
        return {**default_config, **base_config}
    
    def _wait_for_topic_creation(self, futures: Dict, topic_name: str):
        """Wait for topic creation to complete"""
        future = futures[topic_name]
        try:
            future.result()  # Will raise exception if creation failed
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Topic {topic_name} already exists")
            else:
                raise
    
    def _wait_for_topic_deletion(self, futures: Dict, topic_name: str):
        """Wait for topic deletion to complete"""
        future = futures[topic_name]
        try:
            future.result()  # Will raise exception if deletion failed
        except Exception as e:
            if "does not exist" in str(e).lower():
                logger.info(f"Topic {topic_name} does not exist")
            else:
                raise
    
    def _wait_for_config_result(self, futures: Dict, topic_name: str) -> Dict[str, str]:
        """Wait for config description to complete"""
        future = list(futures.values())[0]
        try:
            result = future.result()
            return {config.name: config.value for config in result.values()}
        except Exception as e:
            logger.warning(f"Failed to get config for {topic_name}: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get topic manager statistics"""
        return {
            **self._stats,
            "config": {
                "topic_prefix": self.config.topic_prefix,
                "num_partitions": self.config.num_partitions,
                "replication_factor": self.config.replication_factor,
            }
        }
    
    def clear_stats(self):
        """Clear topic manager statistics"""
        self._stats = {
            "topics_created": 0,
            "topics_deleted": 0,
            "topics_listed": 0,
            "last_error": None,
        }


class TopicManagerError(Exception):
    """Exception raised by topic manager operations"""
    pass