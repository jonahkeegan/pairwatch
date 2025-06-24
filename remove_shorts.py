#!/usr/bin/env python3
"""
Script to find and remove all content with "Short" or "Shorts" genre from the database.
This is a cleanup script to remove shorts that were previously imported.
"""

import pymongo
import json
from datetime import datetime

def main():
    # MongoDB connection
    print("🔍 Connecting to MongoDB...")
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Get initial content count
    initial_count = db.content.count_documents({})
    print(f"📊 Initial content count: {initial_count}")
    
    # Find content with "Short" or "Shorts" in genre
    print("\n🔍 Searching for content with 'Short' or 'Shorts' genre...")
    
    # Query for content containing short/shorts in genre
    shorts_query = {
        "$or": [
            {"genre": {"$regex": r"\bShort\b", "$options": "i"}},
            {"genre": {"$regex": r"\bShorts\b", "$options": "i"}}
        ]
    }
    
    shorts_content = list(db.content.find(shorts_query))
    
    print(f"📋 Found {len(shorts_content)} content items with Short/Shorts genre:")
    
    if len(shorts_content) == 0:
        print("✅ No shorts found in database - nothing to remove!")
        return
    
    # Display all shorts found
    for i, item in enumerate(shorts_content, 1):
        print(f"  {i}. {item.get('title', 'Unknown')} ({item.get('year', 'Unknown')}) - Genre: '{item.get('genre', 'Unknown')}'")
        print(f"     IMDB ID: {item.get('imdb_id', 'Unknown')}, Type: {item.get('content_type', 'Unknown')}")
    
    # Auto-confirm removal (since we're in automated environment)
    print(f"\n⚠️  Auto-proceeding with deletion of {len(shorts_content)} short film/content items from the database.")
    confirm = "yes"
    
    if confirm not in ['yes', 'y']:
        print("❌ Deletion cancelled by user.")
        return
    
    # Remove the shorts
    print(f"\n🗑️  Removing {len(shorts_content)} shorts from database...")
    
    # Get IDs of shorts to remove
    shorts_ids = [item['_id'] for item in shorts_content]
    
    # Delete the shorts
    delete_result = db.content.delete_many({"_id": {"$in": shorts_ids}})
    
    print(f"✅ Successfully deleted {delete_result.deleted_count} short film items")
    
    # Get final content count
    final_count = db.content.count_documents({})
    removed_count = initial_count - final_count
    
    print(f"📊 Final content count: {final_count}")
    print(f"📊 Total items removed: {removed_count}")
    
    # Verify no shorts remain
    remaining_shorts = db.content.count_documents(shorts_query)
    if remaining_shorts == 0:
        print("✅ Verification successful: No shorts remain in database")
    else:
        print(f"⚠️  Warning: {remaining_shorts} shorts still found in database")
    
    print("\n🎉 Short film cleanup completed!")

if __name__ == "__main__":
    main()