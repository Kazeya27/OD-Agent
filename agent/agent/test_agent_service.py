#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script for Agent Service."""

import requests
import json
import time

BASE_URL = "http://localhost:8503"


def test_health_check():
    """Test health check endpoint."""
    print("✅ Testing health check...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["ok"] == True
    print("✓ Health check passed\n")


def test_chat(session_id: str, question: str):
    """Test chat endpoint."""
    print(f"✅ Testing chat with question: {question}")
    response = requests.post(
        f"{BASE_URL}/chat", json={"session_id": session_id, "question": question}
    )
    result = response.json()
    print(f"Session ID: {result['session_id']}")
    print(f"Answer: {result['answer']}")
    print(f"Timestamp: {result['timestamp']}")
    print("✓ Chat test passed\n")
    return result


def test_history(session_id: str):
    """Test history endpoint."""
    print(f"✅ Testing history retrieval for session: {session_id}")
    response = requests.post(f"{BASE_URL}/history", json={"session_id": session_id})
    result = response.json()
    print(f"Session ID: {result['session_id']}")
    print(f"Total messages: {len(result['messages'])}")

    for i, msg in enumerate(result["messages"], 1):
        print(f"\n  Message {i}:")
        print(f"    Time: {msg['time']}")
        print(f"    From: {msg['from']}")
        content = msg["content"]
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"    Content: {content}")

    print("\n✓ History test passed\n")
    return result


def main():
    print("=" * 60)
    print("Agent Service Test Suite")
    print("=" * 60 + "\n")

    try:
        # Test 1: Health check
        test_health_check()

        # Test 2: Chat with simple question
        session_id = f"test-session-{int(time.time())}"
        test_chat(session_id, "你好，请介绍一下你自己")

        # Test 3: Chat with a real query
        test_chat(session_id, "北京的geo_id是多少？")

        # Test 4: Get history
        test_history(session_id)

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to the server.")
        print("   Please make sure the agent service is running on port 8503.")
        print("   Run: python agent_service.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
