#!/usr/bin/env python3
"""
URGENT: Investigate the critical bug where passed content is still appearing in voting pairs
This is based on screenshot evidence showing HBO Boxing appearing despite being marked as "Passed"
"""

import pymongo
import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.append('/app/backend')

async def investigate_critical_exclusion_bug():
    print("🚨 CRITICAL BUG INVESTIGATION - Passed Content Still Appearing")
    print("=" * 70)
    
    # Import the backend functions
    try:
        from server import _get_user_vote_stats, _get_all_content_items_as_df, _get_candidate_items_for_pairing, db
    except ImportError as e:
        print(f"❌ Failed to import backend functions: {e}")
        return False
    
    # Test user details from screenshot
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"  # test010@yopmail.com
    hbo_boxing_id = "466d1b4f-e1a5-4bfe-8321-4b73abc00a28"  # HBO Boxing
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = mongo_client["movie_preferences_db"]
    
    print(f"🔍 Screenshot shows: HBO Boxing appearing in voting pair")
    print(f"🔍 User: test010@yopmail.com ({user_id})")
    print(f"🔍 Content: HBO Boxing ({hbo_boxing_id})")
    print(f"🔍 Evidence: 'Passed (click to undo)' button visible")
    print()
    
    # Step 1: Check ALL interactions for HBO Boxing
    print("1. Checking ALL interactions with HBO Boxing...")
    all_hbo_interactions = list(local_db.user_interactions.find({
        "user_id": user_id,
        "$or": [
            {"content_id": hbo_boxing_id},
            {"content_id": "tt0775367"}  # IMDB ID for HBO Boxing
        ]
    }))
    
    print(f"📊 Total interactions with HBO Boxing: {len(all_hbo_interactions)}")
    for interaction in all_hbo_interactions:
        print(f"   - Type: {interaction['interaction_type']}")
        print(f"     Content ID: {interaction['content_id']}")
        print(f"     Timestamp: {interaction.get('timestamp', 'Unknown')}")
        print(f"     Interaction ID: {interaction['id']}")
    
    # Step 2: Test the exclusion logic in real-time
    print(f"\n2. Testing exclusion logic RIGHT NOW...")
    vote_count, voted_pairs, excluded_content_ids = await _get_user_vote_stats(user_id, None)
    
    print(f"   Vote count: {vote_count}")
    print(f"   Excluded content IDs: {len(excluded_content_ids)}")
    
    hbo_excluded = hbo_boxing_id in excluded_content_ids
    hbo_imdb_excluded = "tt0775367" in excluded_content_ids
    
    print(f"   HBO Boxing content ID excluded: {'✅ YES' if hbo_excluded else '❌ NO'}")
    print(f"   HBO Boxing IMDB ID excluded: {'✅ YES' if hbo_imdb_excluded else '❌ NO'}")
    
    if not (hbo_excluded or hbo_imdb_excluded):
        print("🚨 CRITICAL: HBO Boxing is NOT in the excluded set!")
        print("   This explains why it's appearing in voting pairs!")
        return False
    
    # Step 3: Test the candidate generation logic
    print(f"\n3. Testing candidate generation logic...")
    
    try:
        # Get all content as DataFrame
        all_content_df = await _get_all_content_items_as_df(db)
        print(f"   Total content in DataFrame: {len(all_content_df)}")
        
        # Check if HBO Boxing is in the DataFrame
        hbo_in_df = hbo_boxing_id in all_content_df['content_id'].values
        print(f"   HBO Boxing in content DataFrame: {'✅ YES' if hbo_in_df else '❌ NO'}")
        
        # Test candidate generation for cold-start
        user_profile = {}
        strategy = "cold_start"
        
        candidate_items = await _get_candidate_items_for_pairing(
            user_profile, all_content_df, strategy, vote_count, excluded_content_ids, db
        )
        
        print(f"   Candidate items returned: {len(candidate_items)}")
        
        # Check if HBO Boxing is in candidates
        hbo_in_candidates = any(
            item.get('content_id') == hbo_boxing_id for item in candidate_items
        )
        print(f"   HBO Boxing in candidates: {'❌ YES (BUG!)' if hbo_in_candidates else '✅ NO (CORRECT)'}")
        
        if hbo_in_candidates:
            print("🚨 CRITICAL BUG FOUND: HBO Boxing is in candidate list despite being excluded!")
            
            # Find the specific candidate
            for item in candidate_items:
                if item.get('content_id') == hbo_boxing_id:
                    print(f"   Candidate details: {item}")
                    break
        
    except Exception as e:
        print(f"❌ Error testing candidate generation: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Check the exclusion filter logic directly
    print(f"\n4. Testing exclusion filter logic directly...")
    
    # Simulate the exclusion filter from _get_candidate_items_for_pairing
    if excluded_content_ids:
        # Check content_id field
        content_id_mask = all_content_df['content_id'].isin(excluded_content_ids)
        
        # Check if HBO Boxing would be filtered out
        hbo_row = all_content_df[all_content_df['content_id'] == hbo_boxing_id]
        if not hbo_row.empty:
            hbo_would_be_filtered = hbo_row.iloc[0]['content_id'] in excluded_content_ids
            print(f"   HBO Boxing would be filtered by content_id: {'✅ YES' if hbo_would_be_filtered else '❌ NO'}")
            
            # Check other ID fields
            for col in all_content_df.columns:
                if 'id' in col.lower() and col != 'content_id':
                    hbo_value = hbo_row.iloc[0][col]
                    if hbo_value in excluded_content_ids:
                        print(f"   HBO Boxing filtered by {col}: ✅ YES")
                    else:
                        print(f"   HBO Boxing filtered by {col}: ❌ NO")
        else:
            print("   ❌ HBO Boxing not found in DataFrame!")
    
    # Step 5: Test if there are any recent votes with HBO Boxing
    print(f"\n5. Checking for recent voting activity...")
    
    recent_votes = list(local_db.votes.find({
        "user_id": user_id,
        "$or": [
            {"winner_id": hbo_boxing_id},
            {"loser_id": hbo_boxing_id}
        ]
    }).sort("timestamp", -1))
    
    if recent_votes:
        print(f"⚠️  Found {len(recent_votes)} votes involving HBO Boxing:")
        for vote in recent_votes:
            print(f"   - Vote ID: {vote['id']}")
            print(f"     Winner: {vote.get('winner_id', 'Unknown')}")
            print(f"     Loser: {vote.get('loser_id', 'Unknown')}")
            print(f"     Timestamp: {vote.get('timestamp', 'Unknown')}")
    else:
        print("✅ No votes found with HBO Boxing")
    
    # Step 6: Summary and next steps
    print(f"\n6. BUG ANALYSIS SUMMARY")
    print("=" * 30)
    
    if hbo_excluded or hbo_imdb_excluded:
        print("✅ HBO Boxing IS in the excluded set")
        if hbo_in_candidates:
            print("🚨 BUT it's still appearing in candidate generation!")
            print("💡 This indicates a bug in the candidate filtering logic")
            print("🔧 Need to investigate _get_candidate_items_for_pairing function")
        else:
            print("✅ And it's NOT in candidate generation")
            print("🤔 This suggests the bug might be:")
            print("   1. Frontend caching old voting pairs")
            print("   2. Race condition in pair generation")
            print("   3. Different code path being used")
            print("   4. Issue with specific endpoint (main vs replacement)")
    else:
        print("🚨 HBO Boxing is NOT in the excluded set - major bug!")
        print("💡 This indicates a bug in the _get_user_vote_stats function")
    
    return True

async def main():
    try:
        success = await investigate_critical_exclusion_bug()
        return success
    except Exception as e:
        print(f"❌ Error during critical investigation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)