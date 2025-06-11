import pymongo
import sys
from datetime import datetime

def check_algo_recommendations():
    """Check the algo_recommendations collection in the database"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["movie_preferences_db"]
        
        # Check if the algo_recommendations collection exists
        if "algo_recommendations" not in db.list_collection_names():
            print("❌ algo_recommendations collection does not exist")
            return False
        
        # Get the count of recommendations
        rec_count = db.algo_recommendations.count_documents({})
        print(f"✅ Found {rec_count} recommendations in the database")
        
        # Get the most recent recommendations
        recent_recs = list(db.algo_recommendations.find().sort("created_at", -1).limit(5))
        
        if recent_recs:
            print(f"\n📋 Most recent recommendations:")
            for i, rec in enumerate(recent_recs):
                user_id = rec.get("user_id", "unknown")
                content_id = rec.get("content_id", "unknown")
                score = rec.get("recommendation_score", 0)
                confidence = rec.get("confidence", 0)
                created_at = rec.get("created_at", datetime.now())
                reasoning = rec.get("reasoning", "")
                
                # Get content details
                content = db.content.find_one({"id": content_id})
                content_title = content.get("title", "unknown") if content else "unknown"
                
                print(f"  {i+1}. User: {user_id[:8]}...")
                print(f"     Content: {content_title} (ID: {content_id[:8]}...)")
                print(f"     Score: {score:.2f}, Confidence: {confidence:.2f}")
                print(f"     Created: {created_at}")
                print(f"     Reasoning: {reasoning}")
                print()
            
            # Check if there are multiple recommendations for the same user
            user_counts = {}
            for rec in db.algo_recommendations.find():
                user_id = rec.get("user_id")
                if user_id:
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            users_with_multiple_recs = {user: count for user, count in user_counts.items() if count > 1}
            if users_with_multiple_recs:
                print(f"✅ Found users with multiple recommendations:")
                for user, count in users_with_multiple_recs.items():
                    print(f"  User {user[:8]}... has {count} recommendations")
            else:
                print("❌ No users with multiple recommendations found")
            
            return True
        else:
            print("❌ No recommendations found in the database")
            return False
    
    except Exception as e:
        print(f"❌ Error checking recommendations: {str(e)}")
        return False

if __name__ == "__main__":
    check_algo_recommendations()
    sys.exit(0)