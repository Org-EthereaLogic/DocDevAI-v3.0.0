#!/usr/bin/env python3
"""
Test script to verify LLM API integration is working after fixes
"""

import json
import time

import requests

API_BASE = "http://localhost:8002"


def test_document_generation():
    """Test document generation endpoint"""
    print("=" * 60)
    print("Testing Document Generation with Real LLM...")
    print("=" * 60)

    payload = {
        "template": "readme",
        "context": {
            "title": "Test Project",
            "description": "Testing LLM integration after fixing the bug",
            "features": ["Feature 1", "Feature 2", "Feature 3"],
        },
        "output_format": "markdown",
    }

    try:
        response = requests.post(
            f"{API_BASE}/api/documents/generate",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            metadata = data.get("metadata", {})

            print(f"\nMetadata: {json.dumps(metadata, indent=2)}")
            print(f"\nGenerated Content Length: {len(content)} characters")
            print("\nFirst 500 characters of content:")
            print("-" * 40)
            print(content[:500])
            print("-" * 40)

            # Check if it's demo mode or real
            if "demo_mode" in metadata and metadata["demo_mode"]:
                print("\n⚠️  WARNING: Still in DEMO MODE - LLM not working!")
                return False
            else:
                print("\n✅ SUCCESS: Real LLM content generated!")
                return True
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Request failed: {e}")
        return False


def test_document_enhancement():
    """Test document enhancement endpoint"""
    print("\n" + "=" * 60)
    print("Testing Document Enhancement with MIAIR + LLM...")
    print("=" * 60)

    payload = {
        "content": "This is a test document. It needs improvement.",
        "strategy": "MIAIR_ENHANCED",
        "target_quality": 0.85,
    }

    try:
        response = requests.post(
            f"{API_BASE}/api/documents/enhance",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            enhanced = data.get("enhanced_content", "")
            improvements = data.get("improvements", [])

            print(f"\nEnhanced Content: {enhanced[:200]}...")
            print(f"Improvements: {improvements}")

            # Check if it's demo mode
            if "Demo Mode" in enhanced:
                print("\n⚠️  WARNING: Still in DEMO MODE - Enhancement not working!")
                return False
            else:
                print("\n✅ SUCCESS: Real enhancement performed!")
                return True
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Request failed: {e}")
        return False


def test_document_analysis():
    """Test document analysis endpoint"""
    print("\n" + "=" * 60)
    print("Testing Document Analysis with MIAIR...")
    print("=" * 60)

    payload = {
        "content": "# Test Document\n\nThis is a test document for analysis.",
        "include_suggestions": True,
    }

    try:
        response = requests.post(
            f"{API_BASE}/api/documents/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\nAnalysis Results: {json.dumps(data, indent=2)}")
            print("\n✅ SUCCESS: Analysis completed!")
            return True
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Request failed: {e}")
        return False


if __name__ == "__main__":
    print("\n🔧 DevDocAI API Fix Verification Test\n")

    # Run tests
    gen_success = test_document_generation()
    time.sleep(1)  # Small delay between tests

    enhance_success = test_document_enhancement()
    time.sleep(1)

    analyze_success = test_document_analysis()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Document Generation: {'✅ PASSED' if gen_success else '❌ FAILED'}")
    print(f"Document Enhancement: {'✅ PASSED' if enhance_success else '❌ FAILED'}")
    print(f"Document Analysis: {'✅ PASSED' if analyze_success else '❌ FAILED'}")

    if gen_success and enhance_success and analyze_success:
        print("\n🎉 ALL TESTS PASSED! LLM Integration is working!")
    else:
        print("\n⚠️  Some tests failed. Check server logs for details.")
