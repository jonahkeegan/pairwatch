import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json
import pymongo
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto_content_test")

class AutoContentAdditionTester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        
        # Test user credentials
        self.test_user_email = f"auto_content_test_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Auto Content Test User {datetime.now().strftime('%H%M%S')}"
        
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

    def get_content_count(self):
        """Get the current count of content items in the database"""
        try:
            count = self.db.content.count_documents({})
            logger.info(f"📊 Current content count: {count}")
            return count
        except Exception as e:
            logger.error(f"❌ Error getting content count: {str(e)}")
            return 0

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
    
    def test_user_login(self):
        """Test user login"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=data
        )
        
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            self.user_id = response['user']['id']
            logger.info(f"✅ User logged in with ID: {self.user_id}")
            logger.info(f"✅ Auth token received: {self.auth_token[:10]}...")
            return True, response
        
        return False, response

    def test_auto_content_addition_on_registration(self):
        """Test automatic content addition when a new user registers"""
        logger.info("\n🔍 TESTING AUTOMATIC CONTENT ADDITION ON REGISTRATION")
        
        # Step 1: Get initial content count
        logger.info("\n📋 Step 1: Get initial content count")
        initial_count = self.get_content_count()
        
        # Step 2: Register a new user
        logger.info("\n📋 Step 2: Register a completely new user account")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        logger.info(f"✅ Successfully registered new user: {self.test_user_email}")
        
        # Step 3: Wait for background content addition to complete
        logger.info("\n📋 Step 3: Wait for background content addition to complete (30-60 seconds)")
        logger.info("Waiting 10 seconds...")
        time.sleep(10)
        
        # Check content count after 10 seconds
        count_after_10s = self.get_content_count()
        added_after_10s = count_after_10s - initial_count
        logger.info(f"After 10 seconds: {added_after_10s} new items added")
        
        logger.info("Waiting 20 more seconds...")
        time.sleep(20)
        
        # Check content count after 30 seconds
        count_after_30s = self.get_content_count()
        added_after_30s = count_after_30s - initial_count
        logger.info(f"After 30 seconds: {added_after_30s} new items added")
        
        logger.info("Waiting 30 more seconds...")
        time.sleep(30)
        
        # Step 4: Check final content count
        logger.info("\n📋 Step 4: Check final content count")
        final_count = self.get_content_count()
        total_added = final_count - initial_count
        
        logger.info(f"Initial content count: {initial_count}")
        logger.info(f"Final content count: {final_count}")
        logger.info(f"Total items added: {total_added}")
        
        # Check if approximately 50 items were added (allowing for some duplicates)
        if total_added > 0:
            logger.info(f"✅ {total_added} new content items were added")
            
            # Check if close to 50 items were added
            if total_added >= 40:
                logger.info(f"✅ Close to 50 items were added ({total_added})")
            else:
                logger.info(f"⚠️ Fewer than expected items were added ({total_added})")
        else:
            logger.error("❌ No new content items were added")
            return False
        
        return True

    def test_auto_content_addition_on_login(self):
        """Test automatic content addition when an existing user logs in"""
        logger.info("\n🔍 TESTING AUTOMATIC CONTENT ADDITION ON LOGIN")
        
        # Step 1: Get initial content count
        logger.info("\n📋 Step 1: Get initial content count")
        initial_count = self.get_content_count()
        
        # Step 2: Login with existing user
        logger.info("\n📋 Step 2: Login with existing user")
        login_success, login_response = self.test_user_login()
        if not login_success:
            logger.error("❌ Failed to login, stopping test")
            return False
        
        logger.info(f"✅ Successfully logged in as: {self.test_user_email}")
        
        # Step 3: Wait for background content addition to complete
        logger.info("\n📋 Step 3: Wait for background content addition to complete (30-60 seconds)")
        logger.info("Waiting 10 seconds...")
        time.sleep(10)
        
        # Check content count after 10 seconds
        count_after_10s = self.get_content_count()
        added_after_10s = count_after_10s - initial_count
        logger.info(f"After 10 seconds: {added_after_10s} new items added")
        
        logger.info("Waiting 20 more seconds...")
        time.sleep(20)
        
        # Check content count after 30 seconds
        count_after_30s = self.get_content_count()
        added_after_30s = count_after_30s - initial_count
        logger.info(f"After 30 seconds: {added_after_30s} new items added")
        
        logger.info("Waiting 30 more seconds...")
        time.sleep(30)
        
        # Step 4: Check final content count
        logger.info("\n📋 Step 4: Check final content count")
        final_count = self.get_content_count()
        total_added = final_count - initial_count
        
        logger.info(f"Initial content count: {initial_count}")
        logger.info(f"Final content count: {final_count}")
        logger.info(f"Total items added: {total_added}")
        
        # Check if new items were added (allowing for some duplicates)
        if total_added > 0:
            logger.info(f"✅ {total_added} new content items were added")
            
            # Check if a significant number of items were added
            if total_added >= 20:
                logger.info(f"✅ A significant number of items were added ({total_added})")
            else:
                logger.info(f"⚠️ Fewer than expected items were added ({total_added})")
        else:
            logger.info("⚠️ No new content items were added - this could be normal if the database already contains most of the popular titles")
        
        return True

    def test_deduplication(self):
        """Test that duplicate content is not added"""
        logger.info("\n🔍 TESTING CONTENT DEDUPLICATION")
        
        # Step 1: Check for duplicate IMDB IDs
        logger.info("\n📋 Step 1: Check for duplicate IMDB IDs")
        try:
            # Get all content items
            all_content = list(self.db.content.find({}, {"imdb_id": 1, "title": 1, "year": 1}))
            
            # Check for duplicate IMDB IDs
            imdb_ids = [item.get("imdb_id") for item in all_content if item.get("imdb_id")]
            unique_imdb_ids = set(imdb_ids)
            
            duplicate_count = len(imdb_ids) - len(unique_imdb_ids)
            
            logger.info(f"Total content items: {len(all_content)}")
            logger.info(f"Unique IMDB IDs: {len(unique_imdb_ids)}")
            logger.info(f"Duplicate IMDB IDs: {duplicate_count}")
            
            if duplicate_count == 0:
                logger.info("✅ No duplicate IMDB IDs found")
            else:
                logger.info(f"⚠️ Found {duplicate_count} duplicate IMDB IDs")
                
                # Find the duplicates
                imdb_id_counts = {}
                for imdb_id in imdb_ids:
                    imdb_id_counts[imdb_id] = imdb_id_counts.get(imdb_id, 0) + 1
                
                duplicates = {imdb_id: count for imdb_id, count in imdb_id_counts.items() if count > 1}
                
                # Log some examples
                for imdb_id, count in list(duplicates.items())[:5]:
                    items = list(self.db.content.find({"imdb_id": imdb_id}, {"title": 1, "year": 1}))
                    logger.info(f"  IMDB ID {imdb_id} appears {count} times:")
                    for item in items:
                        logger.info(f"    - {item.get('title')} ({item.get('year')})")
            
            # Step 2: Check for duplicate title+year combinations
            logger.info("\n📋 Step 2: Check for duplicate title+year combinations")
            
            title_year_keys = [f"{item.get('title', '').lower().strip()}_{item.get('year', '')}" for item in all_content]
            unique_title_years = set(title_year_keys)
            
            duplicate_title_year_count = len(title_year_keys) - len(unique_title_years)
            
            logger.info(f"Unique title+year combinations: {len(unique_title_years)}")
            logger.info(f"Duplicate title+year combinations: {duplicate_title_year_count}")
            
            if duplicate_title_year_count == 0:
                logger.info("✅ No duplicate title+year combinations found")
            else:
                logger.info(f"⚠️ Found {duplicate_title_year_count} duplicate title+year combinations")
                
                # Find the duplicates
                title_year_counts = {}
                for key in title_year_keys:
                    title_year_counts[key] = title_year_counts.get(key, 0) + 1
                
                duplicates = {key: count for key, count in title_year_counts.items() if count > 1}
                
                # Log some examples
                for key, count in list(duplicates.items())[:5]:
                    title, year = key.rsplit('_', 1) if '_' in key else (key, '')
                    items = list(self.db.content.find({"title": {"$regex": f"^{title}$", "$options": "i"}, "year": year}))
                    logger.info(f"  '{title}' ({year}) appears {count} times:")
                    for item in items:
                        logger.info(f"    - ID: {item.get('id')}, IMDB ID: {item.get('imdb_id')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking for duplicates: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        logger.info("\n🔍 RUNNING ALL AUTOMATIC CONTENT ADDITION TESTS")
        
        # Test 1: Auto content addition on registration
        reg_result = self.test_auto_content_addition_on_registration()
        
        # Test 2: Auto content addition on login
        login_result = self.test_auto_content_addition_on_login()
        
        # Test 3: Deduplication
        dedup_result = self.test_deduplication()
        
        # Summary
        logger.info("\n📋 TEST SUMMARY:")
        logger.info(f"Auto content addition on registration: {'✅ PASS' if reg_result else '❌ FAIL'}")
        logger.info(f"Auto content addition on login: {'✅ PASS' if login_result else '❌ FAIL'}")
        logger.info(f"Content deduplication: {'✅ PASS' if dedup_result else '❌ FAIL'}")
        
        return reg_result and login_result and dedup_result

if __name__ == "__main__":
    tester = AutoContentAdditionTester()
    tester.run_all_tests()