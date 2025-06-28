#!/usr/bin/env python3
"""
Test to verify the main voting-pair endpoint properly excludes not_interested content
for test010@yopmail.com and 9-1-1 content
"""

import asyncio
import sys
import os
import pymongo

# Add the backend directory to the path so we can import the server functions
sys.path.append('/app/backend')

async def test_voting_pair_exclusion():
    print("🔍 Testing Main Voting Pair Exclusion Logic")
    print("=" * 50)
    
    # Import the backend functions
    try:
        from server import _get_user_vote_stats, _get_all_content_items_as_df, _get_candidate_items_for_pairing, db
    except ImportError as e:
        print(f"❌ Failed to import backend functions: {e}")
        return False
    
    # Test user details
    user_email = "test010@yopmail.com"
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    content_id_911 = "8e914334-fdd5-45f1-aacb-c880cac6d402"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = mongo_client["movie_preferences_db"]
    
    print(f"✅ Testing with user: {user_id}")
    print(f"✅ Testing exclusion of: {content_id_911} (9-1-1)")
    
    # Test the _get_user_vote_stats function
    print(f"\n🔍 Step 1: Testing _get_user_vote_stats function...")
    vote_count, voted_pairs, excluded_content_ids = await _get_user_vote_stats(user_id, None)
    
    print(f"   Vote count: {vote_count}")
    print(f"   Voted pairs: {len(voted_pairs)}")
    print(f"   Excluded content IDs: {len(excluded_content_ids)}")
    
    # Check if 9-1-1 content is excluded
    content_911_excluded = content_id_911 in excluded_content_ids
    
    print(f"   9-1-1 content ID excluded: {'✅ YES' if content_911_excluded else '❌ NO'}")
    
    if not content_911_excluded:
        print("❌ PROBLEM: 9-1-1 content should be excluded but isn't!")
        return False
    
    # Test the content DataFrame generation
    print(f"\n🔍 Step 2: Testing _get_all_content_items_as_df function...")
    all_content_df = await _get_all_content_items_as_df(db)
    
    if all_content_df is None or all_content_df.empty:
        print("❌ PROBLEM: Content DataFrame is empty!")
        return False
    
    print(f"   Total content items in DataFrame: {len(all_content_df)}")
    
    # Check if 9-1-1 is in the DataFrame
    content_911_in_df = content_id_911 in all_content_df['content_id'].values
    print(f"   9-1-1 content in DataFrame: {'✅ YES' if content_911_in_df else '❌ NO'}")
    
    if not content_911_in_df:
        print("❌ PROBLEM: 9-1-1 content not found in content DataFrame!")
        return False
    
    # Test the candidate selection for cold-start strategy
    print(f"\n🔍 Step 3: Testing _get_candidate_items_for_pairing (cold-start)...")
    user_profile = {}  # Empty profile for cold-start
    strategy = "cold_start"
    
    candidate_items = await _get_candidate_items_for_pairing(
        user_profile, all_content_df, strategy, vote_count, excluded_content_ids, db
    )
    
    print(f"   Candidate items returned: {len(candidate_items)}")
    
    # Check if 9-1-1 is in the candidates
    content_911_in_candidates = any(item.get('content_id') == content_id_911 for item in candidate_items)
    print(f"   9-1-1 content in candidates: {'❌ YES (BAD)' if content_911_in_candidates else '✅ NO (GOOD)'}")
    
    if content_911_in_candidates:
        print("❌ PROBLEM: 9-1-1 content found in candidate items despite being excluded!")
        return False
    
    # Test the candidate selection for personalized strategy (if user has enough votes)
    if vote_count >= 10:
        print(f"\n🔍 Step 4: Testing _get_candidate_items_for_pairing (personalized)...")
        strategy = "personalized"
        
        # Build a basic user profile
        user_votes = await db.votes.find({"user_id": user_id}).to_list(length=None)
        if user_votes:
            # Simple profile building
            user_profile = {
                "preferred_genres": ["Action", "Drama"],
                "preferred_content_type": "series",
                "total_votes": vote_count
            }
        
        candidate_items_personalized = await _get_candidate_items_for_pairing(
            user_profile, all_content_df, strategy, vote_count, excluded_content_ids, db
        )
        
        print(f"   Personalized candidate items returned: {len(candidate_items_personalized)}")
        
        # Check if 9-1-1 is in the personalized candidates
        content_911_in_personalized = any(item.get('content_id') == content_id_911 for item in candidate_items_personalized)
        print(f"   9-1-1 content in personalized candidates: {'❌ YES (BAD)' if content_911_in_personalized else '✅ NO (GOOD)'}")
        
        if content_911_in_personalized:
            print("❌ PROBLEM: 9-1-1 content found in personalized candidates despite being excluded!")
            return False
    
    # Test a simulated voting pair generation
    print(f"\n🔍 Step 5: Testing simulated voting pair generation...")
    
    # Try to generate multiple pairs and check if 9-1-1 appears
    for i in range(10):
        if len(candidate_items) >= 2:
            # Simulate pair selection
            import random
            pair = random.sample(candidate_items, 2)
            
            item1_id = pair[0].get('content_id')
            item2_id = pair[1].get('content_id')
            
            if item1_id == content_id_911 or item2_id == content_id_911:
                print(f"❌ PROBLEM: 9-1-1 content appeared in simulated pair {i+1}!")
                return False
    
    print("✅ SUCCESS: 9-1-1 content properly excluded from all simulated pairs!")
    
    return True

async def main():
    try:
        success = await test_voting_pair_exclusion()
        if success:
            print("\n🎉 Voting pair exclusion is working correctly!")
            print("🤔 The issue might be:")
            print("   1. A race condition between interaction recording and voting pair generation")
            print("   2. Frontend caching showing old voting pairs")
            print("   3. Multiple browser tabs/sessions causing conflicts")
            print("   4. The interaction was recorded after the pair was already shown")
        else:
            print("\n💥 Voting pair exclusion has issues that need to be addressed!")
        return success
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)