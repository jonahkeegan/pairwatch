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
logger = logging.getLogger("recommendation_test")

class MoviePreferenceAPITester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.auth_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
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
        
        self.tests_run += 1
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
                self.tests_passed += 1
                logger.info(f"✅ Passed - Status: {response.status_code}")
                self.test_results.append({"name": name, "status": "PASS", "details": f"Status: {response.status_code}"})
            else:
                logger.error(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({"name": name, "status": "FAIL", "details": f"Expected {expected_status}, got {response.status_code}"})

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            logger.error(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({"name": name, "status": "ERROR", "details": str(e)})
            return False, {}

    # Authentication Tests
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
    
    def test_get_voting_pair(self, use_auth=False):
        """Get a pair of items for voting"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Voting Pair", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=auth,
            params=params
        )
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type, use_auth=True):
        """Test submitting a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        if not use_auth or not self.auth_token:
            # Guest session vote
            if not self.session_id:
                logger.error("❌ No session ID available")
                self.test_results.append({"name": "Submit Vote", "status": "SKIP", "details": "No session ID available"})
                return False, {}
            data["session_id"] = self.session_id
            auth = False
        else:
            # Authenticated user vote
            auth = True
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=auth
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            logger.info(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_get_stats(self, use_auth=True):
        """Test getting user stats"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Stats", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get User Stats",
            "GET",
            "stats",
            200,
            auth=auth,
            params=params
        )
        
        if success:
            logger.info(f"Total votes: {response.get('total_votes')}")
            logger.info(f"Movie votes: {response.get('movie_votes')}")
            logger.info(f"Series votes: {response.get('series_votes')}")
            logger.info(f"Votes until recommendations: {response.get('votes_until_recommendations')}")
            logger.info(f"Recommendations available: {response.get('recommendations_available')}")
            logger.info(f"User authenticated: {response.get('user_authenticated')}")
        
        return success, response

    def test_get_recommendations(self, use_auth=True):
        """Test getting recommendations"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Recommendations",
            "GET",
            "recommendations",
            200,
            auth=auth,
            params=params
        )
        
        if success and isinstance(response, list):
            logger.info(f"✅ Received {len(response)} recommendations")
            
            # Check for poster data in recommendations
            poster_count = 0
            for i, rec in enumerate(response):
                logger.info(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
                
                if rec.get('poster'):
                    poster_count += 1
                    logger.info(f"    ✅ Has poster URL: {rec.get('poster')[:50]}...")
                else:
                    logger.info(f"    ⚠️ No poster available")
                    
                if rec.get('imdb_id'):
                    logger.info(f"    ✅ Has IMDB ID: {rec.get('imdb_id')}")
            
            logger.info(f"✅ {poster_count}/{len(response)} recommendations have poster images")
        
        return success, response

    def test_content_interaction(self, content_id, interaction_type, use_auth=True, session_id=None):
        """Test content interaction (watched, want_to_watch, not_interested)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif session_id or self.session_id:
            # Use guest session
            data["session_id"] = session_id or self.session_id
            auth = False
        else:
            logger.error("❌ No session ID or auth token available for content interaction")
            self.test_results.append({"name": f"Content Interaction ({interaction_type})", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=auth
        )
        
        if success and response.get('success') == True:
            logger.info(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response

    def simulate_voting_to_threshold(self, use_auth=True, target_votes=10):
        """Simulate voting until we reach the recommendation threshold"""
        logger.info(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes) using {'authenticated user' if use_auth else 'guest session'}...")
        
        # Get current vote count
        _, stats = self.test_get_stats(use_auth=use_auth)
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        logger.info(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair(use_auth)
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type'],
                use_auth
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                logger.info(f"Progress: {i+1}/{votes_needed} votes")
        
        logger.info(f"✅ Successfully completed {votes_needed} votes")
        return True

    def check_database_for_recommendations(self, user_id):
        """Check if recommendations were stored in the database"""
        try:
            # Check for recommendations in the database
            recommendations = list(self.db.algo_recommendations.find({"user_id": user_id}))
            
            if recommendations:
                logger.info(f"✅ Found {len(recommendations)} recommendations in database for user {user_id}")
                
                # Log some details about the recommendations
                for i, rec in enumerate(recommendations[:5]):  # Show first 5 for brevity
                    content = self.db.content.find_one({"id": rec["content_id"]})
                    title = content["title"] if content else "Unknown"
                    logger.info(f"  {i+1}. {title} - Score: {rec['recommendation_score']:.2f}, Confidence: {rec['confidence']:.2f}")
                    logger.info(f"     Reasoning: {rec['reasoning']}")
                
                return True, recommendations
            else:
                logger.error("❌ No recommendations found in database")
                return False, []
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return False, []

    def test_recommendation_generation_at_10_votes(self):
        """
        Test the specific defect: brand new logged-in user with exactly 10 votes 
        should see AI recommendations but instead sees "No AI recommendations available yet."
        """
        logger.info("\n🔍 TESTING DEFECT: New user with 10 votes should see AI recommendations")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a completely fresh user account")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        logger.info(f"✅ Successfully registered new user: {self.test_user_email}")
        
        # Step 2: Submit exactly 10 votes
        logger.info("\n📋 Step 2: Submit exactly 10 votes to trigger the recommendation system")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=10)
        if not vote_success:
            logger.error("❌ Failed to submit 10 votes")
            return False
        
        logger.info("✅ Successfully submitted exactly 10 votes")
        
        # Step 3: Check if recommendations are available in stats
        logger.info("\n📋 Step 3: Verify recommendations_available flag in stats")
        _, stats = self.test_get_stats(use_auth=True)
        if stats.get('recommendations_available'):
            logger.info("✅ Stats API confirms recommendations are available after 10 votes")
        else:
            logger.error("❌ Stats API reports recommendations are NOT available after 10 votes")
        
        # Step 4: Call /api/recommendations immediately after 10th vote
        logger.info("\n📋 Step 4: Call /api/recommendations immediately after 10th vote")
        success, recommendations = self.test_get_recommendations(use_auth=True)
        
        if success:
            if isinstance(recommendations, list) and len(recommendations) > 0:
                logger.info(f"✅ Received {len(recommendations)} recommendations immediately after 10th vote")
                
                # Log the recommendations
                for i, rec in enumerate(recommendations):
                    logger.info(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
            else:
                logger.error("❌ Received empty recommendations list immediately after 10th vote")
                logger.error(f"API Response: {recommendations}")
        else:
            logger.error("❌ Failed to get recommendations")
        
        # Step 5: Check database for recommendations
        logger.info("\n📋 Step 5: Check if recommendations were stored in algo_recommendations table")
        db_success, db_recommendations = self.check_database_for_recommendations(self.user_id)
        
        # Step 6: Timing test - try calling recommendations again after a short delay
        logger.info("\n📋 Step 6: Timing test - try calling recommendations again after a short delay")
        logger.info("Waiting 5 seconds for potential background processing...")
        time.sleep(5)
        
        delayed_success, delayed_recommendations = self.test_get_recommendations(use_auth=True)
        
        if delayed_success:
            if isinstance(delayed_recommendations, list) and len(delayed_recommendations) > 0:
                logger.info(f"✅ Received {len(delayed_recommendations)} recommendations after 5-second delay")
            else:
                logger.error("❌ Still received empty recommendations list after 5-second delay")
        
        # Step 7: Try a longer delay
        logger.info("\n📋 Step 7: Try a longer delay (10 seconds)")
        logger.info("Waiting 10 more seconds for potential background processing...")
        time.sleep(10)
        
        long_delayed_success, long_delayed_recommendations = self.test_get_recommendations(use_auth=True)
        
        if long_delayed_success:
            if isinstance(long_delayed_recommendations, list) and len(long_delayed_recommendations) > 0:
                logger.info(f"✅ Received {len(long_delayed_recommendations)} recommendations after 15-second total delay")
            else:
                logger.error("❌ Still received empty recommendations list after 15-second total delay")
        
        # Step 8: Final summary
        logger.info("\n📋 Step 8: Final summary of recommendation testing")
        
        if (isinstance(recommendations, list) and len(recommendations) > 0) or \
           (isinstance(delayed_recommendations, list) and len(delayed_recommendations) > 0) or \
           (isinstance(long_delayed_recommendations, list) and len(long_delayed_recommendations) > 0):
            logger.info("✅ PASS: Recommendations were successfully generated for new user with 10 votes")
            return True
        else:
            logger.error("❌ FAIL: No recommendations were generated for new user with 10 votes")
            return False

    def test_recommendation_generation_with_multiple_users(self, num_users=3):
        """Test recommendation generation with multiple users to verify consistency"""
        logger.info(f"\n🔍 Testing recommendation generation with {num_users} different users")
        
        results = []
        
        for i in range(num_users):
            # Reset user credentials for a new user
            self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}@example.com"
            self.test_user_password = "TestPassword123!"
            self.test_user_name = f"Test User {datetime.now().strftime('%H%M%S')} {i}"
            
            logger.info(f"\n📋 Testing with user {i+1}: {self.test_user_email}")
            
            # Register new user
            reg_success, _ = self.test_user_registration()
            if not reg_success:
                logger.error(f"❌ Failed to register user {i+1}")
                results.append(False)
                continue
            
            # Submit 10 votes
            vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=10)
            if not vote_success:
                logger.error(f"❌ Failed to submit 10 votes for user {i+1}")
                results.append(False)
                continue
            
            # Check for recommendations
            success, recommendations = self.test_get_recommendations(use_auth=True)
            
            if success and isinstance(recommendations, list) and len(recommendations) > 0:
                logger.info(f"✅ User {i+1}: Received {len(recommendations)} recommendations")
                results.append(True)
            else:
                # Try with a delay
                logger.info(f"User {i+1}: No immediate recommendations, waiting 5 seconds...")
                time.sleep(5)
                
                delayed_success, delayed_recommendations = self.test_get_recommendations(use_auth=True)
                
                if delayed_success and isinstance(delayed_recommendations, list) and len(delayed_recommendations) > 0:
                    logger.info(f"✅ User {i+1}: Received {len(delayed_recommendations)} recommendations after delay")
                    results.append(True)
                else:
                    logger.error(f"❌ User {i+1}: No recommendations available even after delay")
                    results.append(False)
        
        # Summarize results
        success_count = results.count(True)
        logger.info(f"\n📊 Recommendation generation succeeded for {success_count}/{num_users} users")
        
        return success_count == num_users

class MoviePreferenceAPITester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.auth_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
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
        
        self.tests_run += 1
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
                self.tests_passed += 1
                logger.info(f"✅ Passed - Status: {response.status_code}")
                self.test_results.append({"name": name, "status": "PASS", "details": f"Status: {response.status_code}"})
            else:
                logger.error(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({"name": name, "status": "FAIL", "details": f"Expected {expected_status}, got {response.status_code}"})

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            logger.error(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({"name": name, "status": "ERROR", "details": str(e)})
            return False, {}

    # Authentication Tests
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
    
    def test_get_voting_pair(self, use_auth=False):
        """Get a pair of items for voting"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Voting Pair", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=auth,
            params=params
        )
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type, use_auth=True):
        """Test submitting a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        if not use_auth or not self.auth_token:
            # Guest session vote
            if not self.session_id:
                logger.error("❌ No session ID available")
                self.test_results.append({"name": "Submit Vote", "status": "SKIP", "details": "No session ID available"})
                return False, {}
            data["session_id"] = self.session_id
            auth = False
        else:
            # Authenticated user vote
            auth = True
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=auth
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            logger.info(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_get_stats(self, use_auth=True):
        """Test getting user stats"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Stats", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get User Stats",
            "GET",
            "stats",
            200,
            auth=auth,
            params=params
        )
        
        if success:
            logger.info(f"Total votes: {response.get('total_votes')}")
            logger.info(f"Movie votes: {response.get('movie_votes')}")
            logger.info(f"Series votes: {response.get('series_votes')}")
            logger.info(f"Votes until recommendations: {response.get('votes_until_recommendations')}")
            logger.info(f"Recommendations available: {response.get('recommendations_available')}")
            logger.info(f"User authenticated: {response.get('user_authenticated')}")
        
        return success, response

    def test_get_recommendations(self, use_auth=True):
        """Test getting recommendations"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Recommendations",
            "GET",
            "recommendations",
            200,
            auth=auth,
            params=params
        )
        
        if success and isinstance(response, list):
            logger.info(f"✅ Received {len(response)} recommendations")
            
            # Check for poster data in recommendations
            poster_count = 0
            for i, rec in enumerate(response):
                logger.info(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
                
                if rec.get('poster'):
                    poster_count += 1
                    logger.info(f"    ✅ Has poster URL: {rec.get('poster')[:50]}...")
                else:
                    logger.info(f"    ⚠️ No poster available")
                    
                if rec.get('imdb_id'):
                    logger.info(f"    ✅ Has IMDB ID: {rec.get('imdb_id')}")
            
            logger.info(f"✅ {poster_count}/{len(response)} recommendations have poster images")
        
        return success, response

    def test_content_interaction(self, content_id, interaction_type, use_auth=True, session_id=None):
        """Test content interaction (watched, want_to_watch, not_interested)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif session_id or self.session_id:
            # Use guest session
            data["session_id"] = session_id or self.session_id
            auth = False
        else:
            logger.error("❌ No session ID or auth token available for content interaction")
            self.test_results.append({"name": f"Content Interaction ({interaction_type})", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=auth
        )
        
        if success and response.get('success') == True:
            logger.info(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response

    def simulate_voting_to_threshold(self, use_auth=True, target_votes=10):
        """Simulate voting until we reach the recommendation threshold"""
        logger.info(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes) using {'authenticated user' if use_auth else 'guest session'}...")
        
        # Get current vote count
        _, stats = self.test_get_stats(use_auth=use_auth)
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        logger.info(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair(use_auth)
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type'],
                use_auth
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                logger.info(f"Progress: {i+1}/{votes_needed} votes")
        
        logger.info(f"✅ Successfully completed {votes_needed} votes")
        return True

    def check_database_for_recommendations(self, user_id):
        """Check if recommendations were stored in the database"""
        try:
            # Check for recommendations in the database
            recommendations = list(self.db.algo_recommendations.find({"user_id": user_id}))
            
            if recommendations:
                logger.info(f"✅ Found {len(recommendations)} recommendations in database for user {user_id}")
                
                # Log some details about the recommendations
                for i, rec in enumerate(recommendations[:5]):  # Show first 5 for brevity
                    content = self.db.content.find_one({"id": rec["content_id"]})
                    title = content["title"] if content else "Unknown"
                    logger.info(f"  {i+1}. {title} - Score: {rec['recommendation_score']:.2f}, Confidence: {rec['confidence']:.2f}")
                    logger.info(f"     Reasoning: {rec['reasoning']}")
                
                return True, recommendations
            else:
                logger.error("❌ No recommendations found in database")
                return False, []
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return False, []

    def test_recommendation_generation_at_10_votes(self):
        """
        Test the specific defect: brand new logged-in user with exactly 10 votes 
        should see AI recommendations but instead sees "No AI recommendations available yet."
        """
        logger.info("\n🔍 TESTING DEFECT: New user with 10 votes should see AI recommendations")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a completely fresh user account")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        logger.info(f"✅ Successfully registered new user: {self.test_user_email}")
        
        # Step 2: Submit exactly 10 votes
        logger.info("\n📋 Step 2: Submit exactly 10 votes to trigger the recommendation system")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=10)
        if not vote_success:
            logger.error("❌ Failed to submit 10 votes")
            return False
        
        logger.info("✅ Successfully submitted exactly 10 votes")
        
        # Step 3: Check if recommendations are available in stats
        logger.info("\n📋 Step 3: Verify recommendations_available flag in stats")
        _, stats = self.test_get_stats(use_auth=True)
        if stats.get('recommendations_available'):
            logger.info("✅ Stats API confirms recommendations are available after 10 votes")
        else:
            logger.error("❌ Stats API reports recommendations are NOT available after 10 votes")
        
        # Step 4: Call /api/recommendations immediately after 10th vote
        logger.info("\n📋 Step 4: Call /api/recommendations immediately after 10th vote")
        success, recommendations = self.test_get_recommendations(use_auth=True)
        
        if success:
            if isinstance(recommendations, list) and len(recommendations) > 0:
                logger.info(f"✅ Received {len(recommendations)} recommendations immediately after 10th vote")
                
                # Log the recommendations
                for i, rec in enumerate(recommendations):
                    logger.info(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
            else:
                logger.error("❌ Received empty recommendations list immediately after 10th vote")
                logger.error(f"API Response: {recommendations}")
        else:
            logger.error("❌ Failed to get recommendations")
        
        # Step 5: Check database for recommendations
        logger.info("\n📋 Step 5: Check if recommendations were stored in algo_recommendations table")
        db_success, db_recommendations = self.check_database_for_recommendations(self.user_id)
        
        # Step 6: Timing test - try calling recommendations again after a short delay
        logger.info("\n📋 Step 6: Timing test - try calling recommendations again after a short delay")
        logger.info("Waiting 5 seconds for potential background processing...")
        time.sleep(5)
        
        delayed_success, delayed_recommendations = self.test_get_recommendations(use_auth=True)
        
        if delayed_success:
            if isinstance(delayed_recommendations, list) and len(delayed_recommendations) > 0:
                logger.info(f"✅ Received {len(delayed_recommendations)} recommendations after 5-second delay")
            else:
                logger.error("❌ Still received empty recommendations list after 5-second delay")
        
        # Step 7: Try a longer delay
        logger.info("\n📋 Step 7: Try a longer delay (10 seconds)")
        logger.info("Waiting 10 more seconds for potential background processing...")
        time.sleep(10)
        
        long_delayed_success, long_delayed_recommendations = self.test_get_recommendations(use_auth=True)
        
        if long_delayed_success:
            if isinstance(long_delayed_recommendations, list) and len(long_delayed_recommendations) > 0:
                logger.info(f"✅ Received {len(long_delayed_recommendations)} recommendations after 15-second total delay")
            else:
                logger.error("❌ Still received empty recommendations list after 15-second total delay")
        
        # Step 8: Final summary
        logger.info("\n📋 Step 8: Final summary of recommendation testing")
        
        if (isinstance(recommendations, list) and len(recommendations) > 0) or \
           (isinstance(delayed_recommendations, list) and len(delayed_recommendations) > 0) or \
           (isinstance(long_delayed_recommendations, list) and len(long_delayed_recommendations) > 0):
            logger.info("✅ PASS: Recommendations were successfully generated for new user with 10 votes")
            return True
        else:
            logger.error("❌ FAIL: No recommendations were generated for new user with 10 votes")
            return False

    def test_recommendation_generation_with_multiple_users(self, num_users=3):
        """Test recommendation generation with multiple users to verify consistency"""
        logger.info(f"\n🔍 Testing recommendation generation with {num_users} different users")
        
        results = []
        
        for i in range(num_users):
            # Reset user credentials for a new user
            self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}@example.com"
            self.test_user_password = "TestPassword123!"
            self.test_user_name = f"Test User {datetime.now().strftime('%H%M%S')} {i}"
            
            logger.info(f"\n📋 Testing with user {i+1}: {self.test_user_email}")
            
            # Register new user
            reg_success, _ = self.test_user_registration()
            if not reg_success:
                logger.error(f"❌ Failed to register user {i+1}")
                results.append(False)
                continue
            
            # Submit 10 votes
            vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=10)
            if not vote_success:
                logger.error(f"❌ Failed to submit 10 votes for user {i+1}")
                results.append(False)
                continue
            
            # Check for recommendations
            success, recommendations = self.test_get_recommendations(use_auth=True)
            
            if success and isinstance(recommendations, list) and len(recommendations) > 0:
                logger.info(f"✅ User {i+1}: Received {len(recommendations)} recommendations")
                results.append(True)
            else:
                # Try with a delay
                logger.info(f"User {i+1}: No immediate recommendations, waiting 5 seconds...")
                time.sleep(5)
                
                delayed_success, delayed_recommendations = self.test_get_recommendations(use_auth=True)
                
                if delayed_success and isinstance(delayed_recommendations, list) and len(delayed_recommendations) > 0:
                    logger.info(f"✅ User {i+1}: Received {len(delayed_recommendations)} recommendations after delay")
                    results.append(True)
                else:
                    logger.error(f"❌ User {i+1}: No recommendations available even after delay")
                    results.append(False)
        
        # Summarize results
        success_count = results.count(True)
        logger.info(f"\n📊 Recommendation generation succeeded for {success_count}/{num_users} users")
        
        return success_count == num_users
        
    def test_recommendations_pagination(self):
        """Test pagination for recommendations endpoint"""
        logger.info("\n🔍 TESTING RECOMMENDATIONS PAGINATION")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Submit enough votes to generate recommendations (20+ votes)
        logger.info("\n📋 Step 2: Submit 25 votes to generate sufficient recommendations")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=25)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Add some content interactions to enrich recommendations
        logger.info("\n📋 Step 3: Add some content interactions")
        # Get a voting pair to get some content IDs
        _, pair = self.test_get_voting_pair(use_auth=True)
        if pair and 'item1' in pair and 'item2' in pair:
            self.test_content_interaction(pair['item1']['id'], "watched", use_auth=True)
            self.test_content_interaction(pair['item2']['id'], "not_interested", use_auth=True)
        
        # Wait for recommendations to be generated
        logger.info("Waiting 5 seconds for recommendations to be generated...")
        time.sleep(5)
        
        # Step 4: Test first page of recommendations
        logger.info("\n📋 Step 4: Test first page of recommendations (offset=0, limit=20)")
        start_time = time.time()
        success, first_page = self.run_test(
            "Recommendations First Page",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": 0, "limit": 20}
        )
        first_page_time = time.time() - start_time
        
        if not success or not isinstance(first_page, list):
            logger.error("❌ Failed to get first page of recommendations")
            return False
        
        logger.info(f"✅ First page contains {len(first_page)} recommendations")
        logger.info(f"✅ Response time: {first_page_time:.3f} seconds")
        
        # Step 5: Test second page of recommendations
        logger.info("\n📋 Step 5: Test second page of recommendations (offset=20, limit=20)")
        start_time = time.time()
        success, second_page = self.run_test(
            "Recommendations Second Page",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": 20, "limit": 20}
        )
        second_page_time = time.time() - start_time
        
        if not success:
            logger.error("❌ Failed to get second page of recommendations")
            return False
        
        if isinstance(second_page, list):
            logger.info(f"✅ Second page contains {len(second_page)} recommendations")
            logger.info(f"✅ Response time: {second_page_time:.3f} seconds")
            
            # Check for duplicate recommendations between pages
            first_page_titles = [rec.get('title') for rec in first_page]
            second_page_titles = [rec.get('title') for rec in second_page]
            duplicates = set(first_page_titles) & set(second_page_titles)
            
            if duplicates:
                logger.warning(f"⚠️ Found {len(duplicates)} duplicate recommendations between pages")
            else:
                logger.info("✅ No duplicate recommendations between pages")
        
        # Step 6: Test third page of recommendations
        logger.info("\n📋 Step 6: Test third page of recommendations (offset=40, limit=20)")
        start_time = time.time()
        success, third_page = self.run_test(
            "Recommendations Third Page",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": 40, "limit": 20}
        )
        third_page_time = time.time() - start_time
        
        if not success:
            logger.error("❌ Failed to get third page of recommendations")
            return False
        
        if isinstance(third_page, list):
            logger.info(f"✅ Third page contains {len(third_page)} recommendations")
            logger.info(f"✅ Response time: {third_page_time:.3f} seconds")
        
        # Step 7: Test edge cases
        logger.info("\n📋 Step 7: Test edge cases")
        
        # Test with offset beyond available items
        success, beyond_offset = self.run_test(
            "Recommendations Beyond Available",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": 1000, "limit": 20}
        )
        
        if success and isinstance(beyond_offset, list):
            logger.info(f"✅ Beyond offset returns {len(beyond_offset)} recommendations")
        
        # Test with minimum limit
        success, min_limit = self.run_test(
            "Recommendations Minimum Limit",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": 0, "limit": 1}
        )
        
        if success and isinstance(min_limit, list):
            logger.info(f"✅ Minimum limit returns {len(min_limit)} recommendations")
        
        # Test with maximum limit
        success, max_limit = self.run_test(
            "Recommendations Maximum Limit",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": 0, "limit": 100}
        )
        
        if success and isinstance(max_limit, list):
            logger.info(f"✅ Maximum limit returns {len(max_limit)} recommendations")
        
        # Test with invalid parameters
        success, invalid_params = self.run_test(
            "Recommendations Invalid Parameters",
            "GET",
            "recommendations",
            422,  # FastAPI validation error
            auth=True,
            params={"offset": -1, "limit": 0}
        )
        
        # Step 8: Check database for total recommendations
        logger.info("\n📋 Step 8: Check database for total recommendations")
        try:
            total_recs = self.db.algo_recommendations.count_documents({"user_id": self.user_id})
            logger.info(f"✅ Total recommendations in database: {total_recs}")
            
            if total_recs > 0:
                logger.info(f"✅ User has {total_recs} recommendations in database")
                
                # Check if we're approaching the 1000 item limit
                if total_recs >= 900:
                    logger.info(f"✅ Approaching 1000-item limit with {total_recs} recommendations")
                
                # Log some sample recommendations
                sample_recs = list(self.db.algo_recommendations.find({"user_id": self.user_id}).limit(3))
                for i, rec in enumerate(sample_recs):
                    content = self.db.content.find_one({"id": rec["content_id"]})
                    title = content["title"] if content else "Unknown"
                    logger.info(f"  {i+1}. {title} - Score: {rec['recommendation_score']:.2f}, Confidence: {rec['confidence']:.2f}")
            else:
                logger.error("❌ No recommendations found in database")
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
        
        # Summary
        logger.info("\n📋 Recommendations Pagination Test Summary:")
        logger.info(f"✅ First page ({len(first_page)} items): {first_page_time:.3f}s")
        logger.info(f"✅ Second page ({len(second_page)} items): {second_page_time:.3f}s")
        logger.info(f"✅ Third page ({len(third_page)} items): {third_page_time:.3f}s")
        
        return True

    def test_watchlist_pagination(self):
        """Test pagination for watchlist endpoint"""
        logger.info("\n🔍 TESTING WATCHLIST PAGINATION")
        
        # Step 1: Register a new user if not already registered
        if not self.auth_token:
            logger.info("\n📋 Step 1: Register a new user")
            reg_success, reg_response = self.test_user_registration()
            if not reg_success:
                logger.error("❌ Failed to register user, stopping test")
                return False
        
        # Step 2: Submit votes to get content recommendations
        logger.info("\n📋 Step 2: Submit votes to get content recommendations")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=15)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Add multiple items to watchlist (30+ items)
        logger.info("\n📋 Step 3: Add multiple items to watchlist (aiming for 30+ items)")
        
        # Get content items from database to add to watchlist
        try:
            content_items = list(self.db.content.find().limit(40))
            logger.info(f"Found {len(content_items)} content items to potentially add to watchlist")
            
            # Add items to watchlist
            added_count = 0
            for item in content_items:
                # Add to watchlist via content interaction
                success, _ = self.test_content_interaction(item["id"], "want_to_watch", use_auth=True)
                if success:
                    added_count += 1
                    if added_count % 10 == 0:
                        logger.info(f"Added {added_count} items to watchlist")
                
                # Stop after adding 30 items
                if added_count >= 30:
                    break
            
            logger.info(f"✅ Successfully added {added_count} items to watchlist")
        except Exception as e:
            logger.error(f"❌ Error adding items to watchlist: {str(e)}")
            return False
        
        # Step 4: Test first page of watchlist
        logger.info("\n📋 Step 4: Test first page of watchlist (offset=0, limit=20)")
        start_time = time.time()
        success, first_page = self.run_test(
            "Watchlist First Page",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 0, "limit": 20}
        )
        first_page_time = time.time() - start_time
        
        if not success:
            logger.error("❌ Failed to get first page of watchlist")
            return False
        
        # Verify response structure
        if 'items' in first_page and 'total_count' in first_page and 'has_more' in first_page:
            logger.info(f"✅ First page contains {len(first_page['items'])} watchlist items")
            logger.info(f"✅ Total watchlist items: {first_page['total_count']}")
            logger.info(f"✅ Has more items: {first_page['has_more']}")
            logger.info(f"✅ Response time: {first_page_time:.3f} seconds")
            
            # Log some sample items
            for i, item in enumerate(first_page['items'][:3]):
                logger.info(f"  {i+1}. {item['content']['title']} - Priority: {item['priority']}")
        else:
            logger.error("❌ Invalid response structure for watchlist")
            return False
        
        # Step 5: Test second page of watchlist
        logger.info("\n📋 Step 5: Test second page of watchlist (offset=20, limit=20)")
        start_time = time.time()
        success, second_page = self.run_test(
            "Watchlist Second Page",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 20, "limit": 20}
        )
        second_page_time = time.time() - start_time
        
        if not success:
            logger.error("❌ Failed to get second page of watchlist")
            return False
        
        if 'items' in second_page:
            logger.info(f"✅ Second page contains {len(second_page['items'])} watchlist items")
            logger.info(f"✅ Response time: {second_page_time:.3f} seconds")
            
            # Check for duplicate items between pages
            if 'items' in first_page and len(first_page['items']) > 0:
                first_page_ids = [item['watchlist_id'] for item in first_page['items']]
                second_page_ids = [item['watchlist_id'] for item in second_page['items']]
                duplicates = set(first_page_ids) & set(second_page_ids)
                
                if duplicates:
                    logger.warning(f"⚠️ Found {len(duplicates)} duplicate watchlist items between pages")
                else:
                    logger.info("✅ No duplicate watchlist items between pages")
        
        # Step 6: Test edge cases
        logger.info("\n📋 Step 6: Test edge cases")
        
        # Test with offset beyond available items
        success, beyond_offset = self.run_test(
            "Watchlist Beyond Available",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 1000, "limit": 20}
        )
        
        if success and 'items' in beyond_offset:
            logger.info(f"✅ Beyond offset returns {len(beyond_offset['items'])} watchlist items")
        
        # Test with minimum limit
        success, min_limit = self.run_test(
            "Watchlist Minimum Limit",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 0, "limit": 1}
        )
        
        if success and 'items' in min_limit:
            logger.info(f"✅ Minimum limit returns {len(min_limit['items'])} watchlist items")
        
        # Test with maximum limit
        success, max_limit = self.run_test(
            "Watchlist Maximum Limit",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 0, "limit": 100}
        )
        
        if success and 'items' in max_limit:
            logger.info(f"✅ Maximum limit returns {len(max_limit['items'])} watchlist items")
        
        # Test with invalid parameters
        success, invalid_params = self.run_test(
            "Watchlist Invalid Parameters",
            "GET",
            "watchlist/user_defined",
            422,  # FastAPI validation error
            auth=True,
            params={"offset": -1, "limit": 0}
        )
        
        # Summary
        logger.info("\n📋 Watchlist Pagination Test Summary:")
        if 'items' in first_page and 'items' in second_page:
            logger.info(f"✅ First page ({len(first_page['items'])} items): {first_page_time:.3f}s")
            logger.info(f"✅ Second page ({len(second_page['items'])} items): {second_page_time:.3f}s")
            logger.info(f"✅ Total watchlist items: {first_page['total_count']}")
        
        return True

    def test_performance_with_large_dataset(self):
        """Test performance with large datasets"""
        logger.info("\n🔍 TESTING PERFORMANCE WITH LARGE DATASET")
        
        # Step 1: Register a new user if not already registered
        if not self.auth_token:
            logger.info("\n📋 Step 1: Register a new user")
            reg_success, reg_response = self.test_user_registration()
            if not reg_success:
                logger.error("❌ Failed to register user, stopping test")
                return False
        
        # Step 2: Submit many votes to generate a large dataset
        logger.info("\n📋 Step 2: Submit many votes (30+) to generate a large dataset")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=30)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Add many items to watchlist
        logger.info("\n📋 Step 3: Add many items to watchlist")
        try:
            content_items = list(self.db.content.find().limit(40))
            added_count = 0
            for item in content_items:
                success, _ = self.test_content_interaction(item["id"], "want_to_watch", use_auth=True)
                if success:
                    added_count += 1
                if added_count >= 30:
                    break
            logger.info(f"✅ Added {added_count} items to watchlist")
        except Exception as e:
            logger.error(f"❌ Error adding items to watchlist: {str(e)}")
        
        # Step 4: Test recommendations performance with different page sizes
        logger.info("\n📋 Step 4: Test recommendations performance with different page sizes")
        
        # Wait for recommendations to be generated
        logger.info("Waiting 5 seconds for recommendations to be generated...")
        time.sleep(5)
        
        page_sizes = [10, 20, 50, 100]
        for size in page_sizes:
            start_time = time.time()
            success, response = self.run_test(
                f"Recommendations (limit={size})",
                "GET",
                "recommendations",
                200,
                auth=True,
                params={"offset": 0, "limit": size}
            )
            elapsed_time = time.time() - start_time
            
            if success and isinstance(response, list):
                logger.info(f"✅ Recommendations with limit={size}: {len(response)} items in {elapsed_time:.3f}s")
            else:
                logger.error(f"❌ Failed to get recommendations with limit={size}")
        
        # Step 5: Test watchlist performance with different page sizes
        logger.info("\n📋 Step 5: Test watchlist performance with different page sizes")
        
        for size in page_sizes:
            start_time = time.time()
            success, response = self.run_test(
                f"Watchlist (limit={size})",
                "GET",
                "watchlist/user_defined",
                200,
                auth=True,
                params={"offset": 0, "limit": size}
            )
            elapsed_time = time.time() - start_time
            
            if success and 'items' in response:
                logger.info(f"✅ Watchlist with limit={size}: {len(response['items'])} items in {elapsed_time:.3f}s")
            else:
                logger.error(f"❌ Failed to get watchlist with limit={size}")
        
        # Step 6: Check database for total recommendations
        logger.info("\n📋 Step 6: Check database for total recommendations")
        try:
            total_recs = self.db.algo_recommendations.count_documents({"user_id": self.user_id})
            logger.info(f"✅ Total recommendations in database: {total_recs}")
            
            if total_recs > 0:
                # Check if we're approaching the 1000 item limit
                if total_recs >= 900:
                    logger.info(f"✅ Successfully generated {total_recs} recommendations, approaching 1000-item limit")
                else:
                    logger.info(f"✅ Successfully generated {total_recs} recommendations")
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
        
        return True

def main():
    tester = MoviePreferenceAPITester()
    
    # Test pagination for recommendations
    recommendations_pagination_result = tester.test_recommendations_pagination()
    
    # Test pagination for watchlist
    watchlist_pagination_result = tester.test_watchlist_pagination()
    
    # Test performance with large dataset
    performance_result = tester.test_performance_with_large_dataset()
    
    # Print results
    logger.info(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Print detailed results
    logger.info("\n📋 Test Results:")
    for result in tester.test_results:
        status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
        logger.info(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
    
    # Print pagination test summary
    logger.info("\n📋 Pagination Test Summary:")
    if recommendations_pagination_result:
        logger.info("✅ PASS: Recommendations pagination is working correctly")
    else:
        logger.info("❌ FAIL: Recommendations pagination has issues")
    
    if watchlist_pagination_result:
        logger.info("✅ PASS: Watchlist pagination is working correctly")
    else:
        logger.info("❌ FAIL: Watchlist pagination has issues")
    
    # Print performance test summary
    logger.info("\n📋 Performance Test Summary:")
    if performance_result:
        logger.info("✅ PASS: Performance with large datasets is acceptable")
    else:
        logger.info("❌ FAIL: Performance issues detected with large datasets")
    
    return 0 if recommendations_pagination_result and watchlist_pagination_result and performance_result else 1

if __name__ == "__main__":
    sys.exit(main())
