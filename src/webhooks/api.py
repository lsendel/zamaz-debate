"""
Webhook API Endpoints

This module provides REST API endpoints for managing webhook subscriptions.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator

from src.webhooks.models import WebhookEndpoint, WebhookEventType
from src.webhooks.service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookEndpointRequest(BaseModel):
    """Request model for creating/updating webhook endpoints"""
    url: str = Field(..., description="The webhook URL endpoint")
    event_types: List[str] = Field(..., description="List of event types to subscribe to")
    secret: Optional[str] = Field(None, description="Secret key for webhook signature verification")
    description: Optional[str] = Field(None, description="Human-readable description of the webhook")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional HTTP headers")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    retry_delay_seconds: int = Field(60, description="Delay between retry attempts in seconds")
    is_active: bool = Field(True, description="Whether the webhook is active")

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith('http'):
            raise ValueError('URL must start with http or https')
        return v

    @validator('event_types')
    def validate_event_types(cls, v):
        valid_types = {et.value for et in WebhookEventType}
        for event_type in v:
            if event_type not in valid_types:
                raise ValueError(f'Invalid event type: {event_type}. Valid types: {valid_types}')
        return v

    @validator('timeout_seconds')
    def validate_timeout(cls, v):
        if v < 1 or v > 300:
            raise ValueError('Timeout must be between 1 and 300 seconds')
        return v

    @validator('max_retries')
    def validate_max_retries(cls, v):
        if v < 0 or v > 10:
            raise ValueError('Max retries must be between 0 and 10')
        return v


class WebhookEndpointResponse(BaseModel):
    """Response model for webhook endpoints"""
    id: str
    url: str
    event_types: List[str]
    secret: Optional[str] = None
    description: Optional[str] = None
    headers: Dict[str, str]
    timeout_seconds: int
    max_retries: int
    retry_delay_seconds: int
    is_active: bool
    created_at: str
    updated_at: str


class WebhookStatsResponse(BaseModel):
    """Response model for webhook statistics"""
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    pending_deliveries: int
    retry_deliveries: int
    abandoned_deliveries: int
    average_delivery_time_ms: float
    success_rate: float
    last_delivery_at: Optional[str] = None


class WebhookDeliveryAttemptResponse(BaseModel):
    """Response model for webhook delivery attempts"""
    id: str
    endpoint_id: str
    event_type: str
    status: str
    attempt_number: int
    attempted_at: str
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    next_retry_at: Optional[str] = None


class WebhookTestRequest(BaseModel):
    """Request model for testing webhook endpoints"""
    event_type: str
    test_data: Dict[str, Any] = Field(default_factory=dict)

    @validator('event_type')
    def validate_event_type(cls, v):
        valid_types = {et.value for et in WebhookEventType}
        if v not in valid_types:
            raise ValueError(f'Invalid event type: {v}. Valid types: {valid_types}')
        return v


# Global webhook service instance (will be injected)
webhook_service: Optional[WebhookService] = None


def init_webhook_api(service: WebhookService):
    """Initialize the webhook API with a webhook service instance"""
    global webhook_service
    webhook_service = service


def get_webhook_service() -> WebhookService:
    """Get the webhook service instance"""
    if webhook_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook service not initialized"
        )
    return webhook_service


@router.post("/endpoints", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(request: WebhookEndpointRequest):
    """Create a new webhook endpoint"""
    service = get_webhook_service()
    
    # Convert event types to enum values
    event_types = {WebhookEventType(et) for et in request.event_types}
    
    # Create endpoint
    endpoint = WebhookEndpoint(
        url=request.url,
        event_types=event_types,
        secret=request.secret,
        description=request.description,
        headers=request.headers,
        timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
        retry_delay_seconds=request.retry_delay_seconds,
        is_active=request.is_active,
    )
    
    # Add to service
    endpoint_id = service.add_endpoint(endpoint)
    
    # Return response
    return WebhookEndpointResponse(
        id=str(endpoint_id),
        url=endpoint.url,
        event_types=[et.value for et in endpoint.event_types],
        secret=endpoint.secret,
        description=endpoint.description,
        headers=endpoint.headers,
        timeout_seconds=endpoint.timeout_seconds,
        max_retries=endpoint.max_retries,
        retry_delay_seconds=endpoint.retry_delay_seconds,
        is_active=endpoint.is_active,
        created_at=endpoint.created_at.isoformat(),
        updated_at=endpoint.updated_at.isoformat(),
    )


@router.get("/endpoints", response_model=List[WebhookEndpointResponse])
async def list_webhook_endpoints():
    """List all webhook endpoints"""
    service = get_webhook_service()
    endpoints = service.list_endpoints()
    
    return [
        WebhookEndpointResponse(
            id=str(endpoint.id),
            url=endpoint.url,
            event_types=[et.value for et in endpoint.event_types],
            secret=endpoint.secret,
            description=endpoint.description,
            headers=endpoint.headers,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            retry_delay_seconds=endpoint.retry_delay_seconds,
            is_active=endpoint.is_active,
            created_at=endpoint.created_at.isoformat(),
            updated_at=endpoint.updated_at.isoformat(),
        )
        for endpoint in endpoints
    ]


@router.get("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
async def get_webhook_endpoint(endpoint_id: str):
    """Get a specific webhook endpoint"""
    service = get_webhook_service()
    
    try:
        endpoint_uuid = UUID(endpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid endpoint ID format"
        )
    
    endpoint = service.get_endpoint(endpoint_uuid)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found"
        )
    
    return WebhookEndpointResponse(
        id=str(endpoint.id),
        url=endpoint.url,
        event_types=[et.value for et in endpoint.event_types],
        secret=endpoint.secret,
        description=endpoint.description,
        headers=endpoint.headers,
        timeout_seconds=endpoint.timeout_seconds,
        max_retries=endpoint.max_retries,
        retry_delay_seconds=endpoint.retry_delay_seconds,
        is_active=endpoint.is_active,
        created_at=endpoint.created_at.isoformat(),
        updated_at=endpoint.updated_at.isoformat(),
    )


@router.put("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
async def update_webhook_endpoint(endpoint_id: str, request: WebhookEndpointRequest):
    """Update a webhook endpoint"""
    service = get_webhook_service()
    
    try:
        endpoint_uuid = UUID(endpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid endpoint ID format"
        )
    
    # Prepare updates
    updates = {
        "url": request.url,
        "event_types": request.event_types,
        "secret": request.secret,
        "description": request.description,
        "headers": request.headers,
        "timeout_seconds": request.timeout_seconds,
        "max_retries": request.max_retries,
        "retry_delay_seconds": request.retry_delay_seconds,
        "is_active": request.is_active,
    }
    
    # Update endpoint
    success = service.update_endpoint(endpoint_uuid, updates)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found"
        )
    
    # Return updated endpoint
    updated_endpoint = service.get_endpoint(endpoint_uuid)
    return WebhookEndpointResponse(
        id=str(updated_endpoint.id),
        url=updated_endpoint.url,
        event_types=[et.value for et in updated_endpoint.event_types],
        secret=updated_endpoint.secret,
        description=updated_endpoint.description,
        headers=updated_endpoint.headers,
        timeout_seconds=updated_endpoint.timeout_seconds,
        max_retries=updated_endpoint.max_retries,
        retry_delay_seconds=updated_endpoint.retry_delay_seconds,
        is_active=updated_endpoint.is_active,
        created_at=updated_endpoint.created_at.isoformat(),
        updated_at=updated_endpoint.updated_at.isoformat(),
    )


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_endpoint(endpoint_id: str):
    """Delete a webhook endpoint"""
    service = get_webhook_service()
    
    try:
        endpoint_uuid = UUID(endpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid endpoint ID format"
        )
    
    success = service.remove_endpoint(endpoint_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found"
        )


@router.post("/endpoints/{endpoint_id}/test")
async def test_webhook_endpoint(endpoint_id: str, request: WebhookTestRequest):
    """Test a webhook endpoint by sending a test event"""
    service = get_webhook_service()
    
    try:
        endpoint_uuid = UUID(endpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid endpoint ID format"
        )
    
    endpoint = service.get_endpoint(endpoint_uuid)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found"
        )
    
    # Send test webhook
    event_type = WebhookEventType(request.event_type)
    test_data = {
        "test": True,
        "message": f"Test webhook notification for {request.event_type}",
        **request.test_data
    }
    
    delivery_attempts = await service.send_webhook_notification(
        event_type=event_type,
        event_data=test_data
    )
    
    # Find the delivery attempt for this endpoint
    endpoint_attempt = None
    for attempt in delivery_attempts:
        if attempt.endpoint_id == endpoint_uuid:
            endpoint_attempt = attempt
            break
    
    if not endpoint_attempt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test webhook"
        )
    
    return {
        "message": "Test webhook sent",
        "status": endpoint_attempt.status.value,
        "response_status": endpoint_attempt.response_status,
        "error_message": endpoint_attempt.error_message,
        "duration_ms": endpoint_attempt.duration_ms,
    }


@router.get("/stats", response_model=WebhookStatsResponse)
async def get_webhook_stats():
    """Get webhook delivery statistics"""
    service = get_webhook_service()
    stats = service.get_delivery_stats()
    
    return WebhookStatsResponse(
        total_deliveries=stats.total_deliveries,
        successful_deliveries=stats.successful_deliveries,
        failed_deliveries=stats.failed_deliveries,
        pending_deliveries=stats.pending_deliveries,
        retry_deliveries=stats.retry_deliveries,
        abandoned_deliveries=stats.abandoned_deliveries,
        average_delivery_time_ms=stats.average_delivery_time_ms,
        success_rate=stats.success_rate(),
        last_delivery_at=stats.last_delivery_at.isoformat() if stats.last_delivery_at else None,
    )


@router.get("/delivery-history", response_model=List[WebhookDeliveryAttemptResponse])
async def get_delivery_history(limit: int = 50):
    """Get recent webhook delivery attempts"""
    service = get_webhook_service()
    
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000"
        )
    
    delivery_attempts = service.get_delivery_history(limit)
    
    return [
        WebhookDeliveryAttemptResponse(
            id=str(attempt.id),
            endpoint_id=str(attempt.endpoint_id),
            event_type=attempt.payload.event_type.value,
            status=attempt.status.value,
            attempt_number=attempt.attempt_number,
            attempted_at=attempt.attempted_at.isoformat(),
            response_status=attempt.response_status,
            response_body=attempt.response_body,
            error_message=attempt.error_message,
            duration_ms=attempt.duration_ms,
            next_retry_at=attempt.next_retry_at.isoformat() if attempt.next_retry_at else None,
        )
        for attempt in delivery_attempts
    ]


@router.post("/retry-failed")
async def retry_failed_deliveries():
    """Retry failed webhook deliveries"""
    service = get_webhook_service()
    retry_attempts = await service.retry_failed_deliveries()
    
    return {
        "message": f"Retried {len(retry_attempts)} failed deliveries",
        "retry_attempts": len(retry_attempts)
    }


@router.get("/event-types")
async def get_supported_event_types():
    """Get list of supported webhook event types"""
    return {
        "event_types": [
            {
                "value": event_type.value,
                "name": event_type.name,
                "description": _get_event_type_description(event_type)
            }
            for event_type in WebhookEventType
        ]
    }


def _get_event_type_description(event_type: WebhookEventType) -> str:
    """Get human-readable description for event types"""
    descriptions = {
        WebhookEventType.DECISION_MADE: "Triggered when a decision is made by the system",
        WebhookEventType.DEBATE_COMPLETED: "Triggered when a debate is completed",
        WebhookEventType.CONSENSUS_REACHED: "Triggered when consensus is reached in a debate",
        WebhookEventType.DEBATE_INITIATED: "Triggered when a new debate is started",
        WebhookEventType.ROUND_STARTED: "Triggered when a new debate round begins",
        WebhookEventType.ROUND_COMPLETED: "Triggered when a debate round is completed",
        WebhookEventType.COMPLEXITY_ASSESSED: "Triggered when decision complexity is assessed",
        WebhookEventType.DEBATE_CANCELLED: "Triggered when a debate is cancelled",
        WebhookEventType.DEBATE_TIMEOUT: "Triggered when a debate times out",
        WebhookEventType.DEBATE_METRICS_CALCULATED: "Triggered when debate metrics are calculated",
        WebhookEventType.EVOLUTION_TRIGGERED: "Triggered when system evolution is initiated",
        WebhookEventType.PR_CREATED: "Triggered when a pull request is created",
        WebhookEventType.ERROR_OCCURRED: "Triggered when a system error occurs",
    }
    return descriptions.get(event_type, "No description available")