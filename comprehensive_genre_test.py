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
logger = logging.getLogger("comprehensive_genre_test")

class GenreValidationComprehensiveTester:
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
            
            return True, response, added_content
        
        return False, response, 0
    
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
            
            return True, response, added_content
        
        return False, response, 0
    
    def check_backend_logs(self):
        """Check backend logs for skipped content due to invalid genres"""
        logger.info("\n🔍 Checking backend logs for skipped content...")
        
        try:
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "200", "/var/log/supervisor/backend.*.log"], 
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
    
    def analyze_content_quality(self):
        """Analyze the quality of content in the database"""
        logger.info("\n🔍 Analyzing content quality...")
        
        # Get all content
        all_content = list(self.db.content.find())
        total_content = len(all_content)
        
        # Check for completeness of data
        complete_data_count = 0
        missing_fields = {
            'imdb_id': 0,
            'title': 0,
            'year': 0,
            'genre': 0,
            'rating': 0,
            'poster': 0,
            'plot': 0,
            'director': 0,
            'actors': 0
        }
        
        content_types = {'movie': 0, 'series': 0, 'other': 0}
        
        for item in all_content:
            # Check content type
            content_type = item.get('content_type', 'other')
            if content_type in content_types:
                content_types[content_type] += 1
            else:
                content_types['other'] += 1
            
            # Check for missing fields
            has_all_fields = True
            for field in missing_fields.keys():
                if field not in item or not item[field]:
                    missing_fields[field] += 1
                    has_all_fields = False
            
            if has_all_fields:
                complete_data_count += 1
        
        # Calculate percentages
        complete_percentage = (complete_data_count / total_content) * 100
        
        # Report results
        logger.info(f"Total content items: {total_content}")
        logger.info(f"Content with complete data: {complete_data_count} ({complete_percentage:.1f}%)")
        
        logger.info("Content types:")
        for content_type, count in content_types.items():
            percentage = (count / total_content) * 100
            logger.info(f"  - {content_type}: {count} ({percentage:.1f}%)")
        
        logger.info("Missing fields:")
        for field, count in missing_fields.items():
            percentage = (count / total_content) * 100
            logger.info(f"  - {field}: {count} ({percentage:.1f}%)")
        
        return {
            'total_content': total_content,
            'complete_data': complete_data_count,
            'complete_percentage': complete_percentage,
            'content_types': content_types,
            'missing_fields': missing_fields
        }
    
    def run_comprehensive_test(self):
        """Run a comprehensive test of the genre validation logic"""
        logger.info("\n🔍 STARTING COMPREHENSIVE GENRE VALIDATION TEST")
        
        # Step 1: Check initial database content quality
        logger.info("\n📋 Step 1: Check initial database content quality")
        initial_quality, initial_invalid = self.check_database_content_quality()
        
        # Step 2: Register a new user to trigger content addition
        logger.info("\n📋 Step 2: Register a new user to trigger content addition")
        reg_success, reg_response, reg_added = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 3: Check database content quality after registration
        logger.info("\n📋 Step 3: Check database content quality after registration")
        after_reg_quality, after_reg_invalid = self.check_database_content_quality()
        
        # Step 4: Check backend logs for skipped content
        logger.info("\n📋 Step 4: Check backend logs for skipped content")
        logs_have_skipped, skipped_content = self.check_backend_logs()
        
        # Step 5: Login to trigger more content addition
        logger.info("\n📋 Step 5: Login to trigger more content addition")
        login_success, login_response, login_added = self.test_user_login()
        if not login_success:
            logger.error("❌ Failed to login, stopping test")
            return False
        
        # Step 6: Check database content quality after login
        logger.info("\n📋 Step 6: Check database content quality after login")
        after_login_quality, after_login_invalid = self.check_database_content_quality()
        
        # Step 7: Analyze content quality
        logger.info("\n📋 Step 7: Analyze content quality")
        quality_analysis = self.analyze_content_quality()
        
        # Final summary
        logger.info("\n📋 COMPREHENSIVE GENRE VALIDATION TEST SUMMARY")
        logger.info(f"Initial content quality check: {'PASS' if initial_quality else 'FAIL'}")
        logger.info(f"Content added during registration: {reg_added}")
        logger.info(f"Content quality after registration: {'PASS' if after_reg_quality else 'FAIL'}")
        logger.info(f"Backend logs show skipped content: {'YES' if logs_have_skipped else 'NO'}")
        logger.info(f"Content added during login: {login_added}")
        logger.info(f"Content quality after login: {'PASS' if after_login_quality else 'FAIL'}")
        logger.info(f"Total content in database: {quality_analysis['total_content']}")
        logger.info(f"Content with complete data: {quality_analysis['complete_data']} ({quality_analysis['complete_percentage']:.1f}%)")
        
        # Overall result
        if after_login_quality and logs_have_skipped:
            logger.info("\n✅ OVERALL RESULT: PASS - Genre validation is working correctly")
            logger.info("✅ All content in database has valid genres")
            logger.info("✅ Backend logs show content being skipped due to invalid genres")
            logger.info("✅ New content added during registration and login has valid genres")
            return True
        else:
            logger.error("\n❌ OVERALL RESULT: FAIL - Issues found with genre validation")
            if not after_login_quality:
                logger.error("❌ Found content with invalid genres in the database")
            if not logs_have_skipped:
                logger.error("❌ No evidence in logs of content being skipped due to invalid genres")
            return False

if __name__ == "__main__":
    tester = GenreValidationComprehensiveTester()
    tester.run_comprehensive_test()