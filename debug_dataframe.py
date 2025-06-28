#!/usr/bin/env python3
"""
Debug the DataFrame creation and content conversion process
"""

import asyncio
import sys
import os
import pymongo

# Add the backend directory to the path
sys.path.append('/app/backend')

async def debug_dataframe_conversion():
    print("🔍 Debugging DataFrame Content Conversion")
    print("=" * 50)
    
    # Import the backend functions
    try:
        from server import _get_all_content_items_as_df, _dataframe_row_to_content_item, db
    except ImportError as e:
        print(f"❌ Failed to import backend functions: {e}")
        return False
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = mongo_client["movie_preferences_db"]
    
    # Get a sample content item from database
    sample_content = local_db.content.find_one({"title": "Tenet"})
    
    if sample_content:
        print(f"📋 Sample content from database:")
        print(f"   Title: {sample_content.get('title', 'Unknown')}")
        print(f"   Year: {sample_content.get('year', 'Unknown')}")
        print(f"   Poster URL: {sample_content.get('poster', 'None')}")
        print(f"   Poster exists: {bool(sample_content.get('poster'))}")
        
        if sample_content.get('poster'):
            print(f"   Poster length: {len(sample_content.get('poster'))}")
    else:
        print("❌ No sample content found")
        return False
    
    # Test DataFrame creation
    print(f"\n🔍 Testing DataFrame creation...")
    
    try:
        all_content_df = await _get_all_content_items_as_df(db)
        print(f"   DataFrame shape: {all_content_df.shape}")
        print(f"   DataFrame columns: {list(all_content_df.columns)}")
        
        # Check if poster column exists
        if 'poster' in all_content_df.columns:
            print(f"   ✅ Poster column exists in DataFrame")
            
            # Check sample rows
            tenet_rows = all_content_df[all_content_df['title'] == 'Tenet']
            if not tenet_rows.empty:
                tenet_row = tenet_rows.iloc[0]
                print(f"   Tenet poster in DataFrame: {tenet_row.get('poster', 'NOT FOUND')}")
                print(f"   Tenet row columns: {list(tenet_row.index)}")
                
                # Test conversion back to ContentItem
                print(f"\n🔧 Testing conversion back to ContentItem...")
                row_dict = tenet_row.to_dict()
                content_item_dict = _dataframe_row_to_content_item(row_dict)
                
                print(f"   Converted poster: {content_item_dict.get('poster', 'NOT FOUND')}")
                print(f"   All converted fields: {list(content_item_dict.keys())}")
                
            else:
                print(f"   ❌ Tenet not found in DataFrame")
        else:
            print(f"   ❌ No poster column in DataFrame")
            print(f"   Available columns: {list(all_content_df.columns)}")
        
    except Exception as e:
        print(f"❌ Error testing DataFrame: {e}")
        import traceback
        traceback.print_exc()
    
    return True

async def main():
    try:
        await debug_dataframe_conversion()
    except Exception as e:
        print(f"❌ Error during debugging: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())