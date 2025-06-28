#!/usr/bin/env python3
"""
Diagnostic script to investigate why "HBO Boxing" was shown to test010@yopmail.com 
despite being marked as "Passed" - comprehensive analysis
"""

import pymongo
from datetime import datetime
import json

def main():
    print("🔍 Diagnosing Pass Functionality Bug - HBO Boxing Content")
    print("=" * 60)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    user_email = "test010@yopmail.com"
    content_title = "HBO Boxing"
    
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
    # Try exact match first
    content = db.content.find_one({"title": content_title})
    if not content:
        # Try case-insensitive match
        content = db.content.find_one({"title": {"$regex": f"^{content_title}$", "$options": "i"}})
    
    if not content:
        print(f"❌ Content '{content_title}' not found in database")
        # Try partial match for HBO content
        partial_content = list(db.content.find({"title": {"$regex": "HBO", "$options": "i"}}))
        if partial_content:
            print(f"📋 Found {len(partial_content)} HBO-related titles:")
            for item in partial_content[:10]:  # Show first 10
                print(f"   - {item.get('title', 'Unknown')} (ID: {item.get('id', 'Unknown')})")
                print(f"     Year: {item.get('year', 'Unknown')}, Type: {item.get('content_type', 'Unknown')}")
        return
    
    content_id = content["id"]
    content_imdb_id = content.get("imdb_id", "")
    print(f"✅ Found content ID: {content_id}")
    print(f"   IMDB ID: {content_imdb_id}")
    print(f"   Year: {content.get('year', 'Unknown')}")
    print(f"   Type: {content.get('content_type', 'Unknown')}")
    print(f"   Genre: {content.get('genre', 'Unknown')}")
    print()
    
    # 3. Check for ALL interactions with this content
    print("3. Checking ALL interactions with this content...")
    all_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "$or": [
            {"content_id": content_id},
            {"content_id": content_imdb_id} if content_imdb_id else {"content_id": content_id}
        ]
    }))
    
    print(f"📊 Total interactions with HBO Boxing: {len(all_interactions)}")
    
    pass_interaction = None
    for interaction in all_interactions:
        print(f"   - Type: {interaction['interaction_type']}")
        print(f"     Content ID: {interaction['content_id']}")
        print(f"     Timestamp: {interaction.get('timestamp', 'Unknown')}")
        print(f"     Interaction ID: {interaction.get('id', 'Unknown')}")
        
        if interaction['interaction_type'] == 'passed':
            pass_interaction = interaction
    
    if not pass_interaction:
        print("❌ NO 'passed' interaction found for HBO Boxing!")
        print("   User may have used a different interaction type")
    else:
        print("✅ Found 'passed' interaction")
    print()
    
    # 4. Check ALL pass interactions for this user
    print("4. Checking ALL pass interactions for this user...")
    all_pass_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "interaction_type": "passed"
    }))
    
    print(f"📊 Total PASS interactions for user: {len(all_pass_interactions)}")
    
    if all_pass_interactions:
        print("   Pass interactions:")
        for i, interaction in enumerate(all_pass_interactions, 1):
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
    else:
        print("❌ NO pass interactions found for this user!")
    print()
    
    # 5. Check ALL interactions for this user (all types)
    print("5. Checking ALL user interactions summary...")
    interaction_summary = {}
    all_user_interactions = list(db.user_interactions.find({"user_id": user_id}))
    
    for interaction in all_user_interactions:
        interaction_type = interaction['interaction_type']
        if interaction_type not in interaction_summary:
            interaction_summary[interaction_type] = 0
        interaction_summary[interaction_type] += 1
    
    print(f"📊 Interaction summary for user:")
    for interaction_type, count in interaction_summary.items():
        print(f"   - {interaction_type}: {count}")
    print()
    
    # 6. Test the exclusion logic directly
    print("6. Testing current exclusion logic...")
    
    # Simulate the _get_user_vote_stats function
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
    print(f"   Checking if HBO Boxing is excluded...")
    
    hbo_excluded = content_id in excluded_content_ids
    hbo_imdb_excluded = content_imdb_id in excluded_content_ids if content_imdb_id else False
    
    print(f"   HBO Boxing content ID excluded: {'✅ YES' if hbo_excluded else '❌ NO'}")
    if content_imdb_id:
        print(f"   HBO Boxing IMDB ID excluded: {'✅ YES' if hbo_imdb_excluded else '❌ NO'}")
    
    print(f"   Sample excluded IDs: {list(excluded_content_ids)[:10]}")
    print()
    
    # 7. Check recent votes to see if HBO Boxing appeared
    print("7. Checking recent votes...")
    recent_votes = list(db.votes.find({"user_id": user_id}).sort("timestamp", -1).limit(50))
    print(f"📊 Recent votes count: {len(recent_votes)}")
    
    hbo_votes = []
    for vote in recent_votes:
        if vote.get("winner_id") == content_id or vote.get("loser_id") == content_id:
            hbo_votes.append(vote)
            print(f"⚠️  Found HBO Boxing in vote:")
            print(f"   Vote ID: {vote['id']}")
            print(f"   Winner: {vote.get('winner_id', 'Unknown')}")
            print(f"   Loser: {vote.get('loser_id', 'Unknown')}")
            print(f"   Timestamp: {vote.get('timestamp', 'Unknown')}")
    
    if not hbo_votes:
        print(f"ℹ️  HBO Boxing not found in recent {len(recent_votes)} votes")
    print()
    
    # 8. Cross-reference timing between interactions and votes
    print("8. Analyzing timing between interactions and votes...")
    
    if pass_interaction and hbo_votes:
        interaction_time = pass_interaction.get('timestamp')
        print(f"   Pass interaction time: {interaction_time}")
        
        for vote in hbo_votes:
            vote_time = vote.get('timestamp')
            print(f"   Vote time: {vote_time}")
            
            # If both have timestamps, compare them
            if interaction_time and vote_time:
                try:
                    # Basic timestamp comparison (this is simplified)
                    print(f"   Timing analysis needed for accurate comparison")
                except:
                    print(f"   Could not compare timestamps")
    
    # 9. Check for any data inconsistencies
    print("9. Checking for data inconsistencies...")
    
    # Check if there are duplicate interactions
    duplicate_check = {}
    for interaction in all_user_interactions:
        key = f"{interaction['content_id']}_{interaction['interaction_type']}"
        if key not in duplicate_check:
            duplicate_check[key] = 0
        duplicate_check[key] += 1
    
    duplicates_found = False
    for key, count in duplicate_check.items():
        if count > 1:
            print(f"   ⚠️  Found {count} duplicate interactions: {key}")
            duplicates_found = True
    
    if not duplicates_found:
        print("   ✅ No duplicate interactions found")
    
    # 10. Summary and diagnosis
    print("\n10. COMPREHENSIVE DIAGNOSIS")
    print("=" * 35)
    
    if pass_interaction:
        if hbo_excluded or hbo_imdb_excluded:
            print("✅ Pass interaction recorded AND HBO Boxing should be excluded")
            if hbo_votes:
                print("⚠️  BUT there are votes involving HBO Boxing!")
                print("🤔 Possible explanations:")
                print("   1. Votes occurred BEFORE the pass interaction")
                print("   2. Race condition between voting and interaction recording") 
                print("   3. Bug in the voting pair generation logic")
                print("   4. Frontend caching showing old pairs")
            else:
                print("✅ No votes found with HBO Boxing - exclusion appears to be working")
                print("🤔 If user reported seeing it recently:")
                print("   1. Frontend caching issue (likely)")
                print("   2. User saw it in different context (recommendations, etc.)")
                print("   3. Temporary inconsistency that self-corrected")
        else:
            print("⚠️  Pass interaction recorded BUT HBO Boxing NOT in excluded set")
            print("🤔 This indicates a BUG in the exclusion logic:")
            print("   1. ID matching issue in _get_user_vote_stats")
            print("   2. Content ID format inconsistency")
            print("   3. Database query problem")
    else:
        print("❌ NO pass interaction found for HBO Boxing")
        print("🤔 This suggests:")
        print("   1. User actually used different interaction type (not_interested, etc.)")
        print("   2. Pass interaction was never recorded (API bug)")
        print("   3. Interaction was recorded with different content ID")
        print("   4. Interaction was deleted/lost")
    
    print(f"\n📋 SUMMARY:")
    print(f"   - User has {len(all_pass_interactions)} total pass interactions")
    print(f"   - HBO Boxing pass interaction: {'✅ Found' if pass_interaction else '❌ Missing'}")
    print(f"   - HBO Boxing excluded: {'✅ Yes' if (hbo_excluded or hbo_imdb_excluded) else '❌ No'}")
    print(f"   - HBO Boxing in recent votes: {'⚠️ Yes' if hbo_votes else '✅ No'}")
    print(f"   - Total excluded content: {len(excluded_content_ids)}")

if __name__ == "__main__":
    main()