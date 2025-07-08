# 💰 Cost Saving Guide for Zamaz Debate System

Since you have Claude Pro but want to minimize API costs, here are several ways to use the system efficiently:

## 🎯 Quick Start - Zero Cost Testing

```bash
# Run in mock mode (no API calls at all)
make run-mock

# Test the system without any costs
make test-decision
```

## 📊 Cost-Saving Modes

### 1. **Mock Mode** (Zero Cost)
```bash
# In .env
USE_MOCK_AI=true

# Or run directly
make run-mock
```
- ✅ No API calls
- ✅ Perfect for testing UI/workflow
- ❌ Generic responses (not intelligent)

### 2. **Cached Mode** (Minimal Cost)
```bash
# In .env
USE_CACHED_RESPONSES=true

# Or run directly  
make run-cached
```
- ✅ First call uses API, subsequent identical calls use cache
- ✅ Great for development and demos
- ✅ Intelligent responses preserved
- 💡 Clear cache with: `make clear-cache`

### 3. **Development Mode** (Smart Caching)
```bash
# Already set in your .env
AI_MODE=development
USE_CACHED_RESPONSES=true
```
- ✅ Best balance of cost and functionality
- ✅ Reuses responses for similar questions

### 4. **Production Mode** (Full API)
```bash
# In .env
AI_MODE=production
USE_CACHED_RESPONSES=false
USE_MOCK_AI=false
```
- ❌ Full API costs
- ✅ Always fresh responses

## 💡 Cost-Saving Tips

### 1. **Use Mock Mode for Development**
When working on UI, integration, or non-AI features:
```bash
make run-mock
```

### 2. **Enable Caching for Repeated Testing**
When testing the same scenarios:
```bash
make run-cached
```

### 3. **Batch Similar Questions**
The cache works on exact matches, so standardize your test questions.

### 4. **Monitor Usage**
```bash
# Check cache statistics
make usage

# See how many responses are cached
ls -la ai_cache/
```

### 5. **Use Simple Decisions**
Simple decisions don't trigger debates, saving API calls:
- Rename operations
- Formatting questions  
- Basic yes/no decisions

## 🤖 Alternative: Use Claude.ai Directly

Since you have Claude Pro, you can:

1. **Manual Debate Mode**:
   - Copy the question to Claude.ai
   - Ask: "Debate this as if you were two AI systems"
   - Paste the result back

2. **Hybrid Approach**:
   - Use mock mode for system
   - Manually run important debates in Claude.ai
   - Save results in `debates/` folder

## 📈 Cost Estimation

| Mode | Cost per Decision | Use Case |
|------|------------------|----------|
| Mock | $0 | Development, UI testing |
| Cached (hit) | $0 | Repeated questions |
| Cached (miss) | ~$0.01-0.03 | First time questions |
| Production | ~$0.01-0.03 | Live system |

## 🔧 Advanced: Custom Mock Responses

Edit `services/ai_client_factory.py` to add specific mock responses:

```python
class MockClaudeClient:
    def create(self, model, messages, max_tokens):
        question = messages[0]["content"]
        
        # Add custom responses
        if "security" in question.lower():
            response = "Security is paramount. Implement OAuth2..."
        # ... add more custom logic
```

## 🚀 Recommended Workflow

1. **Development**: Use mock mode
   ```bash
   make run-mock
   ```

2. **Testing New Features**: Use cached mode
   ```bash
   make run-cached
   ```

3. **Important Decisions**: Use production mode or Claude.ai
   ```bash
   # Either use API
   AI_MODE=production make run
   
   # Or use Claude.ai manually
   ```

4. **Demos**: Use cached mode with pre-warmed cache
   ```bash
   # Pre-run common questions
   make run-cached
   # Run demo questions to populate cache
   # Then demo with instant, free responses
   ```

## 📊 Monitor Your Savings

```bash
# Check current mode
make usage

# Count API calls saved
find ai_cache -name "*.json" | wc -l

# Estimate savings (assuming $0.02 per call)
echo "Saved: $$(( $(find ai_cache -name "*.json" | wc -l) * 2 )) cents"
```

---

Remember: The cache is your friend! Use it liberally during development to save costs while maintaining the full debate experience. 💪