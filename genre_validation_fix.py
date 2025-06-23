import pymongo
import requests
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("genre_validation_fix")

# MongoDB connection
mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
db = mongo_client["movie_preferences_db"]

def check_invalid_genres():
    """Check for content with invalid genres in the database"""
    invalid_content = list(db.content.find({
        "$or": [
            {"genre": "N/A"},
            {"genre": "NaN"},
            {"genre": "NULL"},
            {"genre": ""},
            {"genre": None},
            {"genre": {"$regex": "^\\s+$"}}  # Just whitespace
        ]
    }))
    
    logger.info(f"Found {len(invalid_content)} content items with invalid genres")
    
    for i, item in enumerate(invalid_content):
        logger.info(f"\nItem {i+1}:")
        logger.info(f"  ID: {item.get('id')}")
        logger.info(f"  IMDB ID: {item.get('imdb_id')}")
        logger.info(f"  Title: {item.get('title')}")
        logger.info(f"  Year: {item.get('year')}")
        logger.info(f"  Genre: '{item.get('genre')}'")
        logger.info(f"  Content Type: {item.get('content_type')}")
        logger.info(f"  Created At: {item.get('created_at')}")
    
    return invalid_content

def remove_invalid_content():
    """Remove content with invalid genres from the database"""
    invalid_content = check_invalid_genres()
    
    if invalid_content:
        logger.info(f"\nRemoving {len(invalid_content)} content items with invalid genres...")
        
        for item in invalid_content:
            db.content.delete_one({"id": item.get("id")})
            logger.info(f"Removed: {item.get('title')}")
        
        logger.info("Removal complete")
    else:
        logger.info("No invalid content to remove")

def test_genre_validation():
    """Test the genre validation logic by registering a new user and monitoring content addition"""
    # Get initial content count
    initial_count = db.content.count_documents({})
    logger.info(f"Initial content count: {initial_count}")
    
    # Register a new user to trigger content addition
    base_url = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"
    
    # Create unique user credentials
    test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
    test_user_password = "TestPassword123!"
    test_user_name = f"Test User {datetime.now().strftime('%H%M%S')}"
    
    # Register user
    logger.info(f"Registering new user: {test_user_email}")
    response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": test_user_email,
            "password": test_user_password,
            "name": test_user_name
        }
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to register user: {response.status_code} - {response.text}")
        return False
    
    user_data = response.json()
    user_id = user_data["user"]["id"]
    auth_token = user_data["access_token"]
    
    logger.info(f"User registered with ID: {user_id}")
    
    # Wait for content addition to complete
    logger.info("Waiting for content addition to complete (30 seconds)...")
    time.sleep(30)
    
    # Check for new content
    new_count = db.content.count_documents({})
    added_count = new_count - initial_count
    logger.info(f"New content count: {new_count}")
    logger.info(f"Added {added_count} new content items during registration")
    
    # Check for invalid genres after registration
    logger.info("\nChecking for invalid genres after registration...")
    invalid_after_reg = check_invalid_genres()
    
    # Login to trigger more content addition
    logger.info("\nLogging in to trigger more content addition...")
    login_response = requests.post(
        f"{base_url}/auth/login",
        json={
            "email": test_user_email,
            "password": test_user_password
        }
    )
    
    if login_response.status_code != 200:
        logger.error(f"Failed to login: {login_response.status_code} - {login_response.text}")
        return False
    
    # Wait for content addition to complete
    logger.info("Waiting for content addition to complete (30 seconds)...")
    time.sleep(30)
    
    # Check for new content after login
    final_count = db.content.count_documents({})
    added_after_login = final_count - new_count
    logger.info(f"Final content count: {final_count}")
    logger.info(f"Added {added_after_login} new content items during login")
    
    # Check for invalid genres after login
    logger.info("\nChecking for invalid genres after login...")
    invalid_after_login = check_invalid_genres()
    
    # Final summary
    logger.info("\nFinal Summary:")
    logger.info(f"Initial content count: {initial_count}")
    logger.info(f"Content added during registration: {added_count}")
    logger.info(f"Content added during login: {added_after_login}")
    logger.info(f"Total content added: {added_count + added_after_login}")
    logger.info(f"Invalid content after registration: {len(invalid_after_reg)}")
    logger.info(f"Invalid content after login: {len(invalid_after_login)}")
    
    # Check if any new invalid content was added
    new_invalid = []
    if invalid_after_login:
        for item in invalid_after_login:
            created_at = item.get('created_at')
            if created_at and created_at > datetime.now().replace(hour=0, minute=0, second=0):
                new_invalid.append(item)
    
    if new_invalid:
        logger.error(f"❌ FAIL: {len(new_invalid)} new content items with invalid genres were added")
        return False
    else:
        logger.info("✅ PASS: No new content items with invalid genres were added")
        return True

if __name__ == "__main__":
    logger.info("Starting genre validation test and fix")
    
    # First, check for existing invalid content
    logger.info("\nChecking for existing invalid content...")
    existing_invalid = check_invalid_genres()
    
    # Remove invalid content if found
    if existing_invalid:
        remove_invalid_content()
    
    # Test genre validation logic
    logger.info("\nTesting genre validation logic...")
    test_result = test_genre_validation()
    
    # Final check
    logger.info("\nFinal check for invalid content...")
    final_invalid = check_invalid_genres()
    
    if not final_invalid and test_result:
        logger.info("\n✅ OVERALL RESULT: PASS - Genre validation is working correctly")
    else:
        logger.error("\n❌ OVERALL RESULT: FAIL - Issues found with genre validation")