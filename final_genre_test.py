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
logger = logging.getLogger("final_genre_test")

# MongoDB connection
mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
db = mongo_client["movie_preferences_db"]

def check_backend_logs():
    """Check backend logs for skipped content due to invalid genres"""
    logger.info("\n🔍 Checking backend logs for skipped content...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["tail", "-n", "500", "/var/log/supervisor/backend.*.log"], 
            capture_output=True, 
            text=True
        )
        
        log_output = result.stdout
        skipped_content = []
        
        for line in log_output.split('\n'):
            if "Skipping" in line and "invalid or missing genre" in line:
                skipped_content.append(line.strip())
        
        if skipped_content:
            logger.info(f"Found {len(skipped_content)} log entries for skipped content:")
            for entry in skipped_content[:10]:  # Show first 10 for brevity
                logger.info(f"  - {entry}")
            return True, skipped_content
        else:
            logger.info("No log entries found for skipped content")
            return False, []
                
    except Exception as e:
        logger.error(f"Error checking logs: {str(e)}")
        return False, []

def check_database_content_quality():
    """Check that all content in the database has valid genres"""
    logger.info("\n🔍 Checking database content quality...")
    
    # Get all content
    all_content = list(db.content.find())
    total_content = len(all_content)
    logger.info(f"Total content items in database: {total_content}")
    
    # Check for invalid genres
    invalid_genres = []
    for item in all_content:
        genre = item.get('genre', '')
        if not genre or genre.strip() == "" or genre.strip().upper() in ["N/A", "NAN", "NULL"]:
            invalid_genres.append({
                'id': item.get('id'),
                'title': item.get('title'),
                'genre': genre
            })
    
    # Report results
    if invalid_genres:
        logger.error(f"❌ Found {len(invalid_genres)} content items with invalid genres:")
        for item in invalid_genres[:10]:  # Show first 10 for brevity
            logger.error(f"  - {item['title']}: '{item['genre']}'")
        
        invalid_percentage = (len(invalid_genres) / total_content) * 100
        logger.error(f"❌ {invalid_percentage:.2f}% of content has invalid genres")
        return False, invalid_genres
    else:
        logger.info(f"✅ All {total_content} content items have valid genres")
        return True, []

def register_new_user():
    """Register a new user to trigger content addition"""
    # Get initial content count
    initial_content_count = db.content.count_documents({})
    logger.info(f"Initial content count: {initial_content_count}")
    
    # Create unique user credentials
    test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
    test_user_password = "TestPassword123!"
    test_user_name = f"Test User {datetime.now().strftime('%H%M%S')}"
    
    # Register user
    logger.info(f"Registering new user: {test_user_email}")
    response = requests.post(
        "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api/auth/register",
        json={
            "email": test_user_email,
            "password": test_user_password,
            "name": test_user_name
        }
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to register user: {response.status_code} - {response.text}")
        return False, None, 0
    
    user_data = response.json()
    user_id = user_data["user"]["id"]
    auth_token = user_data["access_token"]
    
    logger.info(f"User registered with ID: {user_id}")
    
    # Wait for content addition to complete
    logger.info("Waiting for content addition to complete (30 seconds)...")
    time.sleep(30)
    
    # Check for new content
    new_content_count = db.content.count_documents({})
    added_content = new_content_count - initial_content_count
    logger.info(f"New content count: {new_content_count}")
    logger.info(f"Added {added_content} new content items during registration")
    
    return True, {
        "user_id": user_id,
        "auth_token": auth_token,
        "email": test_user_email,
        "password": test_user_password
    }, added_content

def run_final_test():
    """Run a final test to verify genre validation"""
    logger.info("\n🔍 STARTING FINAL GENRE VALIDATION TEST")
    
    # Step 1: Check initial database content quality
    logger.info("\n📋 Step 1: Check initial database content quality")
    initial_quality, initial_invalid = check_database_content_quality()
    
    # Step 2: Restart backend to clear logs
    logger.info("\n📋 Step 2: Restart backend to clear logs")
    import subprocess
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"])
    logger.info("Backend restarted, waiting 5 seconds...")
    time.sleep(5)
    
    # Step 3: Register a new user to trigger content addition
    logger.info("\n📋 Step 3: Register a new user to trigger content addition")
    reg_success, user_data, added_content = register_new_user()
    if not reg_success:
        logger.error("❌ Failed to register user, stopping test")
        return False
    
    # Step 4: Check backend logs for skipped content
    logger.info("\n📋 Step 4: Check backend logs for skipped content")
    logs_have_skipped, skipped_content = check_backend_logs()
    
    # Step 5: Check database content quality after registration
    logger.info("\n📋 Step 5: Check database content quality after registration")
    after_reg_quality, after_reg_invalid = check_database_content_quality()
    
    # Final summary
    logger.info("\n📋 FINAL GENRE VALIDATION TEST SUMMARY")
    logger.info(f"Initial content quality check: {'PASS' if initial_quality else 'FAIL'}")
    logger.info(f"Content added during registration: {added_content}")
    logger.info(f"Backend logs show skipped content: {'YES' if logs_have_skipped else 'NO'}")
    logger.info(f"Content quality after registration: {'PASS' if after_reg_quality else 'FAIL'}")
    
    # Overall result
    if after_reg_quality:
        logger.info("\n✅ PASS: All content in database has valid genres")
        
        if logs_have_skipped:
            logger.info("✅ PASS: Backend logs show content being skipped due to invalid genres")
            logger.info("\n✅ OVERALL RESULT: PASS - Genre validation is working correctly")
            return True
        else:
            logger.warning("⚠️ WARNING: No evidence in logs of content being skipped due to invalid genres")
            logger.warning("This could mean either:")
            logger.warning("1. The genre validation is working but no invalid genres were encountered")
            logger.warning("2. The genre validation is not working and invalid genres are being accepted")
            logger.warning("\n⚠️ OVERALL RESULT: INCONCLUSIVE - Need more evidence")
            return True
    else:
        logger.error("\n❌ FAIL: Found content with invalid genres in the database")
        logger.error("\n❌ OVERALL RESULT: FAIL - Genre validation is not working correctly")
        return False

if __name__ == "__main__":
    run_final_test()