#!/usr/bin/env python3
"""
Test alternative image sources and update a few poster URLs
to see if the issue is specific to Amazon URLs
"""

import pymongo
import requests

def test_alternative_image_sources():
    print("🔧 Testing Alternative Image Sources")
    print("=" * 40)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Test URLs from different sources
    test_urls = {
        "Direct image URL": "https://via.placeholder.com/300x450/1a1a1a/ffffff?text=Test+Poster",
        "Another CDN": "https://images.unsplash.com/photo-1489599324190-06b1d1f30e78?w=300&h=450&fit=crop",
        "Different format": "https://picsum.photos/300/450"
    }
    
    print("🧪 Testing different image sources...")
    
    working_alternatives = []
    
    for source_name, test_url in test_urls.items():
        print(f"\n   Testing {source_name}:")
        print(f"   URL: {test_url}")
        
        try:
            response = requests.head(test_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    print(f"   ✅ Working ({response.status_code}, {content_type})")
                    working_alternatives.append((source_name, test_url))
                else:
                    print(f"   ⚠️  Not image content ({content_type})")
            else:
                print(f"   ❌ Failed ({response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Update a test movie with a working alternative
    if working_alternatives:
        print(f"\n🔄 Updating test content with alternative image...")
        
        # Find Oppenheimer
        oppenheimer = db.content.find_one({"title": "Oppenheimer", "year": "2023"})
        
        if oppenheimer:
            original_poster = oppenheimer.get('poster')
            test_source, test_url = working_alternatives[0]
            
            print(f"   Original poster: {original_poster}")
            print(f"   Test poster ({test_source}): {test_url}")
            
            # Update with test image
            db.content.update_one(
                {"id": oppenheimer["id"]},
                {"$set": {
                    "poster": test_url,
                    "original_poster": original_poster  # Backup
                }}
            )
            
            print(f"   ✅ Updated Oppenheimer with test image")
            print(f"   📱 Check the voting interface to see if this image loads")
            
            return oppenheimer["id"], original_poster, test_url
    
    return None, None, None

def check_image_loading_in_browser():
    """Provide instructions for testing in browser"""
    print(f"\n🖥️  Browser Testing Instructions:")
    print(f"   1. Open the voting interface in your browser")
    print(f"   2. Open Developer Tools (F12)")
    print(f"   3. Go to Console tab")
    print(f"   4. Look for these debug messages:")
    print(f"      - 'Image loaded successfully: [URL]'")
    print(f"      - 'Image failed to load: [URL]'")
    print(f"   5. Go to Network tab")
    print(f"   6. Filter by 'Images' and see which requests are failing")
    print(f"   7. Check if there are any CORS errors in console")

def restore_original_poster(content_id, original_poster):
    """Restore original poster URL"""
    if content_id and original_poster:
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["movie_preferences_db"]
        
        db.content.update_one(
            {"id": content_id},
            {"$set": {"poster": original_poster}, "$unset": {"original_poster": ""}}
        )
        print(f"✅ Restored original poster URL")

if __name__ == "__main__":
    content_id, original_poster, test_url = test_alternative_image_sources()
    check_image_loading_in_browser()
    
    if content_id:
        print(f"\n⚠️  IMPORTANT: Test image is now active")
        print(f"   Content ID: {content_id}")
        print(f"   Test URL: {test_url}")
        print(f"   Original URL backed up in 'original_poster' field")
        print(f"\n   To restore original poster, run:")
        print(f"   restore_original_poster('{content_id}', '{original_poster}')")
        
        # Auto-restore after a brief period (optional)
        import time
        print(f"\n⏰ Auto-restoring original poster in 60 seconds...")
        print(f"   Press Ctrl+C to cancel and keep test image")
        
        try:
            time.sleep(60)
            restore_original_poster(content_id, original_poster)
            print(f"✅ Original poster restored automatically")
        except KeyboardInterrupt:
            print(f"\n⏹️  Auto-restore cancelled - test image remains active")
    else:
        print(f"\n❌ No working alternative images found")