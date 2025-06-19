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
logger = logging.getLogger("watched_content_exclusion_test")

class WatchedContentExclusionTester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
        self.base_url = base_url
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

    def test_get_voting_pair(self):
        """Get a pair of items for voting"""
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=True
        )
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type):
        """Test submitting a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=True
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            logger.info(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_get_recommendations(self, offset=0, limit=20):
        """Test getting recommendations"""
        params = {"offset": offset, "limit": limit}
        
        success, response = self.run_test(
            f"Get Recommendations (offset={offset}, limit={limit})",
            "GET",
            "recommendations",
            200,
            auth=True,
            params=params
        )
        
        if success and isinstance(response, list):
            logger.info(f"✅ Received {len(response)} recommendations")
            
            # Log some recommendations
            for i, rec in enumerate(response[:3]):
                logger.info(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
                logger.info(f"     IMDB ID: {rec.get('imdb_id')}")
        
        return success, response

    def test_mark_content_as_watched(self, content_id):
        """Test marking content as watched"""
        data = {
            "content_id": content_id,
            "interaction_type": "watched"
        }
        
        success, response = self.run_test(
            "Mark Content as Watched",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=True
        )
        
        if success and response.get('success') == True:
            logger.info(f"✅ Content {content_id} marked as watched successfully")
            return True, response
        
        return success, response

    def simulate_voting_to_threshold(self, target_votes=10):
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
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair()
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type']
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                logger.info(f"Progress: {i+1}/{votes_needed} votes")
        
        logger.info(f"✅ Successfully completed {votes_needed} votes")
        return True

    def check_database_for_watched_interaction(self, content_id):
        """Check if the watched interaction was stored in the database"""
        try:
            # Check for watched interaction in the database
            interaction = self.db.user_interactions.find_one({
                "user_id": self.user_id,
                "content_id": content_id,
                "interaction_type": "watched"
            })
            
            if interaction:
                logger.info(f"✅ Found watched interaction in database for content {content_id}")
                return True, interaction
            else:
                logger.error(f"❌ No watched interaction found in database for content {content_id}")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return False, None

    def check_if_content_in_recommendations(self, content_id, recommendations):
        """Check if a specific content ID appears in the recommendations"""
        for rec in recommendations:
            if rec.get('imdb_id') == content_id:
                return True
        return False

    def test_watched_content_exclusion(self):
        """
        Test the watched content exclusion functionality to verify that marked content
        is properly excluded from recommendations.
        """
        logger.info("\n🔍 TESTING WATCHED CONTENT EXCLUSION FUNCTIONALITY")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new test user")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        logger.info(f"✅ Successfully registered new user: {self.test_user_email}")
        
        # Step 2: Submit votes to generate recommendations
        logger.info("\n📋 Step 2: Submit 10+ votes to generate recommendations")
        vote_success = self.simulate_voting_to_threshold(target_votes=15)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        logger.info("✅ Successfully submitted votes to generate recommendations")
        
        # Step 3: Get initial recommendations
        logger.info("\n📋 Step 3: Get initial recommendations")
        success, initial_recommendations = self.test_get_recommendations()
        
        if not success or not isinstance(initial_recommendations, list) or len(initial_recommendations) == 0:
            logger.error("❌ Failed to get initial recommendations")
            return False
        
        logger.info(f"✅ Received {len(initial_recommendations)} initial recommendations")
        
        # Record the first 3 recommendations
        first_three_recs = initial_recommendations[:3]
        logger.info("\nFirst 3 recommendations:")
        for i, rec in enumerate(first_three_recs):
            logger.info(f"  {i+1}. {rec.get('title')} - IMDB ID: {rec.get('imdb_id')}")
        
        # Step 4: Mark the first recommendation as watched
        logger.info("\n📋 Step 4: Mark the first recommendation as watched")
        first_rec = first_three_recs[0]
        first_rec_imdb_id = first_rec.get('imdb_id')
        
        # Get the content_id from the database using the IMDB ID
        content = self.db.content.find_one({"imdb_id": first_rec_imdb_id})
        if not content:
            logger.error(f"❌ Could not find content with IMDB ID {first_rec_imdb_id} in database")
            return False
        
        content_id = content.get('id')
        logger.info(f"Found content ID {content_id} for IMDB ID {first_rec_imdb_id}")
        
        # Mark the content as watched
        watch_success, _ = self.test_mark_content_as_watched(content_id)
        if not watch_success:
            logger.error(f"❌ Failed to mark content {content_id} as watched")
            return False
        
        logger.info(f"✅ Successfully marked content {content_id} (IMDB ID: {first_rec_imdb_id}) as watched")
        
        # Step 5: Verify the interaction was stored correctly
        logger.info("\n📋 Step 5: Verify the watched interaction was stored correctly")
        db_success, interaction = self.check_database_for_watched_interaction(content_id)
        if not db_success:
            logger.error("❌ Watched interaction not found in database")
            return False
        
        logger.info(f"✅ Watched interaction verified in database: {interaction}")
        
        # Step 6: Get recommendations again immediately
        logger.info("\n📋 Step 6: Get recommendations again immediately")
        success, immediate_recommendations = self.test_get_recommendations()
        
        if not success or not isinstance(immediate_recommendations, list):
            logger.error("❌ Failed to get immediate recommendations")
            return False
        
        logger.info(f"✅ Received {len(immediate_recommendations)} immediate recommendations")
        
        # Check if the watched content is excluded
        watched_content_present = self.check_if_content_in_recommendations(first_rec_imdb_id, immediate_recommendations)
        
        if watched_content_present:
            logger.error(f"❌ Watched content {first_rec_imdb_id} still appears in immediate recommendations")
            
            # Find the position of the watched content
            for i, rec in enumerate(immediate_recommendations):
                if rec.get('imdb_id') == first_rec_imdb_id:
                    logger.error(f"  Found at position {i+1}: {rec.get('title')}")
                    break
        else:
            logger.info(f"✅ Watched content {first_rec_imdb_id} is properly excluded from immediate recommendations")
        
        # Step 7: Force regeneration of recommendations
        logger.info("\n📋 Step 7: Force regeneration of recommendations")
        logger.info("Submitting 5 more votes to trigger recommendation refresh...")
        
        # Submit 5 more votes to trigger recommendation refresh
        for _ in range(5):
            success, pair = self.test_get_voting_pair()
            if success:
                self.test_submit_vote(pair['item1']['id'], pair['item2']['id'], pair['content_type'])
        
        logger.info("Waiting 5 seconds for recommendations to regenerate...")
        time.sleep(5)
        
        # Step 8: Get recommendations after regeneration
        logger.info("\n📋 Step 8: Get recommendations after regeneration")
        success, regenerated_recommendations = self.test_get_recommendations()
        
        if not success or not isinstance(regenerated_recommendations, list):
            logger.error("❌ Failed to get regenerated recommendations")
            return False
        
        logger.info(f"✅ Received {len(regenerated_recommendations)} regenerated recommendations")
        
        # Check if the watched content is still excluded
        watched_content_present = self.check_if_content_in_recommendations(first_rec_imdb_id, regenerated_recommendations)
        
        if watched_content_present:
            logger.error(f"❌ Watched content {first_rec_imdb_id} appears in regenerated recommendations")
            
            # Find the position of the watched content
            for i, rec in enumerate(regenerated_recommendations):
                if rec.get('imdb_id') == first_rec_imdb_id:
                    logger.error(f"  Found at position {i+1}: {rec.get('title')}")
                    break
        else:
            logger.info(f"✅ Watched content {first_rec_imdb_id} is properly excluded from regenerated recommendations")
        
        # Step 9: Get multiple pages of recommendations
        logger.info("\n📋 Step 9: Check multiple pages of recommendations")
        
        # Check first page
        success, page1 = self.test_get_recommendations(offset=0, limit=20)
        watched_in_page1 = self.check_if_content_in_recommendations(first_rec_imdb_id, page1)
        
        # Check second page
        success, page2 = self.test_get_recommendations(offset=20, limit=20)
        watched_in_page2 = self.check_if_content_in_recommendations(first_rec_imdb_id, page2)
        
        # Check third page
        success, page3 = self.test_get_recommendations(offset=40, limit=20)
        watched_in_page3 = self.check_if_content_in_recommendations(first_rec_imdb_id, page3)
        
        if watched_in_page1 or watched_in_page2 or watched_in_page3:
            logger.error(f"❌ Watched content {first_rec_imdb_id} appears in pagination:")
            logger.error(f"  Page 1: {watched_in_page1}")
            logger.error(f"  Page 2: {watched_in_page2}")
            logger.error(f"  Page 3: {watched_in_page3}")
        else:
            logger.info(f"✅ Watched content {first_rec_imdb_id} is properly excluded from all pages")
        
        # Step 10: Check database state
        logger.info("\n📋 Step 10: Check database state")
        
        # Check user_interactions collection
        watched_interaction = self.db.user_interactions.find_one({
            "user_id": self.user_id,
            "content_id": content_id,
            "interaction_type": "watched"
        })
        
        if watched_interaction:
            logger.info(f"✅ Watched interaction found in user_interactions collection")
            logger.info(f"  Content ID: {watched_interaction.get('content_id')}")
            logger.info(f"  Created at: {watched_interaction.get('created_at')}")
        else:
            logger.error("❌ Watched interaction not found in user_interactions collection")
        
        # Check algo_recommendations collection
        algo_recs = list(self.db.algo_recommendations.find({
            "user_id": self.user_id,
            "content_id": content_id
        }))
        
        if algo_recs:
            logger.info(f"⚠️ Found {len(algo_recs)} entries in algo_recommendations for watched content")
            logger.info("This is not necessarily an error, as the exclusion might happen at query time")
        else:
            logger.info("✅ No entries found in algo_recommendations for watched content")
        
        # Step 11: Test cross-session persistence
        logger.info("\n📋 Step 11: Test cross-session persistence")
        
        # Create a new auth token for the same user
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        success, login_response = self.run_test(
            "User Login (new session)",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in login_response:
            old_token = self.auth_token
            self.auth_token = login_response['access_token']
            logger.info(f"✅ Created new auth token: {self.auth_token[:10]}...")
            
            # Get recommendations with new token
            success, new_session_recommendations = self.test_get_recommendations()
            
            if success and isinstance(new_session_recommendations, list):
                logger.info(f"✅ Received {len(new_session_recommendations)} recommendations with new token")
                
                # Check if watched content is still excluded
                watched_content_present = self.check_if_content_in_recommendations(first_rec_imdb_id, new_session_recommendations)
                
                if watched_content_present:
                    logger.error(f"❌ Watched content {first_rec_imdb_id} appears in new session recommendations")
                else:
                    logger.info(f"✅ Watched content {first_rec_imdb_id} is properly excluded in new session")
            else:
                logger.error("❌ Failed to get recommendations with new token")
        else:
            logger.error("❌ Failed to create new auth token")
        
        # Final summary
        logger.info("\n📋 WATCHED CONTENT EXCLUSION TEST SUMMARY")
        
        if not watched_content_present and not watched_in_page1 and not watched_in_page2 and not watched_in_page3:
            logger.info("✅ PASS: Watched content is properly excluded from recommendations")
            logger.info(f"  - Content ID: {content_id}")
            logger.info(f"  - IMDB ID: {first_rec_imdb_id}")
            logger.info(f"  - Title: {first_rec.get('title')}")
            logger.info("  - Excluded from immediate recommendations: ✅")
            logger.info("  - Excluded after regeneration: ✅")
            logger.info("  - Excluded from all pagination pages: ✅")
            logger.info("  - Excluded in new session: ✅")
            return True
        else:
            logger.error("❌ FAIL: Watched content is not properly excluded from recommendations")
            logger.error(f"  - Content ID: {content_id}")
            logger.error(f"  - IMDB ID: {first_rec_imdb_id}")
            logger.error(f"  - Title: {first_rec.get('title')}")
            logger.error(f"  - Excluded from immediate recommendations: {'✅' if not watched_content_present else '❌'}")
            logger.error(f"  - Excluded after regeneration: {'✅' if not watched_in_page1 and not watched_in_page2 and not watched_in_page3 else '❌'}")
            return False

if __name__ == "__main__":
    tester = WatchedContentExclusionTester()
    tester.test_watched_content_exclusion()