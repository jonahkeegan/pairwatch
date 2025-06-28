#!/usr/bin/env python3
"""
Direct test of the voting-pair-replacement endpoint logic 
to verify exclusion is working correctly
"""

import pymongo
import asyncio
import sys
import os

# Add the backend directory to the path so we can import the server functions
sys.path.append('/app/backend')

async def test_replacement_exclusion():
    print("🔍 Testing Voting Pair Replacement Exclusion Logic")
    print("=" * 50)
    
    # Import the backend functions
    from server import _get_user_vote_stats, db
    
    # Test user details
    user_email = "test009@yopmail.com"
    leonardo_content_id = "1d26e225-a9b5-4ff9-9eb4-c6ba117f240b"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = mongo_client["movie_preferences_db"]
    
    # Get user
    user = local_db.users.find_one({"email": user_email})
    if not user:
        print(f"❌ User {user_email} not found")
        return
    
    user_id = user["id"]
    print(f"✅ Testing with user: {user_id}")
    
    # Get Leonardo content
    leonardo_content = local_db.content.find_one({"id": leonardo_content_id})
    if not leonardo_content:
        print(f"❌ Leonardo content {leonardo_content_id} not found")
        return
    
    print(f"✅ Found Leonardo content: {leonardo_content['title']}")
    print(f"   Content type: {leonardo_content['content_type']}")
    
    # Test the _get_user_vote_stats function
    print(f"\n🔍 Testing _get_user_vote_stats function...")
    vote_count, voted_pairs, excluded_content_ids = await _get_user_vote_stats(user_id, None)
    
    print(f"   Vote count: {vote_count}")
    print(f"   Voted pairs: {len(voted_pairs)}")
    print(f"   Excluded content IDs: {len(excluded_content_ids)}")
    
    # Check if Leonardo content is excluded
    leonardo_excluded = leonardo_content_id in excluded_content_ids
    leonardo_imdb_excluded = leonardo_content.get("imdb_id") in excluded_content_ids if leonardo_content.get("imdb_id") else False
    
    print(f"   Leonardo content ID excluded: {'✅ YES' if leonardo_excluded else '❌ NO'}")
    print(f"   Leonardo IMDB ID excluded: {'✅ YES' if leonardo_imdb_excluded else '❌ NO'}")
    
    if not (leonardo_excluded or leonardo_imdb_excluded):
        print("❌ PROBLEM: Leonardo content should be excluded but isn't!")
        return False
    
    # Test the exclusion filter logic
    print(f"\n🔍 Testing exclusion filter logic...")
    content_type = leonardo_content["content_type"]
    
    # Simulate the replacement endpoint query
    exclusion_filter = {
        "content_type": content_type,
        "id": {"$ne": "some_other_content_id"}  # Simulate keeping another content
    }
    
    # Add exclusion for passed/not_interested/watched content
    if excluded_content_ids:
        exclusion_filter["$and"] = [
            {"id": {"$nin": list(excluded_content_ids)}},
            {"imdb_id": {"$nin": list(excluded_content_ids)}}
        ]
    
    print(f"   Filter: {exclusion_filter}")
    
    # Test the query
    items = list(local_db.content.find(exclusion_filter))
    print(f"   Available items after exclusion: {len(items)}")
    
    # Check if Leonardo content is in the results
    leonardo_in_results = any(item["id"] == leonardo_content_id for item in items)
    print(f"   Leonardo in results: {'❌ YES (BAD)' if leonardo_in_results else '✅ NO (GOOD)'}")
    
    # Show some sample items for debugging
    print(f"   Sample items (first 5):")
    for i, item in enumerate(items[:5]):
        print(f"      {i+1}. {item['title']} ({item['id'][:8]}...)")
    
    if leonardo_in_results:
        print("❌ PROBLEM: Leonardo content found in replacement candidates!")
        return False
    else:
        print("✅ SUCCESS: Leonardo content properly excluded from replacement candidates!")
        return True

async def main():
    try:
        success = await test_replacement_exclusion()
        if success:
            print("\n🎉 Voting pair replacement exclusion is working correctly!")
        else:
            print("\n💥 Voting pair replacement exclusion has issues!")
        return success
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)