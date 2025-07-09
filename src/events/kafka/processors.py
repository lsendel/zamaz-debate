"""
Kafka Event Processors

This module contains specialized processors for handling different types of events
received from Kafka topics.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from src.events.kafka.client import KafkaClient
from src.events.kafka.config import KafkaConfig

logger = logging.getLogger(__name__)


class EventProcessor(ABC):
    """Base class for Kafka event processors"""
    
    def __init__(self, kafka_client: KafkaClient, processor_id: str):
        self.kafka_client = kafka_client
        self.processor_id = processor_id
        self._running = False
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "last_processed_at": None,
            "last_error": None,
        }
    
    @abstractmethod
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """Process a single event"""
        pass
    
    @abstractmethod
    def get_event_types(self) -> List[str]:
        """Get the event types this processor handles"""
        pass
    
    async def start(self):
        """Start the processor"""
        if self._running:
            return
        
        logger.info(f"Starting event processor {self.processor_id}")
        
        # Create consumer for this processor
        event_types = self.get_event_types()
        await self.kafka_client.create_consumer(
            consumer_id=f"processor-{self.processor_id}",
            event_types=event_types,
            handler_callback=self._handle_event
        )
        
        self._running = True
        logger.info(f"Event processor {self.processor_id} started for events: {event_types}")
    
    async def stop(self):
        """Stop the processor"""
        if not self._running:
            return
        
        logger.info(f"Stopping event processor {self.processor_id}")
        
        # Remove consumer
        await self.kafka_client.remove_consumer(f"processor-{self.processor_id}")
        
        self._running = False
        logger.info(f"Event processor {self.processor_id} stopped")
    
    async def _handle_event(self, event_data: Dict[str, Any]):
        """Handle incoming event from Kafka"""
        try:
            success = await self.process_event(event_data)
            
            if success:
                self._stats["events_processed"] += 1
                self._stats["last_processed_at"] = datetime.now()
            else:
                self._stats["events_failed"] += 1
                
        except Exception as e:
            logger.error(f"Error processing event in {self.processor_id}: {e}")
            self._stats["events_failed"] += 1
            self._stats["last_error"] = str(e)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            **self._stats,
            "processor_id": self.processor_id,
            "is_running": self._running,
            "event_types": self.get_event_types(),
        }
    
    def clear_stats(self):
        """Clear processor statistics"""
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "last_processed_at": None,
            "last_error": None,
        }


class DebateEventProcessor(EventProcessor):
    """Processor for debate-related events"""
    
    def __init__(self, kafka_client: KafkaClient, processor_id: str = "debate-processor"):
        super().__init__(kafka_client, processor_id)
        self.active_debates: Set[str] = set()
        self.debate_metrics: Dict[str, Any] = {}
    
    def get_event_types(self) -> List[str]:
        """Get debate event types"""
        return ["debate-events"]
    
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """Process debate events"""
        try:
            event_type = event_data.get("event_type")
            debate_id = event_data.get("event_data", {}).get("debate_id")
            
            if not debate_id:
                logger.warning("Debate event without debate_id")
                return False
            
            # Track debate lifecycle
            if event_type == "debate_initiated":
                await self._handle_debate_initiated(debate_id, event_data)
            elif event_type == "debate_round_started":
                await self._handle_debate_round_started(debate_id, event_data)
            elif event_type == "debate_round_completed":
                await self._handle_debate_round_completed(debate_id, event_data)
            elif event_type == "debate_consensus_reached":
                await self._handle_debate_consensus_reached(debate_id, event_data)
            elif event_type == "debate_completed":
                await self._handle_debate_completed(debate_id, event_data)
            else:
                logger.warning(f"Unknown debate event type: {event_type}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing debate event: {e}")
            return False
    
    async def _handle_debate_initiated(self, debate_id: str, event_data: Dict[str, Any]):
        """Handle debate initiation"""
        self.active_debates.add(debate_id)
        self.debate_metrics[debate_id] = {
            "started_at": datetime.now(),
            "rounds": 0,
            "participants": set(),
            "status": "active"
        }
        
        logger.info(f"Debate {debate_id} initiated")
        
        # Publish metrics event
        await self._publish_metrics_event("debate_initiated", {
            "debate_id": debate_id,
            "active_debates_count": len(self.active_debates)
        })
    
    async def _handle_debate_round_started(self, debate_id: str, event_data: Dict[str, Any]):
        """Handle debate round start"""
        if debate_id in self.debate_metrics:
            self.debate_metrics[debate_id]["rounds"] += 1
            
            participant = event_data.get("event_data", {}).get("participant")
            if participant:
                self.debate_metrics[debate_id]["participants"].add(participant)
        
        logger.debug(f"Debate {debate_id} round started")
    
    async def _handle_debate_round_completed(self, debate_id: str, event_data: Dict[str, Any]):
        """Handle debate round completion"""
        logger.debug(f"Debate {debate_id} round completed")
        
        # Could trigger analysis or notifications here
        pass
    
    async def _handle_debate_consensus_reached(self, debate_id: str, event_data: Dict[str, Any]):
        """Handle debate consensus"""
        if debate_id in self.debate_metrics:
            self.debate_metrics[debate_id]["status"] = "consensus_reached"
        
        logger.info(f"Debate {debate_id} reached consensus")
        
        # Publish metrics event
        await self._publish_metrics_event("debate_consensus_reached", {
            "debate_id": debate_id,
            "rounds": self.debate_metrics.get(debate_id, {}).get("rounds", 0)
        })
    
    async def _handle_debate_completed(self, debate_id: str, event_data: Dict[str, Any]):
        """Handle debate completion"""
        if debate_id in self.active_debates:
            self.active_debates.remove(debate_id)
        
        if debate_id in self.debate_metrics:
            metrics = self.debate_metrics[debate_id]
            metrics["status"] = "completed"
            metrics["completed_at"] = datetime.now()
            
            # Calculate debate duration
            if "started_at" in metrics:
                duration = (metrics["completed_at"] - metrics["started_at"]).total_seconds()
                metrics["duration_seconds"] = duration
        
        logger.info(f"Debate {debate_id} completed")
        
        # Publish metrics event
        await self._publish_metrics_event("debate_completed", {
            "debate_id": debate_id,
            "active_debates_count": len(self.active_debates),
            "duration_seconds": self.debate_metrics.get(debate_id, {}).get("duration_seconds", 0)
        })
    
    async def _publish_metrics_event(self, metric_type: str, data: Dict[str, Any]):
        """Publish metrics event"""
        await self.kafka_client.produce_event(
            event_type="metrics-events",
            event_data={
                "metric_type": metric_type,
                "processor": self.processor_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
        )


class DecisionEventProcessor(EventProcessor):
    """Processor for decision-related events"""
    
    def __init__(self, kafka_client: KafkaClient, processor_id: str = "decision-processor"):
        super().__init__(kafka_client, processor_id)
        self.decision_tracking: Dict[str, Any] = {}
    
    def get_event_types(self) -> List[str]:
        """Get decision event types"""
        return ["decision-events"]
    
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """Process decision events"""
        try:
            event_type = event_data.get("event_type")
            decision_id = event_data.get("event_data", {}).get("decision_id")
            
            if not decision_id:
                logger.warning("Decision event without decision_id")
                return False
            
            # Track decision lifecycle
            if event_type == "decision_made":
                await self._handle_decision_made(decision_id, event_data)
            elif event_type == "decision_approved":
                await self._handle_decision_approved(decision_id, event_data)
            elif event_type == "decision_rejected":
                await self._handle_decision_rejected(decision_id, event_data)
            else:
                logger.warning(f"Unknown decision event type: {event_type}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing decision event: {e}")
            return False
    
    async def _handle_decision_made(self, decision_id: str, event_data: Dict[str, Any]):
        """Handle decision creation"""
        decision_data = event_data.get("event_data", {})
        decision_type = decision_data.get("decision_type")
        method = decision_data.get("method")
        
        self.decision_tracking[decision_id] = {
            "created_at": datetime.now(),
            "decision_type": decision_type,
            "method": method,
            "status": "pending"
        }
        
        logger.info(f"Decision {decision_id} made (type: {decision_type}, method: {method})")
        
        # Publish metrics event
        await self._publish_metrics_event("decision_made", {
            "decision_id": decision_id,
            "decision_type": decision_type,
            "method": method
        })
        
        # Trigger PR creation for complex decisions
        if decision_type == "complex" or decision_type == "evolution":
            await self._trigger_pr_creation(decision_id, event_data)
    
    async def _handle_decision_approved(self, decision_id: str, event_data: Dict[str, Any]):
        """Handle decision approval"""
        if decision_id in self.decision_tracking:
            self.decision_tracking[decision_id]["status"] = "approved"
            self.decision_tracking[decision_id]["approved_at"] = datetime.now()
        
        logger.info(f"Decision {decision_id} approved")
        
        # Publish metrics event
        await self._publish_metrics_event("decision_approved", {
            "decision_id": decision_id
        })
    
    async def _handle_decision_rejected(self, decision_id: str, event_data: Dict[str, Any]):
        """Handle decision rejection"""
        if decision_id in self.decision_tracking:
            self.decision_tracking[decision_id]["status"] = "rejected"
            self.decision_tracking[decision_id]["rejected_at"] = datetime.now()
        
        logger.info(f"Decision {decision_id} rejected")
        
        # Publish metrics event
        await self._publish_metrics_event("decision_rejected", {
            "decision_id": decision_id
        })
    
    async def _trigger_pr_creation(self, decision_id: str, event_data: Dict[str, Any]):
        """Trigger PR creation for complex decisions"""
        # This would integrate with the existing PR service
        pr_event_data = {
            "decision_id": decision_id,
            "event_data": event_data,
            "action": "create_pr"
        }
        
        # Publish to a PR creation topic or service
        await self.kafka_client.produce_event(
            event_type="pr-events",
            event_data=pr_event_data,
            partition_key=decision_id
        )
        
        logger.info(f"Triggered PR creation for decision {decision_id}")
    
    async def _publish_metrics_event(self, metric_type: str, data: Dict[str, Any]):
        """Publish metrics event"""
        await self.kafka_client.produce_event(
            event_type="metrics-events",
            event_data={
                "metric_type": metric_type,
                "processor": self.processor_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
        )


class EvolutionEventProcessor(EventProcessor):
    """Processor for evolution-related events"""
    
    def __init__(self, kafka_client: KafkaClient, processor_id: str = "evolution-processor"):
        super().__init__(kafka_client, processor_id)
        self.evolution_tracking: Dict[str, Any] = {}
    
    def get_event_types(self) -> List[str]:
        """Get evolution event types"""
        return ["evolution-events"]
    
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """Process evolution events"""
        try:
            event_type = event_data.get("event_type")
            evolution_id = event_data.get("event_data", {}).get("evolution_id")
            
            if not evolution_id:
                logger.warning("Evolution event without evolution_id")
                return False
            
            # Track evolution lifecycle
            if event_type == "evolution_triggered":
                await self._handle_evolution_triggered(evolution_id, event_data)
            elif event_type == "evolution_completed":
                await self._handle_evolution_completed(evolution_id, event_data)
            elif event_type == "improvement_suggested":
                await self._handle_improvement_suggested(evolution_id, event_data)
            else:
                logger.warning(f"Unknown evolution event type: {event_type}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing evolution event: {e}")
            return False
    
    async def _handle_evolution_triggered(self, evolution_id: str, event_data: Dict[str, Any]):
        """Handle evolution trigger"""
        evolution_data = event_data.get("event_data", {})
        
        self.evolution_tracking[evolution_id] = {
            "triggered_at": datetime.now(),
            "improvement_type": evolution_data.get("improvement_type"),
            "status": "in_progress"
        }
        
        logger.info(f"Evolution {evolution_id} triggered")
        
        # Publish metrics event
        await self._publish_metrics_event("evolution_triggered", {
            "evolution_id": evolution_id,
            "improvement_type": evolution_data.get("improvement_type")
        })
    
    async def _handle_evolution_completed(self, evolution_id: str, event_data: Dict[str, Any]):
        """Handle evolution completion"""
        if evolution_id in self.evolution_tracking:
            self.evolution_tracking[evolution_id]["status"] = "completed"
            self.evolution_tracking[evolution_id]["completed_at"] = datetime.now()
        
        logger.info(f"Evolution {evolution_id} completed")
        
        # Publish metrics event
        await self._publish_metrics_event("evolution_completed", {
            "evolution_id": evolution_id
        })
    
    async def _handle_improvement_suggested(self, evolution_id: str, event_data: Dict[str, Any]):
        """Handle improvement suggestion"""
        improvement_data = event_data.get("event_data", {})
        
        logger.info(f"Improvement suggested for evolution {evolution_id}")
        
        # Publish metrics event
        await self._publish_metrics_event("improvement_suggested", {
            "evolution_id": evolution_id,
            "description": improvement_data.get("description", "")
        })
    
    async def _publish_metrics_event(self, metric_type: str, data: Dict[str, Any]):
        """Publish metrics event"""
        await self.kafka_client.produce_event(
            event_type="metrics-events",
            event_data={
                "metric_type": metric_type,
                "processor": self.processor_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
        )


class MetricsEventProcessor(EventProcessor):
    """Processor for metrics and monitoring events"""
    
    def __init__(self, kafka_client: KafkaClient, processor_id: str = "metrics-processor"):
        super().__init__(kafka_client, processor_id)
        self.metrics_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 100
    
    def get_event_types(self) -> List[str]:
        """Get metrics event types"""
        return ["metrics-events"]
    
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """Process metrics events"""
        try:
            # Add to buffer
            self.metrics_buffer.append(event_data)
            
            # Flush buffer if it's full
            if len(self.metrics_buffer) >= self.buffer_size:
                await self._flush_metrics()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing metrics event: {e}")
            return False
    
    async def _flush_metrics(self):
        """Flush metrics buffer"""
        if not self.metrics_buffer:
            return
        
        logger.info(f"Flushing {len(self.metrics_buffer)} metrics events")
        
        # Here you would typically send to a monitoring system
        # For now, we'll just log aggregated metrics
        
        # Group by metric type
        metrics_by_type = {}
        for metric in self.metrics_buffer:
            metric_type = metric.get("metric_type", "unknown")
            if metric_type not in metrics_by_type:
                metrics_by_type[metric_type] = []
            metrics_by_type[metric_type].append(metric)
        
        # Log aggregated metrics
        for metric_type, metrics in metrics_by_type.items():
            logger.info(f"Metric type {metric_type}: {len(metrics)} events")
        
        # Clear buffer
        self.metrics_buffer.clear()
    
    async def stop(self):
        """Stop the processor and flush remaining metrics"""
        await self._flush_metrics()
        await super().stop()


class ProcessorManager:
    """Manages multiple event processors"""
    
    def __init__(self, kafka_client: KafkaClient):
        self.kafka_client = kafka_client
        self.processors: Dict[str, EventProcessor] = {}
        self._running = False
    
    async def start(self):
        """Start all processors"""
        if self._running:
            return
        
        logger.info("Starting event processors...")
        
        # Create and start default processors
        processors = [
            DebateEventProcessor(self.kafka_client),
            DecisionEventProcessor(self.kafka_client),
            EvolutionEventProcessor(self.kafka_client),
            MetricsEventProcessor(self.kafka_client),
        ]
        
        for processor in processors:
            await processor.start()
            self.processors[processor.processor_id] = processor
        
        self._running = True
        logger.info(f"Started {len(processors)} event processors")
    
    async def stop(self):
        """Stop all processors"""
        if not self._running:
            return
        
        logger.info("Stopping event processors...")
        
        for processor in self.processors.values():
            await processor.stop()
        
        self.processors.clear()
        self._running = False
        logger.info("Event processors stopped")
    
    def add_processor(self, processor: EventProcessor):
        """Add a custom processor"""
        self.processors[processor.processor_id] = processor
    
    def remove_processor(self, processor_id: str):
        """Remove a processor"""
        if processor_id in self.processors:
            del self.processors[processor_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all processors"""
        return {
            "is_running": self._running,
            "processor_count": len(self.processors),
            "processors": {
                processor_id: processor.get_stats() 
                for processor_id, processor in self.processors.items()
            }
        }
    
    def clear_stats(self):
        """Clear statistics for all processors"""
        for processor in self.processors.values():
            processor.clear_stats()


class EventProcessorError(Exception):
    """Exception raised by event processor operations"""
    pass