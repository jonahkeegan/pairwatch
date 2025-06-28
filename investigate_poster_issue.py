#!/usr/bin/env python3
"""
Investigate the poster image loading issue
Check database poster URLs and test their accessibility
"""

import pymongo
import requests
from urllib.parse import urlparse
import time

def investigate_poster_loading_issue():
    print("🔍 Investigating Poster Image Loading Issue")
    print("=" * 50)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Find the specific content mentioned in screenshot
    martin_scorsese_content = db.content.find_one({
        "title": {"$regex": "Martin Scorsese.*True Confessions", "$options": "i"}
    })
    
    if martin_scorsese_content:
        print(f"📋 Found Martin Scorsese content:")
        print(f"   Title: {martin_scorsese_content.get('title', 'Unknown')}")
        print(f"   ID: {martin_scorsese_content.get('id', 'Unknown')}")
        print(f"   Poster URL: {martin_scorsese_content.get('poster', 'None')}")
        print(f"   Year: {martin_scorsese_content.get('year', 'Unknown')}")
        print(f"   Type: {martin_scorsese_content.get('content_type', 'Unknown')}")
        
        poster_url = martin_scorsese_content.get('poster')
        if poster_url:
            print(f"\n🌐 Testing poster URL accessibility...")
            test_image_url(poster_url)
        else:
            print(f"\n❌ No poster URL found in database!")
    else:
        print("❌ Martin Scorsese content not found in database")
    
    # Check general poster URL statistics
    print(f"\n📊 General poster URL analysis...")
    
    total_content = db.content.count_documents({})
    content_with_poster = db.content.count_documents({"poster": {"$exists": True, "$ne": None, "$ne": ""}})
    content_without_poster = total_content - content_with_poster
    
    print(f"   Total content items: {total_content}")
    print(f"   Items with poster URLs: {content_with_poster}")
    print(f"   Items without poster URLs: {content_without_poster}")
    print(f"   Poster coverage: {(content_with_poster/total_content*100):.1f}%")
    
    # Sample some poster URLs to test
    print(f"\n🧪 Testing sample poster URLs...")
    
    sample_content = list(db.content.find(
        {"poster": {"$exists": True, "$ne": None, "$ne": ""}}, 
        {"title": 1, "poster": 1}
    ).limit(5))
    
    working_urls = 0
    broken_urls = 0
    
    for item in sample_content:
        title = item.get('title', 'Unknown')
        poster_url = item.get('poster', '')
        
        print(f"\n   Testing: {title}")
        print(f"   URL: {poster_url}")
        
        if test_image_url(poster_url):
            working_urls += 1
        else:
            broken_urls += 1
        
        time.sleep(0.5)  # Be nice to servers
    
    print(f"\n📋 URL Test Results:")
    print(f"   Working URLs: {working_urls}/{len(sample_content)}")
    print(f"   Broken URLs: {broken_urls}/{len(sample_content)}")
    
    # Check for common poster URL patterns
    print(f"\n🔍 Analyzing poster URL patterns...")
    
    poster_domains = {}
    all_poster_content = list(db.content.find(
        {"poster": {"$exists": True, "$ne": None, "$ne": ""}}, 
        {"poster": 1}
    ))
    
    for item in all_poster_content:
        poster_url = item.get('poster', '')
        if poster_url:
            try:
                domain = urlparse(poster_url).netloc
                if domain not in poster_domains:
                    poster_domains[domain] = 0
                poster_domains[domain] += 1
            except:
                pass
    
    print(f"   Poster URL domains:")
    for domain, count in sorted(poster_domains.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {domain}: {count} images")
    
    # Check for specific URL issues
    print(f"\n⚠️  Common poster URL issues to check:")
    print(f"   1. CORS (Cross-Origin Resource Sharing) restrictions")
    print(f"   2. HTTPS vs HTTP mixed content issues")
    print(f"   3. Image URL expiration or rate limiting")
    print(f"   4. Frontend image loading error handling")
    print(f"   5. Content Security Policy blocking external images")

def test_image_url(url):
    """Test if an image URL is accessible"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type.lower():
                print(f"   ✅ Working (200, {content_type})")
                return True
            else:
                print(f"   ⚠️  Response OK but not image content ({content_type})")
                return False
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    investigate_poster_loading_issue()