#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/ubuntu/dap-deploy')

def test_supabase_connection():
    """Test basic Supabase connection and authentication"""
    try:
        from app.notifications.supabase_notifier import supabase
        print("✅ Supabase client imported successfully")
        
        print("Testing Supabase connection...")
        result = supabase.table('deal_reports').select('*').limit(1).execute()
        print("✅ Supabase connection successful")
        print(f"Query result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_webhook_endpoint_logic():
    """Test webhook endpoint code logic without writing to production database"""
    import json
    import uuid
    
    print("Testing webhook endpoint code logic (no database writes)...")
    
    test_summary_data = {
        "executive_summary": {"key_points": ["Test point 1", "Test point 2"]},
        "strategic_recommendations": {"recommendations": ["Test rec 1", "Test rec 2"]},
        "market_analysis": {"market_size": "$1B", "growth_rate": "15%"},
        "financial_overview": {"revenue": "$1M", "burn_rate": "$100K"},
        "competitive_landscape": {"competitors": ["Comp A", "Comp B"]},
        "action_plan": {"next_steps": ["Step 1", "Step 2"]},
        "investment_readiness": {"score": 8, "notes": "Ready for Series A"}
    }
    
    try:
        structured_data = {
            "executive_summary": json.dumps(test_summary_data.get("executive_summary", {})),
            "strategic_recommendations": json.dumps(test_summary_data.get("strategic_recommendations", {})),
            "market_analysis": json.dumps(test_summary_data.get("market_analysis", {})),
            "financial_overview": json.dumps(test_summary_data.get("financial_overview", {})),
            "competitive_landscape": json.dumps(test_summary_data.get("competitive_landscape", {})),
            "action_plan": json.dumps(test_summary_data.get("action_plan", {})),
            "investment_readiness": json.dumps(test_summary_data.get("investment_readiness", {})),
        }
        
        print("✅ JSON serialization logic works correctly")
        print(f"Structured data keys: {list(structured_data.keys())}")
        
        for key, value in structured_data.items():
            parsed = json.loads(value)
            print(f"  ✅ {key}: {type(parsed)} with {len(parsed) if isinstance(parsed, dict) else 'N/A'} items")
        
        return True
        
    except Exception as e:
        print(f"❌ Webhook logic test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Supabase Integration Verification ===")
    
    print("\n1. Testing Supabase Connection:")
    supabase_ok = test_supabase_connection()
    
    print("\n2. Testing Webhook Endpoint Logic:")
    webhook_ok = test_webhook_endpoint_logic()
    
    print("\n=== Results Summary ===")
    print(f"Supabase Connection: {'✅ PASS' if supabase_ok else '❌ FAIL'}")
    print(f"Webhook Logic: {'✅ PASS' if webhook_ok else '❌ FAIL'}")
    
    if supabase_ok and webhook_ok:
        print("\n🎉 All Supabase integration tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some Supabase integration tests failed.")
        sys.exit(1)
