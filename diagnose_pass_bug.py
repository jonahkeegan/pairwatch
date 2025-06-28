#!/usr/bin/env python3
"""
Diagnostic script to investigate why "Leonardo DiCaprio: A Life in Progress" 
was shown to test009@yopmail.com despite being marked as "Passed"
"""

import pymongo
from datetime import datetime
import json

def main():
    print("🔍 Diagnosing Pass Functionality Bug")
    print("=" * 50)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    user_email = "test009@yopmail.com"
    content_title = "Leonardo DiCaprio: A Life in Progress"
    
    print(f"User: {user_email}")
    print(f"Content: {content_title}")
    print()
    
    # 1. Find the user
    print("1. Checking user account...")
    user = db.users.find_one({"email": user_email})
    if not user:
        print(f"❌ User {user_email} not found in database")
        return
    
    user_id = user["id"]
    print(f"✅ Found user ID: {user_id}")
    print(f"   User name: {user.get('name', 'Unknown')}")
    print(f"   Total votes: {user.get('total_votes', 0)}")
    print()
    
    # 2. Find the content
    print("2. Checking content...")
    content = db.content.find_one({"title": {"$regex": content_title, "$options": "i"}})
    if not content:
        print(f"❌ Content '{content_title}' not found in database")
        # Try partial match
        partial_content = list(db.content.find({"title": {"$regex": "Leonardo DiCaprio", "$options": "i"}}))
        if partial_content:
            print(f"📋 Found {len(partial_content)} similar titles:")
            for item in partial_content:
                print(f"   - {item.get('title', 'Unknown')} (ID: {item.get('id', 'Unknown')})")
        return
    
    content_id = content["id"]
    content_imdb_id = content.get("imdb_id", "")
    print(f"✅ Found content ID: {content_id}")
    print(f"   IMDB ID: {content_imdb_id}")
    print(f"   Year: {content.get('year', 'Unknown')}")
    print(f"   Type: {content.get('content_type', 'Unknown')}")
    print(f"   Genre: {content.get('genre', 'Unknown')}")
    print()
    
    # 3. Check for pass interactions
    print("3. Checking pass interactions...")
    pass_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "interaction_type": "passed"
    }))
    
    print(f"📊 Total pass interactions for user: {len(pass_interactions)}")
    
    # Check if this specific content was passed
    specific_pass = db.user_interactions.find_one({
        "user_id": user_id,
        "content_id": content_id,
        "interaction_type": "passed"
    })
    
    # Also check by IMDB ID
    imdb_pass = None
    if content_imdb_id:
        imdb_pass = db.user_interactions.find_one({
            "user_id": user_id,
            "content_id": content_imdb_id,
            "interaction_type": "passed"
        })
    
    if specific_pass:
        print(f"✅ Found pass interaction for this content:")
        print(f"   Interaction ID: {specific_pass['id']}")
        print(f"   Content ID: {specific_pass['content_id']}")
        print(f"   Timestamp: {specific_pass.get('timestamp', 'Unknown')}")
    elif imdb_pass:
        print(f"✅ Found pass interaction using IMDB ID:")
        print(f"   Interaction ID: {imdb_pass['id']}")
        print(f"   Content ID: {imdb_pass['content_id']}")
        print(f"   Timestamp: {imdb_pass.get('timestamp', 'Unknown')}")
    else:
        print(f"❌ NO pass interaction found for this content")
        print(f"   Checked content_id: {content_id}")
        if content_imdb_id:
            print(f"   Checked imdb_id: {content_imdb_id}")
    print()
    
    # 4. Show all pass interactions for debugging
    if pass_interactions:
        print("📋 All pass interactions for this user:")
        for i, interaction in enumerate(pass_interactions, 1):
            # Try to find the content for this interaction
            passed_content = db.content.find_one({
                "$or": [
                    {"id": interaction["content_id"]},
                    {"imdb_id": interaction["content_id"]}
                ]
            })
            content_name = passed_content.get("title", "Unknown") if passed_content else "Content not found"
            print(f"   {i}. {content_name}")
            print(f"      Content ID: {interaction['content_id']}")
            print(f"      Timestamp: {interaction.get('timestamp', 'Unknown')}")
    print()
    
    # 5. Check recent votes to see if this content appeared in voting pairs
    print("5. Checking recent votes...")
    recent_votes = list(db.votes.find({"user_id": user_id}).sort("timestamp", -1).limit(20))
    print(f"📊 Recent votes count: {len(recent_votes)}")
    
    content_in_votes = False
    for vote in recent_votes:
        if vote.get("winner_id") == content_id or vote.get("loser_id") == content_id:
            content_in_votes = True
            print(f"⚠️  Found content in vote:")
            print(f"   Vote ID: {vote['id']}")
            print(f"   Winner: {vote.get('winner_id', 'Unknown')}")
            print(f"   Loser: {vote.get('loser_id', 'Unknown')}")
            print(f"   Timestamp: {vote.get('timestamp', 'Unknown')}")
            break
    
    if not content_in_votes:
        print(f"ℹ️  Content not found in recent 20 votes")
    print()
    
    # 6. Check all interactions for this content
    print("6. Checking all interactions with this content...")
    all_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "$or": [
            {"content_id": content_id},
            {"content_id": content_imdb_id}
        ]
    }))
    
    print(f"📊 Total interactions with this content: {len(all_interactions)}")
    for interaction in all_interactions:
        print(f"   Type: {interaction['interaction_type']}")
        print(f"   Content ID: {interaction['content_id']}")
        print(f"   Timestamp: {interaction.get('timestamp', 'Unknown')}")
    print()
    
    # 7. Test the exclusion logic directly
    print("7. Testing exclusion logic...")
    print("   Simulating _get_user_vote_stats function...")
    
    # Get all exclusion interactions
    exclusion_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "interaction_type": {"$in": ["watched", "not_interested", "passed"]}
    }))
    
    excluded_content_ids = set()
    for interaction in exclusion_interactions:
        interaction_content_id = interaction["content_id"]
        excluded_content_ids.add(interaction_content_id)
        
        # Also look up the content item to get both its ID and IMDB ID
        content_item = db.content.find_one({
            "$or": [
                {"id": interaction_content_id}, 
                {"imdb_id": interaction_content_id}
            ]
        })
        if content_item:
            excluded_content_ids.add(content_item.get("id", ""))
            excluded_content_ids.add(content_item.get("imdb_id", ""))
    
    # Remove empty strings
    excluded_content_ids.discard("")
    
    print(f"   Total excluded content IDs: {len(excluded_content_ids)}")
    print(f"   Checking if {content_id} is in excluded set...")
    
    if content_id in excluded_content_ids:
        print(f"   ✅ Content ID {content_id} IS in excluded set")
    else:
        print(f"   ❌ Content ID {content_id} IS NOT in excluded set")
    
    if content_imdb_id and content_imdb_id in excluded_content_ids:
        print(f"   ✅ IMDB ID {content_imdb_id} IS in excluded set")
    elif content_imdb_id:
        print(f"   ❌ IMDB ID {content_imdb_id} IS NOT in excluded set")
    
    print(f"   Sample excluded IDs: {list(excluded_content_ids)[:10]}")
    print()
    
    # 8. Summary and recommendations
    print("8. DIAGNOSIS SUMMARY")
    print("=" * 30)
    
    if specific_pass or imdb_pass:
        if content_id in excluded_content_ids or (content_imdb_id and content_imdb_id in excluded_content_ids):
            print("✅ Pass interaction recorded AND content should be excluded")
            print("🤔 This suggests the bug is in the voting pair generation logic")
            print("   Recommendations:")
            print("   - Check if voting pair endpoint is calling _get_user_vote_stats correctly")
            print("   - Verify _get_candidate_items_for_pairing is using excluded_content_ids properly")
            print("   - Check for race conditions or caching issues")
        else:
            print("⚠️  Pass interaction recorded BUT content not in excluded set")
            print("🤔 This suggests the exclusion logic has a bug")
            print("   Recommendations:")
            print("   - Check ID matching logic in _get_user_vote_stats")
            print("   - Verify content ID formats are consistent")
            print("   - Check for case sensitivity or trimming issues")
    else:
        print("❌ NO pass interaction found")
        print("🤔 This suggests either:")
        print("   - The pass was never recorded (API bug)")
        print("   - The pass was recorded with different IDs")
        print("   - The interaction was deleted somehow")
        print("   Recommendations:")
        print("   - Check /api/pass endpoint logs")
        print("   - Verify content ID used in pass request")
        print("   - Check for database cleanup operations")

if __name__ == "__main__":
    main()