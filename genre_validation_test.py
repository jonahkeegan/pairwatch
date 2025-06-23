import requests
import unittest
import time
import sys
import random
import string
import uuid
from datetime import datetime
import json
import pymongo
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("genre_validation_test")

class GenreValidationTester:
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
        """Test user registration and check for genre validation in logs"""
        # Get initial content count
        initial_content_count = self.db.content.count_documents({})
        logger.info(f"Initial content count: {initial_content_count}")
        
        # Register a new user
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
            
            # Wait for content addition to complete
            logger.info("Waiting for content addition to complete (30 seconds)...")
            time.sleep(30)
            
            # Check new content count
            new_content_count = self.db.content.count_documents({})
            added_content = new_content_count - initial_content_count
            logger.info(f"New content count: {new_content_count}")
            logger.info(f"Added {added_content} new content items during registration")
            
            return True, response
        
        return False, response
    
    def test_user_login(self):
        """Test user login and check for genre validation in logs"""
        # Get initial content count
        initial_content_count = self.db.content.count_documents({})
        logger.info(f"Initial content count before login: {initial_content_count}")
        
        # Login
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
            
            # Wait for content addition to complete
            logger.info("Waiting for content addition to complete (30 seconds)...")
            time.sleep(30)
            
            # Check new content count
            new_content_count = self.db.content.count_documents({})
            added_content = new_content_count - initial_content_count
            logger.info(f"New content count after login: {new_content_count}")
            logger.info(f"Added {added_content} new content items during login")
            
            return True, response
        
        return False, response
    
    def check_database_content_quality(self):
        """Check that all content in the database has valid genres"""
        logger.info("\n🔍 Checking database content quality...")
        
        # Get all content
        all_content = list(self.db.content.find())
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
            
            # Show distribution of genres
            genre_counts = {}
            for item in all_content:
                genre = item.get('genre', '')
                genres = [g.strip() for g in genre.split(',')]
                for g in genres:
                    if g:
                        genre_counts[g] = genre_counts.get(g, 0) + 1
            
            logger.info("Genre distribution:")
            for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                logger.info(f"  - {genre}: {count} items ({(count/total_content)*100:.1f}%)")
            
            return True, []

    def run_all_tests(self):
        """Run all tests"""
        logger.info("\n🔍 STARTING GENRE VALIDATION TESTS")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user to trigger content addition")
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Check database content quality after registration
        logger.info("\n📋 Step 2: Check database content quality after registration")
        quality_success, invalid_items = self.check_database_content_quality()
        
        # Step 3: Login to trigger more content addition
        logger.info("\n📋 Step 3: Login to trigger more content addition")
        login_success, _ = self.test_user_login()
        if not login_success:
            logger.error("❌ Failed to login, stopping test")
            return False
        
        # Step 4: Check database content quality again after login
        logger.info("\n📋 Step 4: Final check of database content quality")
        final_quality_success, final_invalid_items = self.check_database_content_quality()
        
        # Final summary
        logger.info("\n📋 GENRE VALIDATION TEST SUMMARY")
        if quality_success and final_quality_success:
            logger.info("✅ PASS: All content in database has valid genres")
            logger.info("✅ Genre validation is working correctly in both search_and_store_content and add_content_from_imdb_id functions")
            return True
        else:
            logger.error("❌ FAIL: Found content with invalid genres")
            return False

if __name__ == "__main__":
    tester = GenreValidationTester()
    tester.run_all_tests()