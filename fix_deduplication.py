import pymongo
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deduplication_fix")

def fix_deduplication_issue():
    """Fix the deduplication issue in the database"""
    logger.info("\n🔧 FIXING DEDUPLICATION ISSUE")
    
    # Connect to MongoDB
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Get all users with recommendations
    users = db.algo_recommendations.distinct("user_id")
    logger.info(f"Found {len(users)} users with recommendations")
    
    fixed_count = 0
    
    for user_id in users:
        # Get all recommendations for the user
        recommendations = list(db.algo_recommendations.find({"user_id": user_id}))
        
        if not recommendations:
            continue
        
        logger.info(f"User {user_id} has {len(recommendations)} recommendations")
        
        # Check for duplicate content_ids
        content_ids = [rec["content_id"] for rec in recommendations]
        unique_content_ids = set(content_ids)
        
        if len(content_ids) != len(unique_content_ids):
            duplicate_count = len(content_ids) - len(unique_content_ids)
            logger.info(f"Found {duplicate_count} duplicates for user {user_id}")
            
            # Keep only the highest scored recommendation for each content_id
            content_id_to_best_rec = {}
            
            for rec in recommendations:
                content_id = rec["content_id"]
                if content_id not in content_id_to_best_rec or rec["recommendation_score"] > content_id_to_best_rec[content_id]["recommendation_score"]:
                    content_id_to_best_rec[content_id] = rec
            
            # Delete all recommendations for this user
            db.algo_recommendations.delete_many({"user_id": user_id})
            
            # Insert only the unique recommendations
            for rec in content_id_to_best_rec.values():
                # Remove _id field to avoid duplicate key error
                if "_id" in rec:
                    del rec["_id"]
                db.algo_recommendations.insert_one(rec)
            
            logger.info(f"Fixed duplicates for user {user_id}: Kept {len(content_id_to_best_rec)} unique recommendations")
            fixed_count += 1
    
    logger.info(f"Fixed duplicates for {fixed_count} users")
    return fixed_count

if __name__ == "__main__":
    fix_deduplication_issue()