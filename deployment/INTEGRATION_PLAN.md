# Hardened System Integration Plan

## Overview
The hardened system has been deployed alongside the original system to allow for gradual migration and testing.

## Architecture
- **Original System**: Running on port 8000 (src/web/app.py)
- **Hardened System**: Running on port 8001 (src/web/app_hardened.py)

## New Features in Hardened System
1. **Security Enhancements**
   - Input validation and sanitization
   - Rate limiting (10 requests/minute)
   - CORS configuration
   - Command injection prevention

2. **Error Handling**
   - Global exception handlers
   - Retry logic with exponential backoff
   - Circuit breaker pattern
   - Structured error responses

3. **Data Validation**
   - Pydantic models for all inputs/outputs
   - Strict type checking
   - Field validation with patterns

4. **Monitoring**
   - Health check endpoint
   - Structured logging
   - Request tracking

5. **Atomic Operations**
   - File operations with rollback
   - Backup creation
   - Lock protection

## Migration Steps

### Phase 1: Testing (Current)
1. Run both systems in parallel
2. Compare responses and performance
3. Monitor for errors and edge cases

### Phase 2: Gradual Migration
1. Update frontend to use hardened endpoints
2. Redirect traffic gradually (10% → 50% → 100%)
3. Monitor metrics and error rates

### Phase 3: Full Migration
1. Update all internal references
2. Deprecate original endpoints
3. Remove original system code

## Testing Commands

```bash
# Start original system
./scripts/start_original.sh

# Start hardened system (in new terminal)
./scripts/start_hardened.sh

# Run comparison tests (in new terminal)
./scripts/compare_systems.py
```

## Rollback Plan
If issues arise:
1. Stop hardened system
2. All traffic automatically falls back to original
3. Investigate and fix issues
4. Re-deploy hardened system

## Monitoring
- Check logs: `tail -f logs/hardened_*.log`
- Health check: `curl http://localhost:8001/health`
- Rate limit test: Run multiple requests rapidly

## Next Steps
1. Run comprehensive tests
2. Update CI/CD pipeline
3. Create performance benchmarks
4. Document API changes
