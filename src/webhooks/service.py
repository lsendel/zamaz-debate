"""
Webhook Service

This module implements the webhook notification service for system events.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

import httpx
from httpx import AsyncClient, Response

from src.webhooks.models import (
    WebhookDeliveryAttempt,
    WebhookDeliveryStatus,
    WebhookEndpoint,
    WebhookEventType,
    WebhookPayload,
    WebhookStats,
)

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service for managing webhook subscriptions and delivering notifications
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/webhooks")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.endpoints_file = self.data_dir / "endpoints.json"
        self.delivery_log_file = self.data_dir / "delivery_log.json"
        
        self._endpoints: Dict[UUID, WebhookEndpoint] = {}
        self._delivery_attempts: List[WebhookDeliveryAttempt] = []
        self._stats = WebhookStats()
        
        # Load persisted data
        self._load_endpoints()
        self._load_delivery_log()
        
        # HTTP client for webhook delivery
        self._http_client: Optional[AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()

    async def start(self):
        """Start the webhook service"""
        self._http_client = AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        logger.info("Webhook service started")

    async def stop(self):
        """Stop the webhook service"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Webhook service stopped")

    def add_endpoint(self, endpoint: WebhookEndpoint) -> UUID:
        """Add a new webhook endpoint"""
        endpoint.updated_at = datetime.now()
        self._endpoints[endpoint.id] = endpoint
        self._save_endpoints()
        
        logger.info(f"Added webhook endpoint: {endpoint.url} for events: {[et.value for et in endpoint.event_types]}")
        return endpoint.id

    def update_endpoint(self, endpoint_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update an existing webhook endpoint"""
        if endpoint_id not in self._endpoints:
            return False
        
        endpoint = self._endpoints[endpoint_id]
        
        # Update allowed fields
        for key, value in updates.items():
            if key == "event_types" and isinstance(value, list):
                endpoint.event_types = {WebhookEventType(et) for et in value}
            elif hasattr(endpoint, key) and key not in ["id", "created_at"]:
                setattr(endpoint, key, value)
        
        endpoint.updated_at = datetime.now()
        self._save_endpoints()
        
        logger.info(f"Updated webhook endpoint: {endpoint_id}")
        return True

    def remove_endpoint(self, endpoint_id: UUID) -> bool:
        """Remove a webhook endpoint"""
        if endpoint_id not in self._endpoints:
            return False
        
        del self._endpoints[endpoint_id]
        self._save_endpoints()
        
        logger.info(f"Removed webhook endpoint: {endpoint_id}")
        return True

    def get_endpoint(self, endpoint_id: UUID) -> Optional[WebhookEndpoint]:
        """Get a webhook endpoint by ID"""
        return self._endpoints.get(endpoint_id)

    def list_endpoints(self) -> List[WebhookEndpoint]:
        """List all webhook endpoints"""
        return list(self._endpoints.values())

    def get_endpoints_for_event(self, event_type: WebhookEventType) -> List[WebhookEndpoint]:
        """Get all endpoints that subscribe to a specific event type"""
        return [
            endpoint for endpoint in self._endpoints.values()
            if endpoint.subscribes_to(event_type)
        ]

    async def send_webhook_notification(
        self,
        event_type: WebhookEventType,
        event_data: Dict[str, Any],
        event_id: Optional[UUID] = None,
    ) -> List[WebhookDeliveryAttempt]:
        """
        Send webhook notifications to all subscribed endpoints
        
        Args:
            event_type: The type of event that occurred
            event_data: The event data payload
            event_id: Optional event ID (will generate if not provided)
            
        Returns:
            List of delivery attempts
        """
        if not self._http_client:
            logger.warning("Webhook service not started, cannot send notifications")
            return []

        event_id = event_id or uuid4()
        timestamp = datetime.now()
        
        # Create webhook payload
        payload = WebhookPayload(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            data=event_data,
        )
        
        # Get all endpoints that subscribe to this event type
        endpoints = self.get_endpoints_for_event(event_type)
        
        if not endpoints:
            logger.debug(f"No endpoints subscribed to {event_type.value}")
            return []
        
        # Send notifications to all subscribed endpoints
        delivery_attempts = []
        tasks = []
        
        for endpoint in endpoints:
            task = asyncio.create_task(self._deliver_webhook(endpoint, payload))
            tasks.append(task)
        
        # Wait for all deliveries to complete
        completed_attempts = await asyncio.gather(*tasks, return_exceptions=True)
        
        for attempt in completed_attempts:
            if isinstance(attempt, WebhookDeliveryAttempt):
                delivery_attempts.append(attempt)
                self._delivery_attempts.append(attempt)
            else:
                logger.error(f"Webhook delivery task failed: {attempt}")
        
        # Update stats
        self._update_stats(delivery_attempts)
        
        # Save delivery log
        self._save_delivery_log()
        
        logger.info(f"Sent {len(delivery_attempts)} webhook notifications for {event_type.value}")
        return delivery_attempts

    async def _deliver_webhook(
        self,
        endpoint: WebhookEndpoint,
        payload: WebhookPayload,
    ) -> WebhookDeliveryAttempt:
        """
        Deliver a webhook notification to a specific endpoint
        
        Args:
            endpoint: The webhook endpoint to deliver to
            payload: The webhook payload
            
        Returns:
            WebhookDeliveryAttempt record
        """
        attempt = WebhookDeliveryAttempt(
            endpoint_id=endpoint.id,
            payload=payload,
            status=WebhookDeliveryStatus.PENDING,
            attempt_number=1,
            attempted_at=datetime.now(),
        )
        
        start_time = time.time()
        
        try:
            # Prepare request
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Zamaz-Debate-System/1.0",
                **endpoint.headers,
            }
            
            payload_data = payload.to_dict()
            payload_json = json.dumps(payload_data)
            
            # Add signature if secret is configured
            if endpoint.secret:
                signature = self._generate_signature(payload_json, endpoint.secret)
                headers["X-Zamaz-Signature"] = signature
            
            # Make HTTP request
            response = await self._http_client.post(
                endpoint.url,
                headers=headers,
                content=payload_json,
                timeout=endpoint.timeout_seconds,
            )
            
            # Record response
            attempt.response_status = response.status_code
            attempt.response_body = response.text[:1000]  # Truncate large responses
            attempt.duration_ms = int((time.time() - start_time) * 1000)
            
            # Check if delivery was successful
            if 200 <= response.status_code < 300:
                attempt.status = WebhookDeliveryStatus.DELIVERED
                logger.debug(f"Webhook delivered successfully to {endpoint.url}")
            else:
                attempt.status = WebhookDeliveryStatus.FAILED
                attempt.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.warning(f"Webhook delivery failed to {endpoint.url}: {attempt.error_message}")
                
        except Exception as e:
            attempt.status = WebhookDeliveryStatus.FAILED
            attempt.error_message = str(e)
            attempt.duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Webhook delivery exception to {endpoint.url}: {e}")
        
        return attempt

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload"""
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, signature)

    async def retry_failed_deliveries(self) -> List[WebhookDeliveryAttempt]:
        """Retry failed webhook deliveries"""
        if not self._http_client:
            return []
        
        now = datetime.now()
        retry_attempts = []
        
        for attempt in self._delivery_attempts:
            if (attempt.status == WebhookDeliveryStatus.FAILED and 
                attempt.next_retry_at and 
                attempt.next_retry_at <= now):
                
                endpoint = self.get_endpoint(attempt.endpoint_id)
                if endpoint and attempt.attempt_number < endpoint.max_retries:
                    # Create new retry attempt
                    retry_attempt = WebhookDeliveryAttempt(
                        endpoint_id=attempt.endpoint_id,
                        payload=attempt.payload,
                        status=WebhookDeliveryStatus.RETRY_PENDING,
                        attempt_number=attempt.attempt_number + 1,
                        attempted_at=now,
                    )
                    
                    # Attempt delivery
                    result = await self._deliver_webhook(endpoint, attempt.payload)
                    result.attempt_number = retry_attempt.attempt_number
                    
                    if result.status == WebhookDeliveryStatus.FAILED:
                        if result.attempt_number >= endpoint.max_retries:
                            result.status = WebhookDeliveryStatus.ABANDONED
                        else:
                            result.next_retry_at = now + timedelta(seconds=endpoint.retry_delay_seconds)
                    
                    retry_attempts.append(result)
                    self._delivery_attempts.append(result)
                    
                    # Mark original attempt as superseded
                    attempt.status = WebhookDeliveryStatus.RETRY_PENDING
        
        if retry_attempts:
            self._update_stats(retry_attempts)
            self._save_delivery_log()
            logger.info(f"Retried {len(retry_attempts)} failed webhook deliveries")
        
        return retry_attempts

    def get_delivery_stats(self) -> WebhookStats:
        """Get webhook delivery statistics"""
        return self._stats

    def get_delivery_history(self, limit: int = 100) -> List[WebhookDeliveryAttempt]:
        """Get recent delivery attempts"""
        return sorted(
            self._delivery_attempts,
            key=lambda x: x.attempted_at,
            reverse=True
        )[:limit]

    def _update_stats(self, delivery_attempts: List[WebhookDeliveryAttempt]):
        """Update delivery statistics"""
        for attempt in delivery_attempts:
            self._stats.total_deliveries += 1
            
            if attempt.status == WebhookDeliveryStatus.DELIVERED:
                self._stats.successful_deliveries += 1
            elif attempt.status == WebhookDeliveryStatus.FAILED:
                self._stats.failed_deliveries += 1
            elif attempt.status == WebhookDeliveryStatus.PENDING:
                self._stats.pending_deliveries += 1
            elif attempt.status == WebhookDeliveryStatus.RETRY_PENDING:
                self._stats.retry_deliveries += 1
            elif attempt.status == WebhookDeliveryStatus.ABANDONED:
                self._stats.abandoned_deliveries += 1
            
            # Update average delivery time
            if attempt.duration_ms:
                current_avg = self._stats.average_delivery_time_ms
                total_successful = self._stats.successful_deliveries
                if total_successful > 0:
                    self._stats.average_delivery_time_ms = (
                        (current_avg * (total_successful - 1) + attempt.duration_ms) / total_successful
                    )
                else:
                    self._stats.average_delivery_time_ms = attempt.duration_ms
            
            # Update last delivery time
            if (not self._stats.last_delivery_at or 
                attempt.attempted_at > self._stats.last_delivery_at):
                self._stats.last_delivery_at = attempt.attempted_at

    def _load_endpoints(self):
        """Load webhook endpoints from disk"""
        if self.endpoints_file.exists():
            try:
                with open(self.endpoints_file, "r") as f:
                    data = json.load(f)
                
                for endpoint_data in data.get("endpoints", []):
                    endpoint = WebhookEndpoint.from_dict(endpoint_data)
                    self._endpoints[endpoint.id] = endpoint
                
                logger.info(f"Loaded {len(self._endpoints)} webhook endpoints")
            except Exception as e:
                logger.error(f"Failed to load webhook endpoints: {e}")

    def _save_endpoints(self):
        """Save webhook endpoints to disk"""
        try:
            data = {
                "endpoints": [endpoint.to_dict() for endpoint in self._endpoints.values()],
                "updated_at": datetime.now().isoformat(),
            }
            
            with open(self.endpoints_file, "w") as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save webhook endpoints: {e}")

    def _load_delivery_log(self):
        """Load delivery attempts from disk"""
        if self.delivery_log_file.exists():
            try:
                with open(self.delivery_log_file, "r") as f:
                    data = json.load(f)
                
                for attempt_data in data.get("delivery_attempts", []):
                    attempt = WebhookDeliveryAttempt.from_dict(attempt_data)
                    self._delivery_attempts.append(attempt)
                
                # Recalculate stats
                self._stats = WebhookStats()
                if self._delivery_attempts:
                    self._update_stats(self._delivery_attempts)
                
                logger.info(f"Loaded {len(self._delivery_attempts)} delivery attempts")
            except Exception as e:
                logger.error(f"Failed to load delivery log: {e}")

    def _save_delivery_log(self):
        """Save delivery attempts to disk"""
        try:
            # Only keep recent attempts to prevent log file from growing too large
            recent_attempts = self.get_delivery_history(1000)
            
            data = {
                "delivery_attempts": [attempt.to_dict() for attempt in recent_attempts],
                "updated_at": datetime.now().isoformat(),
            }
            
            with open(self.delivery_log_file, "w") as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save delivery log: {e}")