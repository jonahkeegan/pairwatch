#!/usr/bin/env python3
"""
Direct API test to catch the bug in real-time
Test the actual voting pair endpoints that the user is hitting
"""

import requests
import time
import pymongo

def test_voting_pair_api_directly():
    print("🚨 DIRECT API TESTING - Finding the Bug")
    print("=" * 50)
    
    BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # User details
    user_email = "test010@yopmail.com"
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    hbo_boxing_id = "466d1b4f-e1a5-4bfe-8321-4b73abc00a28"
    
    print(f"🎯 Target: Find HBO Boxing in API responses")
    print(f"📧 User: {user_email}")
    print(f"🎬 Content: HBO Boxing ({hbo_boxing_id})")
    print()
    
    # Try to login as the user (attempt multiple password possibilities)
    auth_token = None
    possible_passwords = ["password123", "TestPassword123!", "password", "test123"]
    
    for password in possible_passwords:
        try:
            login_data = {"email": user_email, "password": password}
            login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if login_response.status_code == 200:
                auth_token = login_response.json().get('access_token')
                print(f"✅ Successfully logged in with password: {password}")
                break
            else:
                print(f"❌ Failed login with password: {password} (Status: {login_response.status_code})")
        except Exception as e:
            print(f"❌ Login error with {password}: {e}")
    
    if not auth_token:
        print("❌ Could not authenticate - testing with guest session")
        # Create a guest session
        try:
            session_response = requests.post(f"{BASE_URL}/session")
            if session_response.status_code == 200:
                session_id = session_response.json().get('session_id')
                print(f"✅ Created guest session: {session_id}")
            else:
                print("❌ Could not create guest session either")
                return False
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return False
    
    # Test the main voting pair endpoint
    print(f"\n🔍 Testing main voting pair endpoint...")
    
    headers = {}
    params = {}
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        headers["Content-Type"] = "application/json"
    else:
        params["session_id"] = session_id
    
    hbo_found_count = 0
    total_tests = 20
    
    for i in range(total_tests):
        try:
            response = requests.get(f"{BASE_URL}/voting-pair", headers=headers, params=params)
            
            if response.status_code == 200:
                pair_data = response.json()
                item1_id = pair_data.get("item1", {}).get("id")
                item2_id = pair_data.get("item2", {}).get("id")
                item1_title = pair_data.get("item1", {}).get("title", "Unknown")
                item2_title = pair_data.get("item2", {}).get("title", "Unknown")
                
                if item1_id == hbo_boxing_id or item2_id == hbo_boxing_id:
                    hbo_found_count += 1
                    print(f"🚨 TEST {i+1}: HBO BOXING FOUND!")
                    print(f"   Item 1: {item1_title} ({item1_id})")
                    print(f"   Item 2: {item2_title} ({item2_id})")
                    print(f"   Full response: {pair_data}")
                else:
                    if i < 3:  # Show first few for reference
                        print(f"✅ Test {i+1}: {item1_title} vs {item2_title}")
            else:
                print(f"❌ Test {i+1}: API error {response.status_code}")
                if response.text:
                    print(f"   Error: {response.text}")
            
            # Small delay
            time.sleep(0.2)
            
        except Exception as e:
            print(f"❌ Test {i+1}: Request error - {e}")
    
    # Test the replacement endpoint as well
    print(f"\n🔍 Testing replacement endpoint...")
    
    # Get a random content ID to test replacement with
    random_content = db.content.find_one({"content_type": "series", "id": {"$ne": hbo_boxing_id}})
    
    if random_content and auth_token:
        base_content_id = random_content["id"]
        print(f"   Testing replacement with base: {random_content['title']} ({base_content_id})")
        
        for i in range(5):
            try:
                response = requests.get(f"{BASE_URL}/voting-pair-replacement/{base_content_id}", headers=headers)
                
                if response.status_code == 200:
                    pair_data = response.json()
                    item1_id = pair_data.get("item1", {}).get("id")
                    item2_id = pair_data.get("item2", {}).get("id")
                    item1_title = pair_data.get("item1", {}).get("title", "Unknown")
                    item2_title = pair_data.get("item2", {}).get("title", "Unknown")
                    
                    if item1_id == hbo_boxing_id or item2_id == hbo_boxing_id:
                        hbo_found_count += 1
                        print(f"🚨 REPLACEMENT TEST {i+1}: HBO BOXING FOUND!")
                        print(f"   Item 1: {item1_title} ({item1_id})")
                        print(f"   Item 2: {item2_title} ({item2_id})")
                    else:
                        print(f"✅ Replacement test {i+1}: No HBO Boxing")
                else:
                    print(f"❌ Replacement test {i+1}: API error {response.status_code}")
                
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ Replacement test {i+1}: Request error - {e}")
    
    # Summary
    print(f"\n📊 TEST RESULTS:")
    print(f"   Total API calls: {total_tests + 5}")
    print(f"   HBO Boxing appearances: {hbo_found_count}")
    print(f"   Bug reproduction: {'🚨 SUCCESS' if hbo_found_count > 0 else '❌ Failed'}")
    
    if hbo_found_count > 0:
        print(f"\n🎯 BUG CONFIRMED!")
        print(f"   HBO Boxing appeared {hbo_found_count} times despite being excluded")
        print(f"   This proves there's a real bug in the voting pair generation")
    else:
        print(f"\n🤔 BUG NOT REPRODUCED")
        print(f"   Either the bug was fixed, or it's intermittent")
        print(f"   Possible causes:")
        print(f"   1. Frontend caching old pairs")
        print(f"   2. Different user session/authentication")
        print(f"   3. Timing-dependent race condition")
    
    return hbo_found_count > 0

if __name__ == "__main__":
    success = test_voting_pair_api_directly()
    exit(0 if success else 1)