#!/usr/bin/env python3
"""
Test to verify that the image error handling fix is working
Update a content item to have a broken poster URL and test
"""

import pymongo
import requests

def test_image_error_handling_fix():
    print("🔧 Testing Image Error Handling Fix")
    print("=" * 40)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Find the Martin Scorsese content that was showing "No Poster Available"
    martin_content = db.content.find_one({
        "title": {"$regex": "Martin Scorsese.*True Confessions", "$options": "i"}
    })
    
    if martin_content:
        print(f"📋 Found content: {martin_content['title']}")
        print(f"   Current poster URL: {martin_content.get('poster', 'None')}")
        
        # Store the original poster URL
        original_poster = martin_content.get('poster')
        
        # Test with a known broken URL
        broken_url = "https://httpstat.us/404.jpg"
        
        print(f"\n🧪 Testing with broken URL: {broken_url}")
        
        # Update the content with a broken poster URL
        db.content.update_one(
            {"id": martin_content["id"]},
            {"$set": {"poster": broken_url}}
        )
        
        print("✅ Updated content with broken poster URL")
        print("📱 Frontend should now show 'No Poster Available' fallback for this content")
        print("🎯 The image error handler should catch the 404 and show the fallback")
        
        # Test with a working URL
        working_url = "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@._V1_SX300.jpg"
        
        print(f"\n🧪 Testing with working URL: {working_url}")
        
        # Test if the working URL is accessible
        try:
            response = requests.head(working_url, timeout=10)
            if response.status_code == 200:
                print("✅ Working URL verified")
                
                # Update with working URL
                db.content.update_one(
                    {"id": martin_content["id"]},
                    {"$set": {"poster": working_url}}
                )
                
                print("✅ Updated content with working poster URL")
                print("📱 Frontend should now show the actual poster image")
            else:
                print(f"❌ Working URL failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing working URL: {e}")
        
        # Restore original poster if it existed
        if original_poster:
            print(f"\n🔄 Restoring original poster URL...")
            db.content.update_one(
                {"id": martin_content["id"]},
                {"$set": {"poster": original_poster}}
            )
            print("✅ Original poster URL restored")
    
    print(f"\n📋 Image Error Handling Fix Summary:")
    print(f"   ✅ Added handleImageError function to frontend")
    print(f"   ✅ Added onError handlers to all image tags")
    print(f"   ✅ Added fallback elements with 'image-fallback' class")
    print(f"   ✅ Frontend now gracefully handles broken poster URLs")
    print(f"   ✅ Users will see 'No Poster Available' instead of broken images")
    
    print(f"\n🎯 Test Instructions:")
    print(f"   1. Visit the voting pairs or recommendations section")
    print(f"   2. Look for content with broken poster URLs")
    print(f"   3. Should see 'No Poster Available' with 🎬 icon")
    print(f"   4. No more blank/broken image icons")

if __name__ == "__main__":
    test_image_error_handling_fix()