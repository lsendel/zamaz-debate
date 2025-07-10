# Orchestration Workflow Setup Guide

This guide provides step-by-step instructions for setting up and integrating the new orchestration workflow system with the existing Zamaz Debate System.

## Prerequisites

1. **Existing Zamaz Debate System** must be installed and working
2. **Python 3.8+** with virtual environment
3. **Optional**: Ollama for local LLM orchestration
4. **Optional**: Grok API key for cloud LLM orchestration

## Installation Steps

### 1. Install Additional Dependencies

Add these packages to your `requirements.txt`:

```txt
aiohttp>=3.8.0
pyyaml>=6.0
ollama-python>=0.1.7  # Optional, for Ollama integration
```

Install the dependencies:

```bash
./venv/bin/pip install -r requirements.txt
```

### 2. Environment Configuration

Add these variables to your `.env` file:

```bash
# Orchestration Configuration
USE_ORCHESTRATION=true
USE_OLLAMA_ORCHESTRATION=false  # Set to true if using Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.3

# Grok Integration (optional)
GROK_API_KEY=your-grok-api-key-here
GROK_MODEL=grok-1

# Cost Optimization
ENABLE_COST_OPTIMIZATION=true
ENABLE_WORKFLOW_CACHING=true
```

### 3. Ollama Setup (Optional but Recommended)

For local, cost-free orchestration:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull recommended model
ollama pull llama3.3

# Test Ollama
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.3",
  "prompt": "Test prompt",
  "stream": false
}'
```

### 4. Integration with DebateNucleus

Modify `src/core/nucleus.py` to use the orchestration service:

```python
# Add import
from services.orchestration_service import OrchestrationService, create_orchestrated_debate_result

class DebateNucleus:
    def __init__(self, event_bus=None):
        # ... existing initialization ...
        
        # Add orchestration service
        self.orchestration_service = OrchestrationService(self.ai_factory)
        self.use_orchestration = os.getenv("USE_ORCHESTRATION", "false").lower() == "true"

    async def _run_debate(self, question: str, context: str, complexity: str) -> Dict:
        """Run a debate - now with orchestration support"""
        
        if self.use_orchestration and complexity in ["complex", "moderate"]:
            # Use new orchestration system
            try:
                result = await self.orchestration_service.orchestrate_debate(
                    question, context, complexity
                )
                
                # Convert to expected format
                debate_id = f"orchestrated_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return await create_orchestrated_debate_result(result, debate_id)
                
            except Exception as e:
                logger.warning(f"Orchestration failed, falling back to simple debate: {e}")
                # Fall through to existing implementation
        
        # Existing implementation for simple debates or fallback
        # ... rest of existing _run_debate method ...
```

### 5. Testing the Integration

Test the orchestration system:

```bash
# Test orchestration service
./venv/bin/python -c "
import asyncio
from services.orchestration_service import OrchestrationService

async def test():
    service = OrchestrationService()
    result = await service.orchestrate_debate(
        'Should we implement caching for our API?',
        'API response times are slow',
        'moderate'
    )
    print(f'Workflow: {result.execution_summary[\"workflow_id\"]}')
    print(f'Cost: \${result.total_cost:.4f}')
    print(f'State: {result.execution_summary[\"final_state\"]}')

asyncio.run(test())
"
```

Test through the web interface:

```bash
# Start the system
make run

# Test decision with orchestration
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Should we implement a microservices architecture?",
    "context": "We have scalability concerns with our monolith"
  }'
```

### 6. Monitoring and Debugging

Check orchestration logs:

```bash
# Enable debug logging in your Python logging config
import logging
logging.getLogger('src.workflows').setLevel(logging.DEBUG)
logging.getLogger('src.orchestration').setLevel(logging.DEBUG)
logging.getLogger('services.orchestration_service').setLevel(logging.DEBUG)
```

View orchestration statistics:

```python
from services.orchestration_service import OrchestrationService

service = OrchestrationService()
stats = service.get_workflow_stats()
print(json.dumps(stats, indent=2))
```

## Configuration Options

### Workflow Selection

The system automatically selects workflows based on:

1. **Question complexity** (simple → simple_debate, complex → complex_debate)
2. **LLM analysis** (when `USE_OLLAMA_ORCHESTRATION=true`)
3. **Manual override** (specify `preferred_workflow` parameter)

### Cost Optimization

- **Local Ollama**: Free orchestration decisions
- **Grok Integration**: Low-cost cloud orchestration
- **Caching**: Reuse orchestration decisions for similar questions
- **Fallback**: Graceful degradation to simple debates

### Performance Tuning

```bash
# .env configuration
ORCHESTRATION_TIMEOUT=60
MAX_WORKFLOW_EXECUTION_TIME=1800
ENABLE_WORKFLOW_CACHING=true
CACHE_TTL_SECONDS=3600
```

## Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Restart Ollama
   ollama serve
   ```

2. **Workflow Definition Not Found**
   ```bash
   # Check workflow definitions
   ls src/workflows/definitions/
   
   # Verify YAML syntax
   python -c "import yaml; yaml.safe_load(open('src/workflows/definitions/simple_debate.yaml'))"
   ```

3. **Orchestration Service Not Working**
   ```bash
   # Test with mock orchestrator
   export USE_OLLAMA_ORCHESTRATION=false
   
   # Check logs for errors
   tail -f web_interface.log | grep -i orchestrat
   ```

### Debug Mode

Enable comprehensive debugging:

```python
# In your main application
import logging
logging.basicConfig(level=logging.DEBUG)

# Or specific to orchestration
logging.getLogger('src.workflows').setLevel(logging.DEBUG)
logging.getLogger('src.orchestration').setLevel(logging.DEBUG)
```

## Advanced Configuration

### Custom Workflow Definitions

Create custom workflows in `src/workflows/definitions/`:

```yaml
# custom_debate.yaml
id: "custom_debate"
name: "Custom Debate Process"
description: "Your custom debate workflow"
version: "1.0"

participants:
  - "claude-sonnet-4"
  - "custom-ai-model"

config:
  max_rounds: 3
  consensus_threshold: 0.75

steps:
  - id: "custom_step"
    type: "initial_arguments"
    name: "Custom Step"
    description: "Your custom step"
    required_participants: ["claude-sonnet-4"]
```

### Custom LLM Orchestrator

Extend the orchestration client:

```python
from src.orchestration.llm_orchestrator import LLMOrchestrationClient

class CustomOrchestrationClient(LLMOrchestrationClient):
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        # Your custom LLM integration
        pass
    
    def get_cost_per_token(self) -> float:
        return 0.0001  # Your pricing
    
    def get_model_name(self) -> str:
        return "custom-model"
```

## Production Deployment

### Environment Setup

```bash
# Production environment variables
USE_ORCHESTRATION=true
USE_OLLAMA_ORCHESTRATION=true
ENABLE_COST_OPTIMIZATION=true
ORCHESTRATION_TIMEOUT=120
MAX_WORKFLOW_EXECUTION_TIME=3600
```

### Monitoring

Set up monitoring for:

1. **Orchestration success rate**
2. **Average execution time**
3. **Cost per debate**
4. **Workflow selection accuracy**
5. **Consensus detection rate**

### Performance Considerations

1. **Concurrent Workflows**: System supports multiple concurrent workflows
2. **Resource Management**: Monitor Ollama memory usage for local models
3. **API Rate Limits**: Configure appropriate timeouts for external APIs
4. **Caching Strategy**: Implement appropriate cache TTL for your use case

## Next Steps

1. **Monitor Performance**: Track orchestration metrics in production
2. **Optimize Workflows**: Refine workflow definitions based on usage patterns
3. **Add Custom Models**: Integrate domain-specific LLMs for specialized debates
4. **Enhance Analytics**: Add detailed reporting on orchestration effectiveness
5. **Scale Infrastructure**: Consider distributed orchestration for high-volume usage

## Support

For issues or questions:

1. Check the logs: `tail -f web_interface.log`
2. Test components individually using the test functions provided
3. Review the implementation plan: `docs/orchestration_implementation_plan.md`
4. Enable debug logging for detailed troubleshooting

The orchestration system is designed to be backward-compatible and fail gracefully, so your existing debates will continue to work even if orchestration is disabled or fails.