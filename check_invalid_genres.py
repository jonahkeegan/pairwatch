import pymongo
import json

# MongoDB connection
mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
db = mongo_client["movie_preferences_db"]

# Get all content with invalid genres
invalid_content = list(db.content.find({
    "$or": [
        {"genre": "N/A"},
        {"genre": "NaN"},
        {"genre": "NULL"},
        {"genre": ""},
        {"genre": None}
    ]
}))

print(f"Found {len(invalid_content)} content items with invalid genres")

# Print details of each invalid item
for i, item in enumerate(invalid_content):
    print(f"\nItem {i+1}:")
    print(f"  ID: {item.get('id')}")
    print(f"  IMDB ID: {item.get('imdb_id')}")
    print(f"  Title: {item.get('title')}")
    print(f"  Year: {item.get('year')}")
    print(f"  Genre: '{item.get('genre')}'")
    print(f"  Content Type: {item.get('content_type')}")
    print(f"  Created At: {item.get('created_at')}")

# Check when these items were added
print("\nChecking when these items were added...")
for item in invalid_content:
    created_at = item.get('created_at')
    if created_at:
        print(f"  {item.get('title')} was added at {created_at}")