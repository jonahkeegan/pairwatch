#!/usr/bin/env python3
"""
Test to identify potential race conditions or timing issues in the exclusion logic
"""

import pymongo
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.append('/app/backend')

async def check_exclusion_timing():
    print("🔍 Checking Exclusion Timing and Race Conditions")
    print("=" * 50)
    
    # Import the backend functions
    try:
        from server import _get_user_vote_stats, db
    except ImportError as e:
        print(f"❌ Failed to import backend functions: {e}")
        return False
    
    # Test user details
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    content_id_911 = "8e914334-fdd5-45f1-aacb-c880cac6d402"
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = mongo_client["movie_preferences_db"]
    
    print(f"✅ Analyzing user: {user_id}")
    print(f"✅ Analyzing content: {content_id_911} (9-1-1)")
    
    # Check the timing of interactions vs votes
    print(f"\n🔍 Step 1: Checking interaction timing...")
    
    # Get the not_interested interaction
    interaction = local_db.user_interactions.find_one({
        "user_id": user_id,
        "content_id": content_id_911,
        "interaction_type": "not_interested"
    })
    
    if interaction:
        interaction_time = interaction.get('timestamp')
        print(f"   Not_interested interaction recorded at: {interaction_time}")
    else:
        print("   ❌ No not_interested interaction found!")
        return False
    
    # Get recent votes to check timing
    print(f"\n🔍 Step 2: Checking vote timing...")
    recent_votes = list(local_db.votes.find({"user_id": user_id}).sort("timestamp", -1).limit(10))
    
    print(f"   Recent votes count: {len(recent_votes)}")
    
    # Check if any votes involved the 9-1-1 content
    votes_with_911 = []
    for vote in recent_votes:
        if vote.get("winner_id") == content_id_911 or vote.get("loser_id") == content_id_911:
            votes_with_911.append(vote)
            vote_time = vote.get('timestamp')
            print(f"   ⚠️  Found vote with 9-1-1 at: {vote_time}")
            print(f"      Vote ID: {vote['id']}")
            print(f"      Winner: {vote.get('winner_id', 'Unknown')}")
            print(f"      Loser: {vote.get('loser_id', 'Unknown')}")
    
    if not votes_with_911:
        print("   ✅ No recent votes found with 9-1-1 content")
    
    # Check the current exclusion status
    print(f"\n🔍 Step 3: Testing current exclusion status...")
    vote_count, voted_pairs, excluded_content_ids = await _get_user_vote_stats(user_id, None)
    
    print(f"   Current excluded content count: {len(excluded_content_ids)}")
    
    content_911_excluded = content_id_911 in excluded_content_ids
    print(f"   9-1-1 currently excluded: {'✅ YES' if content_911_excluded else '❌ NO'}")
    
    # Get 9-1-1 content details
    content_911 = local_db.content.find_one({"id": content_id_911})
    if content_911:
        imdb_id = content_911.get("imdb_id")
        if imdb_id:
            imdb_excluded = imdb_id in excluded_content_ids
            print(f"   9-1-1 IMDB ID excluded: {'✅ YES' if imdb_excluded else '❌ NO'}")
    
    # Check if there are any other interactions that might interfere
    print(f"\n🔍 Step 4: Checking for conflicting interactions...")
    all_interactions = list(local_db.user_interactions.find({
        "user_id": user_id,
        "content_id": content_id_911
    }))
    
    print(f"   Total interactions with 9-1-1: {len(all_interactions)}")
    for interaction in all_interactions:
        print(f"   - Type: {interaction['interaction_type']}")
        print(f"     Timestamp: {interaction.get('timestamp', 'Unknown')}")
        print(f"     ID: {interaction.get('id', 'Unknown')}")
    
    # Check for potential session conflicts
    print(f"\n🔍 Step 5: Checking for session conflicts...")
    
    # Check if there are any votes without user_id (guest sessions) that might conflict
    session_votes = list(local_db.votes.find({
        "session_id": {"$exists": True},
        "$or": [
            {"winner_id": content_id_911},
            {"loser_id": content_id_911}
        ]
    }))
    
    if session_votes:
        print(f"   ⚠️  Found {len(session_votes)} session votes with 9-1-1 content:")
        for vote in session_votes:
            print(f"   - Session: {vote.get('session_id', 'Unknown')}")
            print(f"     Timestamp: {vote.get('timestamp', 'Unknown')}")
    else:
        print("   ✅ No session votes found with 9-1-1 content")
    
    # Summary
    print(f"\n📊 ANALYSIS SUMMARY:")
    print("=" * 30)
    
    if content_911_excluded:
        print("✅ 9-1-1 content is properly excluded in current state")
        if votes_with_911:
            print("⚠️  However, there were historical votes with this content")
            print("🤔 Possible explanations:")
            print("   1. Content was voted on BEFORE being marked as not_interested")
            print("   2. Race condition between voting and interaction recording")
            print("   3. Frontend caching showed old pairs after interaction was recorded")
            print("   4. Multiple browser tabs/sessions caused conflicts")
        else:
            print("✅ No historical votes found with 9-1-1 content")
            print("🤔 If user reported seeing it recently, possible explanations:")
            print("   1. Frontend caching issue")
            print("   2. User saw it in a different context (recommendations, watchlist)")
            print("   3. Temporary backend inconsistency that self-corrected")
    else:
        print("❌ 9-1-1 content is NOT properly excluded - there's a bug!")
        return False
    
    return True

async def main():
    try:
        success = await check_exclusion_timing()
        if success:
            print("\n🎯 CONCLUSION: Exclusion logic is working correctly")
            print("💡 The issue was likely timing-related or frontend caching")
        else:
            print("\n💥 CONCLUSION: There's a bug in the exclusion logic")
        return success
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)