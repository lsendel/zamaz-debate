#!/usr/bin/env python3
"""
Simple script to trigger evolution once
"""
import requests
import json
import sys


def main():
    url = "http://localhost:8000/evolve"

    try:
        print("🚀 Triggering evolution...")
        response = requests.post(url, timeout=60)

        if response.status_code == 200:
            result = response.json()
            print("✅ Evolution completed successfully!")
            print(f"Decision type: {result.get('complexity', 'unknown')}")
            print(f"Method: {result.get('method', 'unknown')}")
            if result.get("pr_created"):
                print(f"PR Branch: {result.get('pr_branch', 'unknown')}")
        else:
            print(f"❌ Evolution failed with status code: {response.status_code}")
            print(response.text)
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running with 'make run'")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 60 seconds")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
