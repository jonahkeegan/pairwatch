#!/usr/bin/env python3
"""
Comprehensive test to verify that pass functionality is working correctly
and to check if there are systematic issues with pass vs not_interested
"""

import pymongo
import requests
import time
import random
import string
from datetime import datetime

def test_pass_functionality_comprehensive():
    print("🔍 Comprehensive Pass Functionality Test")
    print("=" * 50)
    
    BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Check existing pass interactions across ALL users
    print("1. Checking pass interactions across ALL users...")
    all_pass_interactions = list(db.user_interactions.find({"interaction_type": "passed"}))
    print(f"📊 Total pass interactions in database: {len(all_pass_interactions)}")
    
    if all_pass_interactions:
        print("   Recent pass interactions:")
        for interaction in all_pass_interactions[-5:]:  # Show last 5
            user_id = interaction.get('user_id', 'Unknown')
            content_id = interaction.get('content_id', 'Unknown')
            timestamp = interaction.get('timestamp', 'Unknown')
            print(f"   - User: {user_id[:8]}... Content: {content_id[:8]}... Time: {timestamp}")
    else:
        print("❌ NO pass interactions found in entire database!")
    
    # Check all users and their interaction types
    print("\n2. Analyzing interaction types across all users...")
    interaction_stats = {}
    all_interactions = list(db.user_interactions.find({}))
    
    for interaction in all_interactions:
        interaction_type = interaction['interaction_type']
        if interaction_type not in interaction_stats:
            interaction_stats[interaction_type] = 0
        interaction_stats[interaction_type] += 1
    
    print("📊 Global interaction statistics:")
    for interaction_type, count in interaction_stats.items():
        print(f"   - {interaction_type}: {count}")
    
    # Check specifically test010@yopmail.com user
    print("\n3. Detailed analysis of test010@yopmail.com...")
    test_user = db.users.find_one({"email": "test010@yopmail.com"})
    if test_user:
        user_id = test_user["id"]
        print(f"✅ Found user: {user_id}")
        
        # Get all interactions for this user
        user_interactions = list(db.user_interactions.find({"user_id": user_id}))
        user_interaction_stats = {}
        
        for interaction in user_interactions:
            interaction_type = interaction['interaction_type']
            if interaction_type not in user_interaction_stats:
                user_interaction_stats[interaction_type] = 0
            user_interaction_stats[interaction_type] += 1
        
        print(f"📊 test010@yopmail.com interaction statistics:")
        for interaction_type, count in user_interaction_stats.items():
            print(f"   - {interaction_type}: {count}")
        
        # Check if there are any recent interactions that could be misclassified
        recent_interactions = list(db.user_interactions.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(10))
        
        print(f"\n📋 Recent interactions for test010@yopmail.com:")
        for interaction in recent_interactions:
            content_id = interaction['content_id']
            # Try to get content title
            content = db.content.find_one({
                "$or": [
                    {"id": content_id},
                    {"imdb_id": content_id}
                ]
            })
            content_title = content.get('title', 'Unknown') if content else 'Content not found'
            
            print(f"   - {interaction['interaction_type']}: {content_title}")
            print(f"     Content ID: {content_id}")
            print(f"     Timestamp: {interaction.get('timestamp', 'Unknown')}")
    
    # Test the pass endpoint directly
    print("\n4. Testing pass endpoint directly...")
    
    # Try to create a test user and test pass functionality
    test_email = f"passtest_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    # Register test user
    register_data = {
        "email": test_email,
        "password": test_password,
        "name": "Pass Test User"
    }
    
    try:
        register_response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if register_response.status_code == 200:
            auth_token = register_response.json().get('access_token')
            test_user_id = register_response.json()['user']['id']
            print(f"✅ Created test user: {test_user_id}")
            
            # Get a content item to test with
            test_content = db.content.find_one({"content_type": "movie"})
            if test_content:
                test_content_id = test_content["id"]
                print(f"✅ Using test content: {test_content['title']} ({test_content_id})")
                
                # Test the pass endpoint
                pass_data = {"content_id": test_content_id}
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json"
                }
                
                pass_response = requests.post(f"{BASE_URL}/pass", json=pass_data, headers=headers)
                print(f"📡 Pass endpoint response: {pass_response.status_code}")
                
                if pass_response.status_code == 200:
                    response_data = pass_response.json()
                    print(f"✅ Pass endpoint working: {response_data}")
                    
                    # Verify the interaction was recorded
                    time.sleep(1)  # Give it a moment to save
                    recorded_interaction = db.user_interactions.find_one({
                        "user_id": test_user_id,
                        "content_id": test_content_id,
                        "interaction_type": "passed"
                    })
                    
                    if recorded_interaction:
                        print("✅ Pass interaction successfully recorded in database")
                    else:
                        print("❌ Pass interaction NOT found in database - BUG!")
                else:
                    print(f"❌ Pass endpoint failed: {pass_response.text}")
            else:
                print("❌ No test content found")
        else:
            print(f"❌ Failed to register test user: {register_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing pass endpoint: {e}")
    
    # 5. Check if there are any system-wide issues
    print("\n5. System-wide analysis...")
    
    # Check how many users have any pass interactions
    users_with_pass = db.user_interactions.distinct("user_id", {"interaction_type": "passed"})
    total_users = db.users.count_documents({})
    
    print(f"📊 Users with pass interactions: {len(users_with_pass)} out of {total_users} total users")
    
    if len(users_with_pass) == 0:
        print("⚠️  NO users have any pass interactions - this might indicate:")
        print("   1. Pass functionality is broken")
        print("   2. Frontend is not calling pass endpoint")
        print("   3. Users are using not_interested instead")
        print("   4. Pass feature is not being used")
    
    # Check recent API endpoint usage
    print("\n6. Summary and recommendations...")
    print("=" * 40)
    
    if len(all_pass_interactions) == 0:
        print("🚨 CRITICAL FINDING: No pass interactions found system-wide!")
        print("📋 Possible issues:")
        print("   1. Pass endpoint not being called by frontend")
        print("   2. Pass button mapping to wrong API call")
        print("   3. Users confused about which button to use")
        print("   4. Pass functionality completely broken")
        print("\n💡 Recommendations:")
        print("   1. Check frontend implementation of Pass button")
        print("   2. Verify API endpoint mapping")
        print("   3. Test pass functionality end-to-end")
        print("   4. Review user interface clarity")
    else:
        print(f"✅ Found {len(all_pass_interactions)} pass interactions system-wide")
        print("   The functionality appears to be working for some users")
    
    return len(all_pass_interactions) > 0

if __name__ == "__main__":
    success = test_pass_functionality_comprehensive()
    exit(0 if success else 1)