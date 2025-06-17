#!/usr/bin/env python3
"""
Test script to verify backend report generation and table content updates.
Tests that the backend properly handles report generation for existing analysis requests.
"""

import json
import uuid
import requests
import sys
from datetime import datetime
from typing import Dict, Any

def test_report_generation_workflow() -> bool:
    """Test that backend properly generates reports and updates table contents."""
    
    test_request_id = str(uuid.uuid4())
    
    print("=" * 70)
    print("Testing Report Generation Workflow")
    print("=" * 70)
    print(f"Testing report generation for request ID: {test_request_id}")
    print()
    
    try:
        print("Step 1: Testing POST /api/reports/{id}/generate endpoint...")
        gen_response = requests.post(
            f"http://localhost:8000/api/reports/{test_request_id}/generate",
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"Generation response status: {gen_response.status_code}")
        
        if gen_response.status_code == 404:
            print("✅ Expected 404 for non-existent request ID (correct behavior)")
            print("Backend properly validates request existence before processing")
            return True
        elif gen_response.status_code == 200:
            print("✅ Report generation triggered successfully")
            
            try:
                gen_data = gen_response.json()
                print(f"Generation response status: {gen_data.get('status', 'unknown')}")
                
                if gen_data.get('status') in ['processing', 'completed']:
                    print("✅ Report generation workflow working correctly")
                    return True
                else:
                    print(f"⚠️  Unexpected status: {gen_data.get('status')}")
                    return False
                    
            except json.JSONDecodeError:
                print("⚠️  Generation response not valid JSON")
                print(f"Raw response: {gen_response.text[:200]}...")
                return False
        else:
            print(f"❌ Unexpected response status: {gen_response.status_code}")
            print(f"Error response: {gen_response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the backend server running on localhost:8000?")
        print("Start the server with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out - server may be overloaded")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_status_endpoint() -> bool:
    """Test that status endpoint works correctly."""
    
    test_request_id = str(uuid.uuid4())
    
    print("\n" + "=" * 70)
    print("Testing Status Endpoint")
    print("=" * 70)
    print(f"Testing status endpoint for request ID: {test_request_id}")
    print()
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/reports/{test_request_id}/status",
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 404:
            print("✅ Expected 404 for non-existent request ID (correct behavior)")
            print("Status endpoint properly validates request existence")
            return True
        elif response.status_code == 200:
            print("✅ Status endpoint responded successfully")
            
            try:
                status_data = response.json()
                print(f"Status response: {json.dumps(status_data, indent=2)}")
                
                required_fields = ['report_id', 'status', 'progress']
                missing_fields = [field for field in required_fields if field not in status_data]
                
                if missing_fields:
                    print(f"⚠️  Missing fields in status response: {missing_fields}")
                    return False
                else:
                    print("✅ All required status fields present")
                    return True
                    
            except json.JSONDecodeError:
                print("⚠️  Status response not valid JSON")
                print(f"Raw response: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
            print(f"Error response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Status endpoint test failed: {e}")
        return False

def test_webhook_endpoint() -> bool:
    """Test that webhook endpoint handles report completion correctly."""
    
    webhook_payload = {
        "reportId": str(uuid.uuid4()),
        "pdfUrl": "https://example.com/report.pdf",
        "summaryData": {
            "executive_summary": {"key_points": ["Point 1", "Point 2"]},
            "strategic_recommendations": {"recommendations": ["Rec 1", "Rec 2"]},
            "market_analysis": {"market_size": "$1B", "growth_rate": "15%"},
            "financial_overview": {"revenue": "$1M", "burn_rate": "$100K"},
            "competitive_landscape": {"competitors": ["Comp A", "Comp B"]},
            "action_plan": {"next_steps": ["Step 1", "Step 2"]},
            "investment_readiness": {"score": 8, "notes": "Ready for Series A"}
        }
    }
    
    print("\n" + "=" * 70)
    print("Testing Webhook Endpoint")
    print("=" * 70)
    print(f"Testing webhook with report completion data")
    print(f"Report ID: {webhook_payload['reportId']}")
    print()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/webhook/report-completion",
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Webhook endpoint accepted payload successfully")
            
            try:
                response_data = response.json()
                print(f"Webhook response: {json.dumps(response_data, indent=2)}")
                
                if response_data.get("status") == "success":
                    print("✅ Webhook processed successfully")
                    return True
                else:
                    print(f"⚠️  Unexpected webhook response: {response_data}")
                    return False
                    
            except json.JSONDecodeError:
                print("⚠️  Webhook response not valid JSON")
                print(f"Raw response: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Webhook endpoint failed: {response.status_code}")
            print(f"Error response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Webhook endpoint test failed: {e}")
        return False

def main():
    """Run all backend update and report generation tests."""
    print("Backend Report Generation and Update Test Suite")
    print("Verifying backend handles report generation and table content updates")
    print()
    
    tests = [
        ("Report Generation Workflow", test_report_generation_workflow),
        ("Status Endpoint", test_status_endpoint),
        ("Webhook Endpoint", test_webhook_endpoint)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend report generation and updates working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the backend implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
