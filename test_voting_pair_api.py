#!/usr/bin/env python3
"""
Check what poster URLs are actually being returned in voting pairs
Test the voting pair API to see the actual data structure
"""

import requests
import json

def test_voting_pair_api():
    print("🔍 Testing Voting Pair API Response")
    print("=" * 40)
    
    BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"
    
    # Create a guest session
    try:
        session_response = requests.post(f"{BASE_URL}/session")
        if session_response.status_code == 200:
            session_id = session_response.json().get('session_id')
            print(f"✅ Created session: {session_id}")
            
            # Get a voting pair
            params = {"session_id": session_id}
            pair_response = requests.get(f"{BASE_URL}/voting-pair", params=params)
            
            if pair_response.status_code == 200:
                pair_data = pair_response.json()
                print(f"✅ Got voting pair successfully")
                
                # Analyze the response structure
                print(f"\n📋 Voting Pair Structure:")
                print(f"   Content Type: {pair_data.get('content_type', 'Unknown')}")
                
                # Check Item 1
                item1 = pair_data.get('item1', {})
                print(f"\n📽️  Item 1:")
                print(f"   Title: {item1.get('title', 'Unknown')}")
                print(f"   Year: {item1.get('year', 'Unknown')}")
                print(f"   Type: {item1.get('content_type', 'Unknown')}")
                print(f"   Poster URL: {item1.get('poster', 'NOT FOUND')}")
                print(f"   Poster exists: {bool(item1.get('poster'))}")
                print(f"   Poster length: {len(item1.get('poster', ''))}")
                
                # Check Item 2  
                item2 = pair_data.get('item2', {})
                print(f"\n📽️  Item 2:")
                print(f"   Title: {item2.get('title', 'Unknown')}")
                print(f"   Year: {item2.get('year', 'Unknown')}")
                print(f"   Type: {item2.get('content_type', 'Unknown')}")
                print(f"   Poster URL: {item2.get('poster', 'NOT FOUND')}")
                print(f"   Poster exists: {bool(item2.get('poster'))}")
                print(f"   Poster length: {len(item2.get('poster', ''))}")
                
                # Test the poster URLs
                print(f"\n🧪 Testing Poster URL Accessibility:")
                
                for i, item in enumerate([item1, item2], 1):
                    poster_url = item.get('poster')
                    if poster_url:
                        print(f"\n   Item {i} Poster Test:")
                        test_poster_access(poster_url)
                    else:
                        print(f"\n   Item {i}: ❌ No poster URL")
                
                # Show raw JSON for debugging
                print(f"\n📄 Raw API Response (first 500 chars):")
                print(json.dumps(pair_data, indent=2)[:500] + "...")
                
            else:
                print(f"❌ Failed to get voting pair: {pair_response.status_code}")
                print(f"   Response: {pair_response.text}")
        else:
            print(f"❌ Failed to create session: {session_response.status_code}")
    
    except Exception as e:
        print(f"❌ Error testing API: {e}")

def test_poster_access(url):
    """Quick test of poster URL accessibility"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            print(f"   ✅ Accessible ({response.status_code}, {content_type})")
        else:
            print(f"   ❌ Failed ({response.status_code})")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    test_voting_pair_api()