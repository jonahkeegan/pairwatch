#!/usr/bin/env python3
"""
URGENT: Investigate why HBO Boxing is STILL appearing after the fix
The screenshot shows it's still being shown to test010@yopmail.com
"""

import asyncio
import pymongo
import requests
import time
from datetime import datetime, timedelta

async def emergency_bug_investigation():
    print("🚨 EMERGENCY BUG INVESTIGATION - HBO Boxing Still Appearing")
    print("=" * 65)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    user_email = "test010@yopmail.com"
    user_id = "f96bda6f-20cd-472c-91e6-9adf9a2a99f3"
    hbo_boxing_id = "466d1b4f-e1a5-4bfe-8321-4b73abc00a28"
    
    print(f"🔍 URGENT: Screenshot evidence shows HBO Boxing still appearing")
    print(f"📧 User: {user_email}")
    print(f"🎬 Content: HBO Boxing ({hbo_boxing_id})")
    print(f"📸 Evidence: 'Passed (click to undo)' button visible")
    print()
    
    # 1. Check current interaction status
    print("1. Checking CURRENT interaction status...")
    
    all_hbo_interactions = list(db.user_interactions.find({
        "user_id": user_id,
        "$or": [
            {"content_id": hbo_boxing_id},
            {"content_id": "tt0775367"}  # IMDB ID
        ]
    }).sort("timestamp", -1))
    
    print(f"📊 Total interactions with HBO Boxing: {len(all_hbo_interactions)}")
    
    if all_hbo_interactions:
        latest_interaction = all_hbo_interactions[0]
        print(f"   Latest interaction:")
        print(f"   - Type: {latest_interaction['interaction_type']}")
        print(f"   - Content ID: {latest_interaction['content_id']}")
        print(f"   - Timestamp: {latest_interaction.get('timestamp', 'Unknown')}")
        print(f"   - ID: {latest_interaction['id']}")
    else:
        print("❌ NO interactions found!")
    
    # 2. Check if there are very recent votes involving HBO Boxing
    print(f"\n2. Checking RECENT voting activity...")
    
    # Check votes from the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    recent_hbo_votes = list(db.votes.find({
        "user_id": user_id,
        "$or": [
            {"winner_id": hbo_boxing_id},
            {"loser_id": hbo_boxing_id}
        ],
        "timestamp": {"$gte": one_hour_ago}
    }).sort("timestamp", -1))
    
    if recent_hbo_votes:
        print(f"⚠️  Found {len(recent_hbo_votes)} RECENT votes with HBO Boxing:")
        for vote in recent_hbo_votes:
            print(f"   - Vote ID: {vote['id']}")
            print(f"     Winner: {vote.get('winner_id', 'Unknown')}")
            print(f"     Loser: {vote.get('loser_id', 'Unknown')}")
            print(f"     Timestamp: {vote.get('timestamp', 'Unknown')}")
    else:
        print("✅ No recent votes with HBO Boxing")
    
    # 3. Test the backend logic RIGHT NOW
    print(f"\n3. Testing backend exclusion logic RIGHT NOW...")
    
    import sys
    sys.path.append('/app/backend')
    
    try:
        from server import _get_user_vote_stats, db as server_db
        
        vote_count, voted_pairs, excluded_content_ids = await _get_user_vote_stats(user_id, None)
        
        print(f"   Vote count: {vote_count}")
        print(f"   Excluded content IDs: {len(excluded_content_ids)}")
        
        hbo_excluded = hbo_boxing_id in excluded_content_ids
        print(f"   HBO Boxing excluded: {'✅ YES' if hbo_excluded else '❌ NO'}")
        
        if not hbo_excluded:
            print("🚨 CRITICAL: HBO Boxing is NOT being excluded by the backend!")
            print(f"   Sample excluded IDs: {list(excluded_content_ids)[:10]}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing backend logic: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Check backend logs for recent activity
    print(f"\n4. Checking backend logs for recent activity...")
    
    import subprocess
    
    try:
        # Get recent backend logs
        result = subprocess.run([
            "tail", "-n", "100", "/var/log/supervisor/backend.out.log"
        ], capture_output=True, text=True)
        
        log_lines = result.stdout.split('\n')
        
        # Look for HBO Boxing content ID in logs
        hbo_log_lines = [line for line in log_lines if hbo_boxing_id in line]
        
        if hbo_log_lines:
            print(f"⚠️  Found {len(hbo_log_lines)} log entries with HBO Boxing:")
            for line in hbo_log_lines[-3:]:  # Show last 3
                print(f"   {line.strip()}")
        else:
            print("✅ No HBO Boxing found in recent backend logs")
        
        # Look for voting-pair requests
        voting_log_lines = [line for line in log_lines if "voting-pair" in line and user_id[:8] in line]
        
        if voting_log_lines:
            print(f"   Recent voting-pair requests for user:")
            for line in voting_log_lines[-3:]:  # Show last 3
                print(f"   {line.strip()}")
        
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
    
    # 5. Test if there are multiple endpoints being used
    print(f"\n5. Checking ALL possible endpoints that could serve voting pairs...")
    
    # Check if there are any other endpoints
    try:
        import os
        backend_file = "/app/backend/server.py"
        
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # Look for any endpoint that might return VotePair
        voting_endpoints = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if '@api_router.get(' in line and ('voting' in line or 'pair' in line):
                voting_endpoints.append((i+1, line.strip()))
        
        print(f"   Found {len(voting_endpoints)} potential voting endpoints:")
        for line_num, endpoint in voting_endpoints:
            print(f"   Line {line_num}: {endpoint}")
        
    except Exception as e:
        print(f"❌ Error checking endpoints: {e}")
    
    # 6. Check if there's a caching issue
    print(f"\n6. Checking for potential caching issues...")
    
    # Check if the user has multiple sessions
    user_sessions = list(db.sessions.find({"user_id": user_id}))
    print(f"   User sessions: {len(user_sessions)}")
    
    # Check if there are any guest sessions that might be interfering
    if user_sessions:
        for session in user_sessions[-2:]:  # Show last 2
            print(f"   Session: {session.get('session_id', 'Unknown')}")
            print(f"   Created: {session.get('created_at', 'Unknown')}")
    
    # 7. Final assessment
    print(f"\n7. CRITICAL ASSESSMENT")
    print("=" * 25)
    
    print("🚨 SCREENSHOT EVIDENCE CONFIRMS BUG IS STILL PRESENT")
    print("   Despite the fix, HBO Boxing is still appearing to the user")
    print("   This indicates there's:")
    print("   1. Another code path not covered by the fix")
    print("   2. Frontend caching serving old data")
    print("   3. Race condition between interaction and voting")
    print("   4. Different endpoint being used")
    print("   5. Bug in a different part of the system")
    
    print(f"\n💡 IMMEDIATE NEXT STEPS:")
    print("   1. Identify which exact endpoint is serving the problematic content")
    print("   2. Check if frontend is caching old voting pairs")
    print("   3. Verify all voting-related endpoints have proper exclusions")
    print("   4. Add comprehensive logging to track the issue")
    
    return False

async def main():
    try:
        await emergency_bug_investigation()
    except Exception as e:
        print(f"❌ Emergency investigation error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())