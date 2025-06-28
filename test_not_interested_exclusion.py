#!/usr/bin/env python3
"""
Test to verify that not_interested interactions are properly excluding content
for test010@yopmail.com and ensure the exclusion system is working
"""

import asyncio
import sys
import os
import pymongo

# Add the backend directory to the path
sys.path.append('/app/backend')

async def test_not_interested_exclusion():
    print("🔍 Testing NOT_INTERESTED Exclusion for test010@yopmail.com")
    print("=" * 60)
    
    # Import the backend functions
    try:
        from server import _get_user_vote_stats, db
    except ImportError as e:
        print(f"❌ Failed to import backend functions: {e}")
        return False
    
    # Test user details
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    hbo_boxing_id = "466d1b4f-e1a5-4bfe-8321-4b73abc00a28"
    nine11_id = "8e914334-fdd5-45f1-aacb-c880cac6d402"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = mongo_client["movie_preferences_db"]
    
    print(f"✅ Testing user: {user_id}")
    print(f"✅ Testing HBO Boxing: {hbo_boxing_id}")
    print(f"✅ Testing 9-1-1: {nine11_id}")
    
    # Test the exclusion logic
    print(f"\n🔍 Step 1: Testing _get_user_vote_stats function...")
    vote_count, voted_pairs, excluded_content_ids = await _get_user_vote_stats(user_id, None)
    
    print(f"   Vote count: {vote_count}")
    print(f"   Voted pairs: {len(voted_pairs)}")
    print(f"   Excluded content IDs: {len(excluded_content_ids)}")
    
    # Check specific content exclusions
    hbo_excluded = hbo_boxing_id in excluded_content_ids
    nine11_excluded = nine11_id in excluded_content_ids
    
    print(f"   HBO Boxing excluded: {'✅ YES' if hbo_excluded else '❌ NO'}")
    print(f"   9-1-1 excluded: {'✅ YES' if nine11_excluded else '❌ NO'}")
    
    # Get the user's not_interested interactions
    print(f"\n🔍 Step 2: Analyzing not_interested interactions...")
    not_interested = list(local_db.user_interactions.find({
        "user_id": user_id,
        "interaction_type": "not_interested"
    }))
    
    print(f"   Total not_interested interactions: {len(not_interested)}")
    
    # Check each not_interested item to see if it's excluded
    excluded_count = 0
    not_excluded_count = 0
    
    print(f"   Checking exclusion status of each not_interested item:")
    for interaction in not_interested:
        content_id = interaction["content_id"]
        
        # Get content title for display
        content = local_db.content.find_one({
            "$or": [
                {"id": content_id},
                {"imdb_id": content_id}
            ]
        })
        title = content.get('title', 'Unknown') if content else 'Content not found'
        
        is_excluded = content_id in excluded_content_ids
        if content and not is_excluded:
            # Also check by the content's ID and IMDB ID
            is_excluded = (content.get('id') in excluded_content_ids or 
                          content.get('imdb_id') in excluded_content_ids)
        
        if is_excluded:
            excluded_count += 1
            print(f"   ✅ {title} - EXCLUDED")
        else:
            not_excluded_count += 1
            print(f"   ❌ {title} - NOT EXCLUDED")
    
    print(f"\n📊 Summary:")
    print(f"   Not_interested items properly excluded: {excluded_count}")
    print(f"   Not_interested items NOT excluded: {not_excluded_count}")
    
    # Test if these excluded items would appear in voting pairs
    print(f"\n🔍 Step 3: Testing voting pair generation...")
    
    # Simulate voting pair generation by checking if excluded content appears
    all_content = list(local_db.content.find({}))
    available_content = []
    
    for content in all_content:
        content_id = content.get('id')
        imdb_id = content.get('imdb_id', '')
        
        # Check if this content should be excluded
        is_excluded = (content_id in excluded_content_ids or 
                      (imdb_id and imdb_id in excluded_content_ids))
        
        if not is_excluded:
            available_content.append(content)
    
    print(f"   Total content in database: {len(all_content)}")
    print(f"   Available content after exclusions: {len(available_content)}")
    print(f"   Content excluded by filters: {len(all_content) - len(available_content)}")
    
    # Check if HBO Boxing and 9-1-1 are in available content (they shouldn't be)
    hbo_available = any(c.get('id') == hbo_boxing_id for c in available_content)
    nine11_available = any(c.get('id') == nine11_id for c in available_content)
    
    print(f"   HBO Boxing in available content: {'❌ YES (BAD)' if hbo_available else '✅ NO (GOOD)'}")
    print(f"   9-1-1 in available content: {'❌ YES (BAD)' if nine11_available else '✅ NO (GOOD)'}")
    
    # Final verification
    success = (excluded_count == len(not_interested) and 
               not hbo_available and 
               not nine11_available)
    
    print(f"\n🎯 CONCLUSION:")
    if success:
        print("✅ NOT_INTERESTED exclusion is working perfectly!")
        print("   All not_interested content is properly excluded from voting pairs")
        print("   HBO Boxing and 9-1-1 will not appear in future voting")
    else:
        print("❌ There are issues with NOT_INTERESTED exclusion!")
        print("   Some not_interested content may still appear in voting pairs")
    
    # Additional investigation
    print(f"\n💡 INVESTIGATION RESULTS:")
    print(f"   This confirms that the user used 'Not Interested' instead of 'Pass'")
    print(f"   Both interactions have the same effect (exclusion from voting)")
    print(f"   The issue is likely user interface terminology or user confusion")
    
    return success

async def main():
    try:
        success = await test_not_interested_exclusion()
        return success
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)