# Webhook Notification System

The Zamaz Debate System now includes a comprehensive webhook notification system that allows external systems to receive real-time notifications about system events such as decisions, debates, and evolution activities.

## Features

- **Event-Driven Architecture**: Integrates with the existing domain event system
- **Secure Delivery**: HMAC-SHA256 signature verification for webhook security
- **Retry Logic**: Automatic retry with exponential backoff for failed deliveries
- **Delivery Statistics**: Comprehensive metrics and delivery history tracking
- **REST API**: Full REST API for webhook endpoint management
- **Multiple Event Types**: Support for all major system events
- **Flexible Configuration**: Per-endpoint timeout, retry, and header settings

## Supported Event Types

| Event Type | Description |
|------------|-------------|
| `decision_made` | Triggered when a decision is made by the system |
| `debate_completed` | Triggered when a debate is completed |
| `consensus_reached` | Triggered when consensus is reached in a debate |
| `debate_initiated` | Triggered when a new debate is started |
| `round_started` | Triggered when a new debate round begins |
| `round_completed` | Triggered when a debate round is completed |
| `complexity_assessed` | Triggered when decision complexity is assessed |
| `debate_cancelled` | Triggered when a debate is cancelled |
| `debate_timeout` | Triggered when a debate times out |
| `debate_metrics_calculated` | Triggered when debate metrics are calculated |
| `evolution_triggered` | Triggered when system evolution is initiated |
| `pr_created` | Triggered when a pull request is created |
| `error_occurred` | Triggered when a system error occurs |

## Quick Start

### 1. Register a Webhook Endpoint

```bash
curl -X POST http://localhost:8000/webhooks/endpoints \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "event_types": ["decision_made", "debate_completed"],
    "secret": "your-secret-key",
    "description": "My webhook endpoint"
  }'
```

### 2. List Webhook Endpoints

```bash
curl http://localhost:8000/webhooks/endpoints
```

### 3. Get Webhook Statistics

```bash
curl http://localhost:8000/webhooks/stats
```

### 4. Test a Webhook Endpoint

```bash
curl -X POST http://localhost:8000/webhooks/endpoints/{endpoint_id}/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "decision_made",
    "test_data": {"message": "Test notification"}
  }'
```

## REST API Reference

### Webhook Endpoints

#### Create Webhook Endpoint
```
POST /webhooks/endpoints
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "event_types": ["decision_made", "debate_completed"],
  "secret": "optional-secret-key",
  "description": "Optional description",
  "headers": {"X-Custom-Header": "value"},
  "timeout_seconds": 30,
  "max_retries": 3,
  "retry_delay_seconds": 60,
  "is_active": true
}
```

#### List Webhook Endpoints
```
GET /webhooks/endpoints
```

#### Get Webhook Endpoint
```
GET /webhooks/endpoints/{endpoint_id}
```

#### Update Webhook Endpoint
```
PUT /webhooks/endpoints/{endpoint_id}
```

#### Delete Webhook Endpoint
```
DELETE /webhooks/endpoints/{endpoint_id}
```

#### Test Webhook Endpoint
```
POST /webhooks/endpoints/{endpoint_id}/test
```

### Statistics and Monitoring

#### Get Webhook Statistics
```
GET /webhooks/stats
```

**Response:**
```json
{
  "total_deliveries": 150,
  "successful_deliveries": 145,
  "failed_deliveries": 5,
  "pending_deliveries": 0,
  "retry_deliveries": 3,
  "abandoned_deliveries": 2,
  "average_delivery_time_ms": 245.5,
  "success_rate": 96.7,
  "last_delivery_at": "2025-01-15T10:30:00Z"
}
```

#### Get Delivery History
```
GET /webhooks/delivery-history?limit=50
```

#### Retry Failed Deliveries
```
POST /webhooks/retry-failed
```

#### Get Supported Event Types
```
GET /webhooks/event-types
```

## Webhook Payload Format

All webhook notifications follow this standard format:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "decision_made",
  "timestamp": "2025-01-15T10:30:00Z",
  "source": "zamaz-debate-system",
  "version": "1.0",
  "data": {
    "decision_id": "550e8400-e29b-41d4-a716-446655440001",
    "question": "Should we implement feature X?",
    "recommendation": "Yes, implement with proper testing",
    "confidence": 0.85,
    "implementation_required": true
  }
}
```

## Security

### Signature Verification

When a webhook endpoint has a secret configured, all webhook deliveries include an `X-Zamaz-Signature` header with an HMAC-SHA256 signature:

```
X-Zamaz-Signature: sha256=a29d01234567890abcdef1234567890abcdef
```

**Python verification example:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

# Usage
payload = request.get_data(as_text=True)
signature = request.headers.get('X-Zamaz-Signature')
is_valid = verify_webhook_signature(payload, signature, "your-secret")
```

## Error Handling and Retries

### Retry Policy
- **Failed Status Codes**: 4xx and 5xx HTTP status codes trigger retries
- **Network Errors**: Connection timeouts and network errors trigger retries
- **Retry Delay**: Configurable delay between retry attempts (default: 60 seconds)
- **Max Retries**: Configurable maximum retry attempts (default: 3)
- **Abandonment**: Deliveries are abandoned after exceeding max retries

### Error Response Handling
- **2xx Status Codes**: Considered successful delivery
- **3xx Status Codes**: Considered successful delivery
- **4xx Status Codes**: Client errors, will be retried
- **5xx Status Codes**: Server errors, will be retried
- **Timeout**: Connection timeout, will be retried

## Event Examples

### Decision Made Event
```json
{
  "event_type": "decision_made",
  "data": {
    "decision_id": "550e8400-e29b-41d4-a716-446655440001",
    "question": "Should we implement caching?",
    "recommendation": "Yes, implement Redis caching",
    "confidence": 0.92,
    "implementation_required": true,
    "debate_id": "550e8400-e29b-41d4-a716-446655440002"
  }
}
```

### Debate Completed Event
```json
{
  "event_type": "debate_completed",
  "data": {
    "debate_id": "550e8400-e29b-41d4-a716-446655440002",
    "total_rounds": 3,
    "total_arguments": 6,
    "final_consensus": "Implement Redis caching with proper monitoring",
    "decision_id": "550e8400-e29b-41d4-a716-446655440001"
  }
}
```

### Evolution Triggered Event
```json
{
  "event_type": "evolution_triggered",
  "data": {
    "evolution_type": "feature",
    "feature": "webhook_notifications",
    "description": "Added webhook notification system for external integrations",
    "debate_id": "550e8400-e29b-41d4-a716-446655440003"
  }
}
```

## Integration Examples

### Express.js (Node.js)
```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.json());

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-zamaz-signature'];
  const payload = JSON.stringify(req.body);
  
  // Verify signature
  const expectedSignature = 'sha256=' + crypto
    .createHmac('sha256', 'your-secret')
    .update(payload)
    .digest('hex');
  
  if (signature === expectedSignature) {
    console.log('Received webhook:', req.body.event_type);
    console.log('Data:', req.body.data);
    res.status(200).send('OK');
  } else {
    res.status(401).send('Unauthorized');
  }
});
```

### Django (Python)
```python
import hmac
import hashlib
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def webhook_handler(request):
    if request.method == 'POST':
        payload = request.body.decode('utf-8')
        signature = request.headers.get('X-Zamaz-Signature')
        
        # Verify signature
        expected_signature = 'sha256=' + hmac.new(
            b'your-secret',
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(signature, expected_signature):
            data = json.loads(payload)
            print(f"Received webhook: {data['event_type']}")
            print(f"Data: {data['data']}")
            return HttpResponse('OK')
        else:
            return HttpResponse('Unauthorized', status=401)
    
    return HttpResponse('Method not allowed', status=405)
```

## Best Practices

1. **Always Verify Signatures**: Use the provided secret to verify webhook signatures
2. **Handle Failures Gracefully**: Return appropriate HTTP status codes for failed processing
3. **Be Idempotent**: Use the `event_id` to handle duplicate deliveries
4. **Monitor Webhook Health**: Regularly check webhook statistics and fix failing endpoints
5. **Use Appropriate Timeouts**: Set reasonable timeout values for your webhook endpoints
6. **Log Webhook Events**: Keep logs of received webhooks for debugging and monitoring
7. **Test Webhooks**: Use the test endpoint to verify your webhook implementation

## Monitoring and Debugging

### Check Webhook Statistics
```bash
curl http://localhost:8000/webhooks/stats
```

### View Recent Deliveries
```bash
curl http://localhost:8000/webhooks/delivery-history?limit=10
```

### Retry Failed Deliveries
```bash
curl -X POST http://localhost:8000/webhooks/retry-failed
```

### Test Webhook Endpoint
```bash
curl -X POST http://localhost:8000/webhooks/endpoints/{endpoint_id}/test \
  -H "Content-Type: application/json" \
  -d '{"event_type": "decision_made", "test_data": {"test": true}}'
```

## Troubleshooting

### Common Issues

1. **Webhooks Not Receiving**: Check if endpoint is active and subscribed to the correct event types
2. **Signature Verification Fails**: Ensure the secret matches exactly and payload is not modified
3. **Delivery Failures**: Check webhook endpoint URL, network connectivity, and response codes
4. **Missing Events**: Verify event bus is running and webhook handler is subscribed to events

### Debug Steps

1. Check webhook endpoint configuration
2. Verify webhook URL is accessible
3. Test webhook endpoint using the test API
4. Review delivery history for error messages
5. Check system logs for event publishing issues

## Migration Guide

If you're integrating the webhook system into an existing application:

1. **Start the Webhook Service**: Initialize webhook service in your application startup
2. **Configure Event Bus**: Ensure event bus is running and connected to webhook handler
3. **Add API Routes**: Include webhook router in your FastAPI application
4. **Test Integration**: Use the example script to verify webhook functionality
5. **Monitor Delivery**: Set up monitoring for webhook delivery statistics

For more examples and detailed implementation guides, see the `examples/webhook_example.py` file.