#!/usr/bin/env python3
"""
Check the actual database content structure to understand the field mismatch
"""

import pymongo

def check_database_structure():
    print("🔍 Checking Database Content Structure")
    print("=" * 40)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Get a sample content item
    sample_content = db.content.find_one()
    
    if sample_content:
        print("📋 Sample content item fields:")
        for field, value in sample_content.items():
            print(f"   {field}: {type(value).__name__} = {value}")
    else:
        print("❌ No content found in database")
        return
    
    print(f"\n📊 Total content items: {db.content.count_documents({})}")
    
    # Check field consistency
    print(f"\n🔍 Checking field consistency...")
    
    # Check if all items have required fields
    items_with_imdb_id = db.content.count_documents({"imdb_id": {"$exists": True, "$ne": None, "$ne": ""}})
    items_with_genre = db.content.count_documents({"genre": {"$exists": True, "$ne": None, "$ne": ""}})
    items_with_id = db.content.count_documents({"id": {"$exists": True}})
    items_with_content_id = db.content.count_documents({"content_id": {"$exists": True}})
    
    total_items = db.content.count_documents({})
    
    print(f"   Items with 'id' field: {items_with_id}/{total_items}")
    print(f"   Items with 'content_id' field: {items_with_content_id}/{total_items}")
    print(f"   Items with 'imdb_id' field: {items_with_imdb_id}/{total_items}")
    print(f"   Items with 'genre' field: {items_with_genre}/{total_items}")
    
    # Show the field mapping needed
    print(f"\n💡 ContentItem model expects:")
    print(f"   - id: str")
    print(f"   - imdb_id: str")
    print(f"   - title: str")
    print(f"   - year: str")
    print(f"   - content_type: str")
    print(f"   - genre: str")
    print(f"   - rating: Optional[str]")
    print(f"   - poster: Optional[str]")
    print(f"   - plot: Optional[str]")
    print(f"   - director: Optional[str]")
    print(f"   - actors: Optional[str]")

if __name__ == "__main__":
    check_database_structure()