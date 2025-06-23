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
logger = logging.getLogger("watched_content_test")

class MoviePreferenceAPITester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
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

    def test_get_recommendations(self, use_auth=True, offset=0, limit=20):
        """Test getting recommendations"""
        params = {"offset": offset, "limit": limit}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params["session_id"] = self.session_id
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Get Recommendations (offset={offset}, limit={limit})",
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
        current_votes = 0
        
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

    def check_database_for_interactions(self, user_id, interaction_type="watched"):
        """Check if interactions were stored in the database"""
        try:
            # Check for interactions in the database
            interactions = list(self.db.user_interactions.find({
                "user_id": user_id,
                "interaction_type": interaction_type
            }))
            
            if interactions:
                logger.info(f"✅ Found {len(interactions)} '{interaction_type}' interactions in database for user {user_id}")
                
                # Log some details about the interactions
                for i, interaction in enumerate(interactions[:5]):  # Show first 5 for brevity
                    content = self.db.content.find_one({"id": interaction["content_id"]})
                    title = content["title"] if content else "Unknown"
                    logger.info(f"  {i+1}. {title} - Content ID: {interaction['content_id']}")
                
                return True, interactions
            else:
                logger.error(f"❌ No '{interaction_type}' interactions found in database")
                return False, []
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return False, []

    def test_watched_content_exclusion(self):
        """
        Test the watched content exclusion functionality in personalized voting pair generation.
        
        Steps:
        1. Register a new user
        2. Submit enough votes to trigger personalized strategy (10+)
        3. Get initial voting pairs and note the content
        4. Mark specific content as 'watched'
        5. Request new voting pairs
        6. Verify that marked-as-watched content does NOT appear in new pairs
        """
        logger.info("\n🔍 TESTING WATCHED CONTENT EXCLUSION")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Submit enough votes to trigger personalized strategy (15 votes)
        logger.info("\n📋 Step 2: Submit 15 votes to trigger personalized strategy")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=15)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Get initial recommendations and record the first 3 items
        logger.info("\n📋 Step 3: Get initial recommendations and record the first 3 items")
        success, initial_recommendations = self.test_get_recommendations(use_auth=True)
        
        if not success or not isinstance(initial_recommendations, list) or len(initial_recommendations) < 3:
            logger.error("❌ Failed to get initial recommendations or not enough items")
            return False
        
        # Record the first 3 recommendations
        watched_items = initial_recommendations[:3]
        logger.info(f"✅ Selected {len(watched_items)} items to mark as watched")
        
        # Step 4: Mark the first recommendation as 'watched'
        logger.info("\n📋 Step 4: Mark the first recommendation as 'watched'")
        
        # Try with both internal ID and IMDB ID formats
        for i, item in enumerate(watched_items):
            # Get the content item to find its internal ID
            content_item = None
            try:
                content_item = self.db.content.find_one({"imdb_id": item["imdb_id"]})
            except Exception as e:
                logger.error(f"❌ Error finding content item: {str(e)}")
            
            if content_item:
                # For the first item, use internal ID
                if i == 0:
                    content_id = content_item["id"]
                    logger.info(f"Marking item {i+1} as watched using internal ID: {content_id}")
                # For the second item, use IMDB ID
                elif i == 1:
                    content_id = item["imdb_id"]
                    logger.info(f"Marking item {i+1} as watched using IMDB ID: {content_id}")
                # For the third item, don't mark it (control)
                else:
                    logger.info(f"Not marking item {i+1} as watched (control)")
                    continue
                
                # Mark as watched
                success, _ = self.test_content_interaction(content_id, "watched", use_auth=True)
                if not success:
                    logger.error(f"❌ Failed to mark item {i+1} as watched")
            else:
                logger.error(f"❌ Could not find content item for recommendation {i+1}")
        
        # Step 5: Verify the interactions are stored in the database
        logger.info("\n📋 Step 5: Verify the interactions are stored in the database")
        db_success, watched_interactions = self.check_database_for_interactions(self.user_id, "watched")
        
        if not db_success:
            logger.error("❌ Failed to verify watched interactions in database")
        
        # Step 6: Test exclusion in recommendations
        logger.info("\n📋 Step 6: Test exclusion in recommendations")
        
        # Wait a moment for the background processing
        logger.info("Waiting 5 seconds for background processing...")
        time.sleep(5)
        
        # Get new recommendations
        success, new_recommendations = self.test_get_recommendations(use_auth=True)
        
        if not success or not isinstance(new_recommendations, list):
            logger.error("❌ Failed to get new recommendations")
            return False
        
        # Check if watched items are excluded
        watched_imdb_ids = [item["imdb_id"] for item in watched_items[:2]]  # Only the first 2 were marked as watched
        found_watched_items = []
        
        for rec in new_recommendations:
            if rec["imdb_id"] in watched_imdb_ids:
                found_watched_items.append(rec["title"])
        
        if found_watched_items:
            logger.error(f"❌ Found {len(found_watched_items)} watched items in recommendations: {', '.join(found_watched_items)}")
            logger.error("Watched content exclusion is NOT working correctly for recommendations")
        else:
            logger.info("✅ No watched items found in recommendations - exclusion is working correctly")
        
        # Step 7: Test exclusion in voting pairs
        logger.info("\n📋 Step 7: Test exclusion in voting pairs")
        
        # Get multiple voting pairs and check if watched content appears
        num_pairs_to_check = 10
        found_in_pairs = []
        
        for i in range(num_pairs_to_check):
            success, pair = self.test_get_voting_pair(use_auth=True)
            
            if success:
                # Check if either item in the pair is a watched item
                for watched_item in watched_items[:2]:  # Only the first 2 were marked as watched
                    if pair["item1"]["imdb_id"] == watched_item["imdb_id"] or pair["item2"]["imdb_id"] == watched_item["imdb_id"]:
                        found_in_pairs.append(f"Pair {i+1}: {watched_item['title']}")
            else:
                logger.error(f"❌ Failed to get voting pair {i+1}")
        
        if found_in_pairs:
            logger.error(f"❌ Found watched items in {len(found_in_pairs)}/{num_pairs_to_check} voting pairs:")
            for item in found_in_pairs:
                logger.error(f"  - {item}")
            logger.error("Watched content exclusion is NOT working correctly for voting pairs")
        else:
            logger.info(f"✅ No watched items found in {num_pairs_to_check} voting pairs - exclusion is working correctly")
        
        # Step 8: Test with both cold-start and personalized strategies
        logger.info("\n📋 Step 8: Test with both cold-start and personalized strategies")
        
        # Create a new user for cold-start testing
        self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}_cold@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Test User Cold {datetime.now().strftime('%H%M%S')}"
        
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register cold-start user")
        else:
            # Submit just 5 votes (below the 10-vote threshold for personalized)
            vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=5)
            if not vote_success:
                logger.error("❌ Failed to submit votes for cold-start user")
            else:
                # Get a recommendation to mark as watched
                success, cold_recommendations = self.test_get_recommendations(use_auth=True)
                
                if success and isinstance(cold_recommendations, list) and len(cold_recommendations) > 0:
                    # Mark the first recommendation as watched
                    content_item = self.db.content.find_one({"imdb_id": cold_recommendations[0]["imdb_id"]})
                    if content_item:
                        success, _ = self.test_content_interaction(content_item["id"], "watched", use_auth=True)
                        
                        if success:
                            # Wait a moment
                            time.sleep(2)
                            
                            # Check if it appears in voting pairs
                            found_in_cold_pairs = False
                            for i in range(5):
                                success, pair = self.test_get_voting_pair(use_auth=True)
                                
                                if success:
                                    if pair["item1"]["imdb_id"] == cold_recommendations[0]["imdb_id"] or pair["item2"]["imdb_id"] == cold_recommendations[0]["imdb_id"]:
                                        found_in_cold_pairs = True
                                        break
                            
                            if found_in_cold_pairs:
                                logger.error("❌ Found watched item in cold-start voting pairs")
                                logger.error("Watched content exclusion is NOT working correctly for cold-start strategy")
                            else:
                                logger.info("✅ No watched items found in cold-start voting pairs - exclusion is working correctly")
        
        # Step 9: Test ID matching verification
        logger.info("\n📋 Step 9: Test ID matching verification")
        
        # Already tested in steps 4-7 by using both internal ID and IMDB ID formats
        
        # Step 10: Summary
        logger.info("\n📋 Step 10: Summary")
        
        if not found_watched_items and not found_in_pairs:
            logger.info("✅ PASS: Watched content exclusion is working correctly")
            logger.info("✅ Both internal ID and IMDB ID formats are handled correctly")
            logger.info("✅ Exclusion persists across multiple API calls")
            return True
        else:
            logger.error("❌ FAIL: Watched content exclusion is NOT working correctly")
            if found_watched_items:
                logger.error(f"❌ Found {len(found_watched_items)} watched items in recommendations")
            if found_in_pairs:
                logger.error(f"❌ Found watched items in {len(found_in_pairs)}/{num_pairs_to_check} voting pairs")
            return False

def main():
    tester = MoviePreferenceAPITester()
    
    # Run the watched content exclusion test
    tester.test_watched_content_exclusion()
    
    # Print summary
    logger.info("\n📊 TEST SUMMARY")
    logger.info(f"Total tests run: {tester.tests_run}")
    logger.info(f"Tests passed: {tester.tests_passed}")
    logger.info(f"Success rate: {tester.tests_passed/tester.tests_run*100:.1f}%")

if __name__ == "__main__":
    main()