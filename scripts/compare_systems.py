#!/usr/bin/env python3
'''Compare original and hardened systems'''
import requests
import json
from datetime import datetime

def test_endpoint(url, endpoint, data=None):
    '''Test an endpoint and return results'''
    try:
        if data:
            response = requests.post(f"{url}{endpoint}", json=data, timeout=10)
        else:
            response = requests.get(f"{url}{endpoint}", timeout=10)
        
        return {
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "data": response.json() if response.ok else response.text
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def main():
    original_url = "http://localhost:8000"
    hardened_url = "http://localhost:8001"
    
    print("🔍 Comparing Original vs Hardened Systems")
    print("=" * 50)
    
    # Test health endpoints
    print("\n📋 Health Check:")
    original_health = test_endpoint(original_url, "/health")
    hardened_health = test_endpoint(hardened_url, "/health")
    
    print(f"Original: {original_health.get('status_code', 'Failed')}")
    print(f"Hardened: {hardened_health.get('status_code', 'Failed')} - {hardened_health.get('data', {}).get('status', 'Unknown')}")
    
    # Test stats
    print("\n📊 Stats:")
    original_stats = test_endpoint(original_url, "/stats")
    hardened_stats = test_endpoint(hardened_url, "/stats")
    
    print(f"Original: {original_stats.get('data', {})}")
    print(f"Hardened: {hardened_stats.get('data', {})}")
    
    # Test decision endpoint
    print("\n🤔 Decision Test:")
    test_decision = {
        "question": "Should we implement automated testing for all new features?",
        "context": "We want to improve code quality"
    }
    
    original_decision = test_endpoint(original_url, "/decide", test_decision)
    hardened_decision = test_endpoint(hardened_url, "/decide", test_decision)
    
    print(f"Original response time: {original_decision.get('response_time', 'N/A')}s")
    print(f"Hardened response time: {hardened_decision.get('response_time', 'N/A')}s")
    
    # Test rate limiting (hardened only)
    print("\n🚦 Rate Limiting Test (Hardened):")
    for i in range(12):
        result = test_endpoint(hardened_url, "/stats")
        if result.get('status_code') == 429:
            print(f"  Rate limit hit after {i} requests ✓")
            break
    else:
        print("  Rate limit not triggered (may need adjustment)")
    
    print("\n✅ Comparison complete!")

if __name__ == "__main__":
    main()
