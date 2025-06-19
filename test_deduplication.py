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
logger = logging.getLogger("deduplication_test")

class DeduplicationTester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        
        # Test user credentials - use existing user if specified
        self.test_user_email = "test005@yopmail.com"  # As requested in the test
        self.test_user_password = "TestPassword123!"
        self.test_user_name = "Test User 005"
        
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

    def test_user_login(self):
        """Test user login with existing account"""
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
    
    def test_user_registration(self):
        """Test user registration if login fails"""
        # Generate a unique email
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        self.test_user_email = f"test_user_{timestamp}@example.com"
        self.test_user_name = f"Test User {timestamp}"
        
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

    def test_get_recommendations(self, offset=0, limit=50):
        """Test getting recommendations with pagination"""
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False, {}
        
        success, response = self.run_test(
            f"Get Recommendations (offset={offset}, limit={limit})",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": offset, "limit": limit}
        )
        
        if success and isinstance(response, list):
            logger.info(f"✅ Received {len(response)} recommendations")
        
        return success, response

    def simulate_voting_to_threshold(self, target_votes=15):
        """Simulate voting until we reach the recommendation threshold"""
        logger.info(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes)...")
        
        # Get current vote count
        _, stats = self.run_test(
            "Get User Stats",
            "GET",
            "stats",
            200,
            auth=True
        )
        
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        logger.info(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        if votes_needed == 0:
            logger.info("✅ User already has enough votes")
            return True
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.run_test(
                "Get Voting Pair",
                "GET",
                "voting-pair",
                200,
                auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.run_test(
                "Submit Vote",
                "POST",
                "vote",
                200,
                auth=True,
                data={
                    "winner_id": pair['item1']['id'], 
                    "loser_id": pair['item2']['id'],
                    "content_type": pair['content_type']
                }
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                logger.info(f"Progress: {i+1}/{votes_needed} votes")
        
        logger.info(f"✅ Successfully completed {votes_needed} votes")
        return True

    def check_for_duplicates(self, recommendations):
        """Check for duplicate recommendations"""
        if not recommendations or not isinstance(recommendations, list):
            logger.error("❌ No recommendations to check for duplicates")
            return False
        
        # Check for duplicate content_ids
        content_ids = [rec.get('imdb_id') for rec in recommendations]
        unique_content_ids = set(content_ids)
        
        if len(content_ids) != len(unique_content_ids):
            logger.error(f"❌ Found duplicate content_ids: {len(content_ids) - len(unique_content_ids)} duplicates")
            
            # Find the duplicates
            duplicate_ids = {}
            for content_id in content_ids:
                if content_ids.count(content_id) > 1:
                    duplicate_ids[content_id] = content_ids.count(content_id)
            
            logger.error(f"Duplicate content_ids: {duplicate_ids}")
            
            # Log the duplicate recommendations
            for content_id, count in duplicate_ids.items():
                logger.error(f"Content ID {content_id} appears {count} times:")
                for i, rec in enumerate(recommendations):
                    if rec.get('imdb_id') == content_id:
                        logger.error(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
            
            return False
        else:
            logger.info(f"✅ No duplicate content_ids found in {len(content_ids)} recommendations")
        
        # Check for duplicate titles
        titles = [rec.get('title') for rec in recommendations]
        unique_titles = set(titles)
        
        if len(titles) != len(unique_titles):
            logger.error(f"❌ Found duplicate titles: {len(titles) - len(unique_titles)} duplicates")
            
            # Find the duplicates
            duplicate_titles = {}
            for title in titles:
                if titles.count(title) > 1:
                    duplicate_titles[title] = titles.count(title)
            
            logger.error(f"Duplicate titles: {duplicate_titles}")
            
            # Log the duplicate recommendations
            for title, count in duplicate_titles.items():
                logger.error(f"Title '{title}' appears {count} times:")
                for i, rec in enumerate(recommendations):
                    if rec.get('title') == title:
                        logger.error(f"  {i+1}. {rec.get('title')} - IMDB ID: {rec.get('imdb_id')} - {rec.get('reason')}")
            
            return False
        else:
            logger.info(f"✅ No duplicate titles found in {len(titles)} recommendations")
        
        return True

    def check_database_for_duplicates(self):
        """Check the database for duplicate recommendations"""
        if not self.user_id:
            logger.error("❌ No user ID available")
            return False
        
        try:
            # Get all recommendations for the user
            recommendations = list(self.db.algo_recommendations.find({"user_id": self.user_id}))
            
            if not recommendations:
                logger.error("❌ No recommendations found in database")
                return False
            
            logger.info(f"✅ Found {len(recommendations)} recommendations in database")
            
            # Check for duplicate content_ids
            content_ids = [rec["content_id"] for rec in recommendations]
            unique_content_ids = set(content_ids)
            
            if len(content_ids) != len(unique_content_ids):
                logger.error(f"❌ Found duplicate content_ids in database: {len(content_ids) - len(unique_content_ids)} duplicates")
                
                # Find the duplicates
                duplicate_ids = {}
                for content_id in content_ids:
                    if content_ids.count(content_id) > 1:
                        duplicate_ids[content_id] = content_ids.count(content_id)
                
                logger.error(f"Duplicate content_ids in database: {duplicate_ids}")
                
                # Log some of the duplicate recommendations
                for content_id, count in list(duplicate_ids.items())[:3]:  # Show first 3 duplicates
                    logger.error(f"Content ID {content_id} appears {count} times in database:")
                    duplicate_recs = [rec for rec in recommendations if rec["content_id"] == content_id]
                    for i, rec in enumerate(duplicate_recs[:3]):  # Show first 3 instances
                        content = self.db.content.find_one({"id": rec["content_id"]})
                        title = content["title"] if content else "Unknown"
                        logger.error(f"  {i+1}. {title} - Score: {rec['recommendation_score']:.2f}, Confidence: {rec['confidence']:.2f}")
                
                return False
            else:
                logger.info(f"✅ No duplicate content_ids found in database")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return False

    def test_deduplication(self):
        """Test the deduplication functionality for recommendations"""
        logger.info("\n🔍 TESTING RECOMMENDATION DEDUPLICATION")
        
        # Step 1: Login with existing user or register a new one
        logger.info("\n📋 Step 1: Login with existing user or register a new one")
        login_success, _ = self.test_user_login()
        
        if not login_success:
            logger.info("Login failed, registering a new user...")
            reg_success, _ = self.test_user_registration()
            if not reg_success:
                logger.error("❌ Failed to register user, stopping test")
                return False
        
        # Step 2: Ensure user has enough votes for recommendations
        logger.info("\n📋 Step 2: Ensure user has enough votes for recommendations")
        vote_success = self.simulate_voting_to_threshold(target_votes=15)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Get recommendations with a larger sample
        logger.info("\n📋 Step 3: Get recommendations with a larger sample (offset=0, limit=50)")
        success, recommendations = self.test_get_recommendations(offset=0, limit=50)
        
        if not success or not recommendations:
            logger.error("❌ Failed to get recommendations")
            return False
        
        # Step 4: Check for duplicates in the API response
        logger.info("\n📋 Step 4: Check for duplicates in the API response")
        api_dedup_success = self.check_for_duplicates(recommendations)
        
        # Step 5: Check for duplicates in the database
        logger.info("\n📋 Step 5: Check for duplicates in the database")
        db_dedup_success = self.check_database_for_duplicates()
        
        # Step 6: Get a second page of recommendations to check for duplicates across pages
        logger.info("\n📋 Step 6: Get a second page of recommendations (offset=50, limit=50)")
        success, second_page = self.test_get_recommendations(offset=50, limit=50)
        
        if success and second_page:
            logger.info(f"✅ Received {len(second_page)} recommendations in second page")
            
            # Check for duplicates within the second page
            logger.info("Checking for duplicates within the second page...")
            second_page_dedup_success = self.check_for_duplicates(second_page)
            
            # Check for duplicates between pages
            logger.info("Checking for duplicates between first and second page...")
            
            # Combine both pages
            all_recommendations = recommendations + second_page
            cross_page_dedup_success = self.check_for_duplicates(all_recommendations)
        else:
            logger.info("No second page of recommendations available or empty")
            second_page_dedup_success = True
            cross_page_dedup_success = True
        
        # Step 7: Check specifically for 'Rick and Morty' duplicates
        logger.info("\n📋 Step 7: Check specifically for 'Rick and Morty' duplicates")
        rick_and_morty_count = 0
        for rec in recommendations:
            if rec.get('title') == 'Rick and Morty':
                rick_and_morty_count += 1
        
        if rick_and_morty_count > 1:
            logger.error(f"❌ Found {rick_and_morty_count} instances of 'Rick and Morty'")
            for i, rec in enumerate(recommendations):
                if rec.get('title') == 'Rick and Morty':
                    logger.error(f"  {i+1}. Rick and Morty - IMDB ID: {rec.get('imdb_id')} - {rec.get('reason')}")
        else:
            logger.info(f"✅ Found {rick_and_morty_count} instances of 'Rick and Morty'")
        
        # Step 8: Final summary
        logger.info("\n📋 Step 8: Final summary of deduplication testing")
        
        if api_dedup_success and db_dedup_success and second_page_dedup_success and cross_page_dedup_success:
            logger.info("✅ PASS: Deduplication is working correctly")
            logger.info("✅ No duplicate content IDs found in API responses")
            logger.info("✅ No duplicate titles found in API responses")
            logger.info("✅ No duplicate content IDs found in database")
            return True
        else:
            logger.error("❌ FAIL: Deduplication issues found")
            if not api_dedup_success:
                logger.error("❌ Duplicate content IDs or titles found in API responses")
            if not db_dedup_success:
                logger.error("❌ Duplicate content IDs found in database")
            if not second_page_dedup_success:
                logger.error("❌ Duplicate content IDs or titles found in second page")
            if not cross_page_dedup_success:
                logger.error("❌ Duplicate content IDs or titles found between pages")
            return False

if __name__ == "__main__":
    tester = DeduplicationTester()
    tester.test_deduplication()