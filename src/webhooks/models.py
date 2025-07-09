"""
Webhook Domain Models

This module contains the domain models for webhook notifications system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4


class WebhookEventType(Enum):
    """Supported webhook event types"""
    DECISION_MADE = "decision_made"
    DEBATE_COMPLETED = "debate_completed"
    CONSENSUS_REACHED = "consensus_reached"
    DEBATE_INITIATED = "debate_initiated"
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    COMPLEXITY_ASSESSED = "complexity_assessed"
    DEBATE_CANCELLED = "debate_cancelled"
    DEBATE_TIMEOUT = "debate_timeout"
    DEBATE_METRICS_CALCULATED = "debate_metrics_calculated"
    EVOLUTION_TRIGGERED = "evolution_triggered"
    PR_CREATED = "pr_created"
    ERROR_OCCURRED = "error_occurred"


class WebhookDeliveryStatus(Enum):
    """Status of webhook delivery attempts"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"
    ABANDONED = "abandoned"


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: UUID = field(default_factory=uuid4)
    url: str = ""
    secret: Optional[str] = None
    event_types: Set[WebhookEventType] = field(default_factory=set)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 60

    def __post_init__(self):
        if isinstance(self.event_types, list):
            self.event_types = set(WebhookEventType(et) if isinstance(et, str) else et for et in self.event_types)

    def subscribes_to(self, event_type: WebhookEventType) -> bool:
        """Check if this endpoint subscribes to a specific event type"""
        return self.is_active and (event_type in self.event_types)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": str(self.id),
            "url": self.url,
            "secret": self.secret,
            "event_types": [et.value for et in self.event_types],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "description": self.description,
            "headers": self.headers,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookEndpoint":
        """Create from dictionary"""
        return cls(
            id=UUID(data["id"]),
            url=data["url"],
            secret=data.get("secret"),
            event_types={WebhookEventType(et) for et in data.get("event_types", [])},
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            description=data.get("description"),
            headers=data.get("headers", {}),
            timeout_seconds=data.get("timeout_seconds", 30),
            max_retries=data.get("max_retries", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 60),
        )


@dataclass
class WebhookPayload:
    """Webhook notification payload"""
    event_id: UUID
    event_type: WebhookEventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "zamaz-debate-system"
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source": self.source,
            "version": self.version,
        }


@dataclass
class WebhookDeliveryAttempt:
    """Record of a webhook delivery attempt"""
    id: UUID = field(default_factory=uuid4)
    endpoint_id: UUID = field(default_factory=uuid4)
    payload: WebhookPayload = field(default_factory=lambda: WebhookPayload(
        event_id=uuid4(),
        event_type=WebhookEventType.DECISION_MADE,
        timestamp=datetime.now(),
        data={}
    ))
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    attempt_number: int = 1
    attempted_at: datetime = field(default_factory=datetime.now)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    next_retry_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": str(self.id),
            "endpoint_id": str(self.endpoint_id),
            "payload": self.payload.to_dict(),
            "status": self.status.value,
            "attempt_number": self.attempt_number,
            "attempted_at": self.attempted_at.isoformat(),
            "response_status": self.response_status,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookDeliveryAttempt":
        """Create from dictionary"""
        payload_data = data["payload"]
        payload = WebhookPayload(
            event_id=UUID(payload_data["event_id"]),
            event_type=WebhookEventType(payload_data["event_type"]),
            timestamp=datetime.fromisoformat(payload_data["timestamp"]),
            data=payload_data["data"],
            source=payload_data.get("source", "zamaz-debate-system"),
            version=payload_data.get("version", "1.0"),
        )
        
        return cls(
            id=UUID(data["id"]),
            endpoint_id=UUID(data["endpoint_id"]),
            payload=payload,
            status=WebhookDeliveryStatus(data["status"]),
            attempt_number=data["attempt_number"],
            attempted_at=datetime.fromisoformat(data["attempted_at"]),
            response_status=data.get("response_status"),
            response_body=data.get("response_body"),
            error_message=data.get("error_message"),
            duration_ms=data.get("duration_ms"),
            next_retry_at=datetime.fromisoformat(data["next_retry_at"]) if data.get("next_retry_at") else None,
        )


@dataclass
class WebhookStats:
    """Webhook delivery statistics"""
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    pending_deliveries: int = 0
    retry_deliveries: int = 0
    abandoned_deliveries: int = 0
    average_delivery_time_ms: float = 0.0
    last_delivery_at: Optional[datetime] = None

    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total_deliveries": self.total_deliveries,
            "successful_deliveries": self.successful_deliveries,
            "failed_deliveries": self.failed_deliveries,
            "pending_deliveries": self.pending_deliveries,
            "retry_deliveries": self.retry_deliveries,
            "abandoned_deliveries": self.abandoned_deliveries,
            "average_delivery_time_ms": self.average_delivery_time_ms,
            "success_rate": self.success_rate(),
            "last_delivery_at": self.last_delivery_at.isoformat() if self.last_delivery_at else None,
        }