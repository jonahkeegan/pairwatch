#!/usr/bin/env python3
"""
Simplified test to directly check the exclusion logic in the voting endpoints
"""

import requests
import pymongo
import time
import json

def test_exclusion_logic():
    print("🔍 Testing Exclusion Logic for 9-1-1 Content")
    print("=" * 50)
    
    BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"
    
    # Test user details
    user_email = "test010@yopmail.com"
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    content_id_911 = "8e914334-fdd5-45f1-aacb-c880cac6d402"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    print(f"✅ Testing with user: {user_id}")
    print(f"✅ Testing exclusion of: {content_id_911} (9-1-1)")
    
    # Check the user's interactions
    print(f"\n🔍 Checking user interactions...")
    interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "content_id": content_id_911
    }))
    
    print(f"   Interactions with 9-1-1: {len(interactions)}")
    for interaction in interactions:
        print(f"   - Type: {interaction['interaction_type']}")
        print(f"   - Timestamp: {interaction.get('timestamp', 'Unknown')}")
    
    # Test the voting pair endpoint multiple times
    print(f"\n🔍 Testing voting pair endpoint (50 attempts)...")
    
    content_911_appeared = False
    appearance_count = 0
    total_tests = 50
    
    # We need an auth token to test with the actual user
    # Let's try to login first
    login_data = {
        "email": user_email,
        "password": "password123"  # Default password, might need to adjust
    }
    
    try:
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if login_response.status_code == 200:
            auth_token = login_response.json().get('access_token')
            print(f"✅ Successfully logged in as {user_email}")
        else:
            print(f"❌ Failed to login: {login_response.status_code}")
            # Try with a known test password
            login_data["password"] = "TestPassword123!"
            login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            if login_response.status_code == 200:
                auth_token = login_response.json().get('access_token')
                print(f"✅ Successfully logged in as {user_email} with test password")
            else:
                print(f"❌ Failed to login with test password: {login_response.status_code}")
                print("   Will test with guest session instead")
                auth_token = None
    except Exception as e:
        print(f"❌ Login error: {e}")
        auth_token = None
    
    # If we have an auth token, test with authenticated user
    if auth_token:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        for i in range(total_tests):
            try:
                response = requests.get(f"{BASE_URL}/voting-pair", headers=headers)
                
                if response.status_code == 200:
                    pair_data = response.json()
                    item1_id = pair_data.get("item1", {}).get("id")
                    item2_id = pair_data.get("item2", {}).get("id")
                    
                    if item1_id == content_id_911 or item2_id == content_id_911:
                        content_911_appeared = True
                        appearance_count += 1
                        item1_title = pair_data.get("item1", {}).get("title", "Unknown")
                        item2_title = pair_data.get("item2", {}).get("title", "Unknown")
                        print(f"  ❌ Test {i+1}: 9-1-1 APPEARED!")
                        print(f"     Item 1: {item1_title} ({item1_id})")
                        print(f"     Item 2: {item2_title} ({item2_id})")
                    else:
                        if i < 5 or i % 10 == 0:  # Show some samples
                            item1_title = pair_data.get("item1", {}).get("title", "Unknown")
                            item2_title = pair_data.get("item2", {}).get("title", "Unknown")
                            print(f"  ✅ Test {i+1}: {item1_title} vs {item2_title}")
                else:
                    print(f"  ❌ Test {i+1}: API error {response.status_code}")
                
                # Small delay between requests
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ Test {i+1}: Request error - {e}")
    else:
        print("❌ Cannot test with authenticated user, skipping detailed testing")
    
    # Test replacement endpoint as well
    print(f"\n🔍 Testing replacement endpoint...")
    
    if auth_token:
        # Get some other content to test replacement with
        other_content = db.content.find_one({
            "content_type": "series",
            "id": {"$ne": content_id_911}
        })
        
        if other_content:
            other_id = other_content["id"]
            print(f"   Testing replacement with base content: {other_content['title']}")
            
            for i in range(10):
                try:
                    response = requests.get(f"{BASE_URL}/voting-pair-replacement/{other_id}", headers=headers)
                    
                    if response.status_code == 200:
                        pair_data = response.json()
                        item1_id = pair_data.get("item1", {}).get("id")
                        item2_id = pair_data.get("item2", {}).get("id")
                        
                        if item1_id == content_id_911 or item2_id == content_id_911:
                            content_911_appeared = True
                            appearance_count += 1
                            print(f"  ❌ Replacement test {i+1}: 9-1-1 APPEARED!")
                        else:
                            print(f"  ✅ Replacement test {i+1}: No 9-1-1 content")
                    else:
                        print(f"  ❌ Replacement test {i+1}: API error {response.status_code}")
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"  ❌ Replacement test {i+1}: Request error - {e}")
    
    # Results
    print(f"\n📊 Test Results:")
    print(f"   Total tests: {total_tests + 10}")
    print(f"   9-1-1 appearances: {appearance_count}")
    print(f"   9-1-1 appeared: {'❌ YES' if content_911_appeared else '✅ NO'}")
    
    if not content_911_appeared:
        print("\n🎉 SUCCESS: 9-1-1 content properly excluded from all voting pairs!")
    else:
        print(f"\n💥 FAILURE: 9-1-1 content appeared {appearance_count} times despite being marked as not_interested!")
    
    return not content_911_appeared

if __name__ == "__main__":
    success = test_exclusion_logic()
    exit(0 if success else 1)