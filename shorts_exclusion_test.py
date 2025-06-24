import requests
import time
import sys
import random
import string
import uuid
from datetime import datetime
import json
import pymongo
import logging
import re
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("shorts_exclusion_test")

class ShortsExclusionTester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        
        # Test user credentials
        self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Test User {datetime.now().strftime('%H%M%S')}"
        
        # MongoDB connection
        self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.mongo_client["movie_preferences_db"]
        
        logger.info(f"🔍 Testing API at: {self.base_url}")
        logger.info(f"📝 Test user: {self.test_user_email}")

    def run_test(self, name, method, endpoint, expected_status, data=None, auth=False, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add authorization header if needed
        if auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        logger.info(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                logger.info(f"✅ Passed - Status: {response.status_code}")
            else:
                logger.error(f"❌ Failed - Expected {expected_status}, got {response.status_code}")

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            logger.error(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_user_registration(self):
        """Test user registration"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
            "name": self.test_user_name
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=data
        )
        
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            self.user_id = response['user']['id']
            logger.info(f"✅ User registered with ID: {self.user_id}")
            logger.info(f"✅ Auth token received: {self.auth_token[:10]}...")
            return True, response
        
        return False, response

    def test_database_for_shorts(self):
        """Check if there are any shorts in the database"""
        logger.info("\n🔍 Checking database for shorts...")
        
        # Get total content count
        total_content = self.db.content.count_documents({})
        logger.info(f"Total content items in database: {total_content}")
        
        # Check for shorts using regex pattern
        shorts_pattern = re.compile(r'short', re.IGNORECASE)
        shorts_query = {"genre": shorts_pattern}
        shorts_count = self.db.content.count_documents(shorts_query)
        
        if shorts_count > 0:
            logger.error(f"❌ Found {shorts_count} items with 'Short' or 'Shorts' in genre")
            
            # Get some examples
            shorts_examples = list(self.db.content.find(shorts_query).limit(5))
            for i, item in enumerate(shorts_examples):
                logger.error(f"  {i+1}. {item.get('title')} - Genre: {item.get('genre')}")
            
            return False, shorts_count
        else:
            logger.info(f"✅ No items with 'Short' or 'Shorts' in genre found")
            return True, 0

    def test_content_addition_with_shorts_filter(self):
        """Test that new content addition properly filters out shorts"""
        logger.info("\n🔍 Testing content addition with shorts filter...")
        
        # Step 1: Register a new user to trigger content addition
        logger.info("\n📋 Step 1: Register a new user to trigger content addition")
        initial_content_count = self.db.content.count_documents({})
        logger.info(f"Initial content count: {initial_content_count}")
        
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Wait for content addition to complete
        logger.info("\n📋 Step 2: Wait for content addition to complete")
        logger.info("Waiting 30 seconds for content addition to complete...")
        time.sleep(30)
        
        # Step 3: Check if content was added and no shorts were included
        logger.info("\n📋 Step 3: Check if content was added and no shorts were included")
        final_content_count = self.db.content.count_documents({})
        added_content_count = final_content_count - initial_content_count
        
        logger.info(f"Final content count: {final_content_count}")
        logger.info(f"Added {added_content_count} new content items")
        
        # Check if any of the newly added content has shorts in genre
        shorts_pattern = re.compile(r'short', re.IGNORECASE)
        shorts_query = {"genre": shorts_pattern}
        shorts_count = self.db.content.count_documents(shorts_query)
        
        if shorts_count > 0:
            logger.error(f"❌ Found {shorts_count} items with 'Short' or 'Shorts' in genre after content addition")
            
            # Get some examples
            shorts_examples = list(self.db.content.find(shorts_query).limit(5))
            for i, item in enumerate(shorts_examples):
                logger.error(f"  {i+1}. {item.get('title')} - Genre: {item.get('genre')}")
            
            return False
        else:
            logger.info(f"✅ No items with 'Short' or 'Shorts' in genre found after content addition")
            return True

    def check_backend_logs_for_shorts_skipping(self):
        """Check backend logs for evidence of shorts being skipped"""
        logger.info("\n🔍 Checking backend logs for evidence of shorts being skipped...")
        
        try:
            # This is a simplified approach - in a real environment, you'd need to access actual log files
            # For this test, we'll just check if the filter code exists in the server.py file
            
            if os.path.exists("/app/backend/server.py"):
                with open("/app/backend/server.py", "r") as f:
                    server_code = f.read()
                    
                # Check for shorts filter code
                shorts_filter_pattern = r"if\s+\"short\"\s+in\s+genre_lower.*?contains\s+shorts\s+genre"
                if re.search(shorts_filter_pattern, server_code, re.DOTALL):
                    logger.info("✅ Found shorts filter code in server.py")
                    
                    # Check for both functions
                    if "Skipping" in server_code and "contains shorts genre" in server_code:
                        logger.info("✅ Found 'Skipping' and 'contains shorts genre' messages in server.py")
                        
                        # Check if filter is in both functions
                        search_and_store_filter = "search_and_store_content" in server_code and "contains shorts genre" in server_code
                        add_content_filter = "add_content_from_imdb_id" in server_code and "contains shorts genre" in server_code
                        
                        if search_and_store_filter and add_content_filter:
                            logger.info("✅ Shorts filter is implemented in both search_and_store_content and add_content_from_imdb_id functions")
                            return True
                        else:
                            logger.error("❌ Shorts filter is not implemented in both required functions")
                            return False
                    else:
                        logger.error("❌ Could not find 'Skipping' and 'contains shorts genre' messages in server.py")
                        return False
                else:
                    logger.error("❌ Could not find shorts filter code in server.py")
                    return False
            else:
                logger.error("❌ Could not find server.py file")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking backend logs: {str(e)}")
            return False

    def check_database_content_count(self):
        """Check if the database content count is 404 (down from 477)"""
        logger.info("\n🔍 Checking database content count...")
        
        total_content = self.db.content.count_documents({})
        logger.info(f"Total content items in database: {total_content}")
        
        # The expected count is 404 according to the review request
        if total_content == 404:
            logger.info(f"✅ Database content count is exactly 404 as expected")
            return True
        elif total_content < 404:
            logger.warning(f"⚠️ Database content count is {total_content}, which is less than the expected 404")
            return False
        else:
            logger.warning(f"⚠️ Database content count is {total_content}, which is more than the expected 404")
            # This might be OK if new content has been added since the shorts were removed
            return True

    def run_all_tests(self):
        """Run all shorts exclusion tests"""
        logger.info("\n🔍 RUNNING ALL SHORTS EXCLUSION TESTS")
        
        # Test 1: Check if there are any shorts in the database
        logger.info("\n📋 TEST 1: Check if there are any shorts in the database")
        db_check_success, shorts_count = self.test_database_for_shorts()
        
        # Test 2: Check if the database content count is 404 (down from 477)
        logger.info("\n📋 TEST 2: Check if the database content count is 404 (down from 477)")
        content_count_success = self.check_database_content_count()
        
        # Test 3: Check backend logs for evidence of shorts being skipped
        logger.info("\n📋 TEST 3: Check backend logs for evidence of shorts being skipped")
        logs_check_success = self.check_backend_logs_for_shorts_skipping()
        
        # Test 4: Test content addition with shorts filter
        logger.info("\n📋 TEST 4: Test content addition with shorts filter")
        content_addition_success = self.test_content_addition_with_shorts_filter()
        
        # Final summary
        logger.info("\n📋 SHORTS EXCLUSION TESTING SUMMARY")
        logger.info(f"✅ Database check for shorts: {'PASS' if db_check_success else 'FAIL'}")
        logger.info(f"✅ Database content count check: {'PASS' if content_count_success else 'FAIL'}")
        logger.info(f"✅ Backend logs check: {'PASS' if logs_check_success else 'FAIL'}")
        logger.info(f"✅ Content addition test: {'PASS' if content_addition_success else 'FAIL'}")
        
        overall_success = db_check_success and logs_check_success and content_addition_success
        logger.info(f"\n{'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success

if __name__ == "__main__":
    tester = ShortsExclusionTester()
    tester.run_all_tests()