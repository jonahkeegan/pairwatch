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

def main():
    tester = MoviePreferenceAPITester()
    
    # Test the specific defect
    defect_test_result = tester.test_recommendation_generation_at_10_votes()
    
    # Test with multiple users for consistency
    multi_user_test_result = tester.test_recommendation_generation_with_multiple_users(num_users=2)
    
    # Print results
    logger.info(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Print detailed results
    logger.info("\n📋 Test Results:")
    for result in tester.test_results:
        status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
        logger.info(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
    
    # Print defect test summary
    logger.info("\n📋 Defect Test Summary:")
    if defect_test_result:
        logger.info("✅ PASS: New user with exactly 10 votes successfully received AI recommendations")
    else:
        logger.info("❌ FAIL: New user with exactly 10 votes did NOT receive AI recommendations")
    
    # Print multi-user test summary
    logger.info("\n📋 Multi-User Test Summary:")
    if multi_user_test_result:
        logger.info("✅ PASS: All test users successfully received AI recommendations after 10 votes")
    else:
        logger.info("❌ FAIL: Some test users did NOT receive AI recommendations after 10 votes")
    
    return 0 if defect_test_result and multi_user_test_result else 1

if __name__ == "__main__":
    sys.exit(main())
