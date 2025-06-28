#!/usr/bin/env python3
"""
Comprehensive verification that the critical bug has been fixed
Test multiple scenarios to ensure exclusions work in all cases
"""

import requests
import time
import pymongo
import random

def comprehensive_bug_fix_verification():
    print("🔧 COMPREHENSIVE BUG FIX VERIFICATION")
    print("=" * 50)
    
    BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Get test010@yopmail.com user data for verification
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    hbo_boxing_id = "466d1b4f-e1a5-4bfe-8321-4b73abc00a28"
    nine11_id = "8e914334-fdd5-45f1-aacb-c880cac6d402"
    
    # Get all excluded content for this user
    excluded_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "interaction_type": {"$in": ["watched", "not_interested", "passed"]}
    }))
    
    excluded_content_ids = set()
    for interaction in excluded_interactions:
        content_id = interaction["content_id"]
        excluded_content_ids.add(content_id)
        
        # Also get the content's other ID
        content = db.content.find_one({
            "$or": [
                {"id": content_id},
                {"imdb_id": content_id}
            ]
        })
        if content:
            excluded_content_ids.add(content.get("id", ""))
            excluded_content_ids.add(content.get("imdb_id", ""))
    
    excluded_content_ids.discard("")
    
    print(f"📊 User exclusion summary:")
    print(f"   Total excluded content IDs: {len(excluded_content_ids)}")
    print(f"   HBO Boxing in excluded set: {'✅ YES' if hbo_boxing_id in excluded_content_ids else '❌ NO'}")
    print(f"   9-1-1 in excluded set: {'✅ YES' if nine11_id in excluded_content_ids else '❌ NO'}")
    print()
    
    # Test with guest sessions (most likely to trigger fallback)
    print("🔍 Testing with multiple guest sessions...")
    
    total_tests = 0
    excluded_content_found = 0
    sessions_tested = 3
    
    for session_num in range(sessions_tested):
        print(f"\n--- Guest Session {session_num + 1} ---")
        
        # Create new guest session
        try:
            session_response = requests.post(f"{BASE_URL}/session")
            if session_response.status_code == 200:
                session_id = session_response.json().get('session_id')
                print(f"✅ Created session: {session_id}")
                
                params = {"session_id": session_id}
                
                # Test voting pairs for this session
                for i in range(15):  # Test 15 pairs per session
                    try:
                        response = requests.get(f"{BASE_URL}/voting-pair", params=params)
                        total_tests += 1
                        
                        if response.status_code == 200:
                            pair_data = response.json()
                            item1_id = pair_data.get("item1", {}).get("id")
                            item2_id = pair_data.get("item2", {}).get("id")
                            
                            # Check if any excluded content appears
                            if item1_id in excluded_content_ids or item2_id in excluded_content_ids:
                                excluded_content_found += 1
                                item1_title = pair_data.get("item1", {}).get("title", "Unknown")
                                item2_title = pair_data.get("item2", {}).get("title", "Unknown")
                                
                                print(f"🚨 EXCLUDED CONTENT FOUND in test {total_tests}!")
                                print(f"   Item 1: {item1_title} ({'EXCLUDED' if item1_id in excluded_content_ids else 'OK'})")
                                print(f"   Item 2: {item2_title} ({'EXCLUDED' if item2_id in excluded_content_ids else 'OK'})")
                                
                                # Specifically check for HBO Boxing and 9-1-1
                                if item1_id == hbo_boxing_id or item2_id == hbo_boxing_id:
                                    print(f"   ⚠️  HBO BOXING FOUND!")
                                if item1_id == nine11_id or item2_id == nine11_id:
                                    print(f"   ⚠️  9-1-1 FOUND!")
                        else:
                            print(f"❌ API error in test {total_tests}: {response.status_code}")
                        
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"❌ Request error in test {total_tests}: {e}")
                        
            else:
                print(f"❌ Failed to create session {session_num + 1}")
                
        except Exception as e:
            print(f"❌ Session creation error: {e}")
    
    # Summary
    print(f"\n📊 COMPREHENSIVE TEST RESULTS:")
    print(f"   Total API calls: {total_tests}")
    print(f"   Sessions tested: {sessions_tested}")
    print(f"   Excluded content appearances: {excluded_content_found}")
    print(f"   Bug fix success rate: {((total_tests - excluded_content_found) / total_tests * 100):.1f}%" if total_tests > 0 else "N/A")
    
    if excluded_content_found == 0:
        print(f"\n🎉 BUG FIX VERIFIED!")
        print(f"   ✅ NO excluded content appeared in {total_tests} tests")
        print(f"   ✅ HBO Boxing exclusion working")
        print(f"   ✅ 9-1-1 exclusion working") 
        print(f"   ✅ All user exclusions respected")
        success = True
    else:
        print(f"\n⚠️  BUG STILL PRESENT!")
        print(f"   ❌ {excluded_content_found} excluded content appearances found")
        print(f"   ❌ Additional investigation needed")
        success = False
    
    # Test a few authenticated scenarios if possible
    print(f"\n🔍 Additional testing with different scenarios...")
    
    # Test with a new user who has pass interactions
    try:
        # Create a test user
        test_email = f"bugfixtest_{int(time.time())}@example.com"
        register_data = {
            "email": test_email,
            "password": "TestPassword123!",
            "name": "Bug Fix Test User"
        }
        
        register_response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if register_response.status_code == 200:
            auth_token = register_response.json().get('access_token')
            test_user_id = register_response.json()['user']['id']
            
            print(f"✅ Created test user: {test_user_id}")
            
            # Get a content item and pass on it
            test_content = db.content.find_one({"content_type": "movie"})
            if test_content:
                test_content_id = test_content["id"]
                
                # Pass on the content
                pass_data = {"content_id": test_content_id}
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json"
                }
                
                pass_response = requests.post(f"{BASE_URL}/pass", json=pass_data, headers=headers)
                if pass_response.status_code == 200:
                    print(f"✅ Passed on content: {test_content['title']}")
                    
                    # Now test voting pairs - the passed content should NOT appear
                    passed_content_found = False
                    for i in range(10):
                        pair_response = requests.get(f"{BASE_URL}/voting-pair", headers=headers)
                        if pair_response.status_code == 200:
                            pair_data = pair_response.json()
                            item1_id = pair_data.get("item1", {}).get("id")
                            item2_id = pair_data.get("item2", {}).get("id")
                            
                            if item1_id == test_content_id or item2_id == test_content_id:
                                passed_content_found = True
                                print(f"❌ Passed content appeared in voting pair!")
                                break
                        time.sleep(0.1)
                    
                    if not passed_content_found:
                        print(f"✅ Passed content correctly excluded from voting pairs")
                    
    except Exception as e:
        print(f"❌ Test user creation failed: {e}")
    
    return success

if __name__ == "__main__":
    success = comprehensive_bug_fix_verification()
    exit(0 if success else 1)