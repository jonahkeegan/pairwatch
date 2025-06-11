import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

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
        
        print(f"🔍 Testing API at: {self.base_url}")
        print(f"📝 Test user: {self.test_user_email}")

    def run_test(self, name, method, endpoint, expected_status, data=None, auth=False, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add authorization header if needed
        if auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
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
                print(f"✅ Passed - Status: {response.status_code}")
                self.test_results.append({"name": name, "status": "PASS", "details": f"Status: {response.status_code}"})
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({"name": name, "status": "FAIL", "details": f"Expected {expected_status}, got {response.status_code}"})

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
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
            print(f"✅ User registered with ID: {self.user_id}")
            print(f"✅ Auth token received: {self.auth_token[:10]}...")
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
            print(f"✅ User logged in with ID: {self.user_id}")
            print(f"✅ Auth token received: {self.auth_token[:10]}...")
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
            print("❌ No session ID or auth token available")
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
                print("❌ No session ID available")
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
            print(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
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
            print("❌ No session ID or auth token available")
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
            print(f"Total votes: {response.get('total_votes')}")
            print(f"Movie votes: {response.get('movie_votes')}")
            print(f"Series votes: {response.get('series_votes')}")
            print(f"Votes until recommendations: {response.get('votes_until_recommendations')}")
            print(f"Recommendations available: {response.get('recommendations_available')}")
            print(f"User authenticated: {response.get('user_authenticated')}")
        
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
            print("❌ No session ID or auth token available")
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
            print(f"✅ Received {len(response)} recommendations")
            
            # Check for poster data in recommendations
            poster_count = 0
            for i, rec in enumerate(response):
                print(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
                
                if rec.get('poster'):
                    poster_count += 1
                    print(f"    ✅ Has poster URL: {rec.get('poster')[:50]}...")
                else:
                    print(f"    ⚠️ No poster available")
                    
                if rec.get('imdb_id'):
                    print(f"    ✅ Has IMDB ID: {rec.get('imdb_id')}")
            
            print(f"✅ {poster_count}/{len(response)} recommendations have poster images")
        
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
            print("❌ No session ID or auth token available for content interaction")
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
            print(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response

    def simulate_voting_to_threshold(self, use_auth=True, target_votes=10):
        """Simulate voting until we reach the recommendation threshold"""
        print(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes) using {'authenticated user' if use_auth else 'guest session'}...")
        
        # Get current vote count
        _, stats = self.test_get_stats(use_auth=use_auth)
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        print(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair(use_auth)
            if not success:
                print(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type'],
                use_auth
            )
            
            if not vote_success:
                print(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                print(f"Progress: {i+1}/{votes_needed} votes")
        
        print(f"✅ Successfully completed {votes_needed} votes")
        return True

    def test_automatic_triggers(self):
        """
        Test the automatic trigger points with debugging enabled.
        
        This test specifically verifies:
        1. Register a new user
        2. Submit exactly 10 votes (this should trigger milestone auto-generation)
        3. Mark some content as "watched" (this should trigger interaction-based refresh)
        4. Submit 5 more votes to reach 15 votes (another milestone)
        
        The test captures and reports DEBUG messages from the logs.
        """
        print("\n🔍 Testing Automatic Trigger Points with Debugging...")
        
        # Step 1: Register a new user
        print("\n📋 Step 1: Register a new user")
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            print("❌ Failed to register user, stopping test")
            return False
        
        print("✅ Successfully registered new user")
        
        # Step 2: Submit exactly 10 votes (this should trigger milestone auto-generation)
        print("\n📋 Step 2: Submit exactly 10 votes (milestone trigger)")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=10)
        if not vote_success:
            print("❌ Failed to submit 10 votes")
            return False
        
        print("✅ Successfully submitted 10 votes")
        
        # Check if recommendations are available
        _, stats = self.test_get_stats(use_auth=True)
        if stats.get('recommendations_available'):
            print("✅ Recommendations are available after 10 votes")
        else:
            print("❌ Recommendations are not available after 10 votes")
        
        # Get recommendations to verify they were auto-generated
        success, recommendations = self.test_get_recommendations(use_auth=True)
        if success and len(recommendations) > 0:
            print(f"✅ Auto-generated recommendations available: {len(recommendations)} items")
        else:
            print("❌ No auto-generated recommendations found")
        
        # Step 3: Mark some content as "watched" (this should trigger interaction-based refresh)
        print("\n📋 Step 3: Mark content as 'watched' (interaction trigger)")
        
        # Get a voting pair to get content ID
        pair_success, pair = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            print("❌ Failed to get content for interaction")
            return False
        
        # Mark content as watched
        content_id = pair['item1']['id']
        content_title = pair['item1']['title']
        
        print(f"Marking content as watched: {content_title} (ID: {content_id})")
        watched_success, _ = self.test_content_interaction(content_id, "watched", use_auth=True)
        
        if not watched_success:
            print("❌ Failed to mark content as watched")
            return False
        
        print("✅ Successfully marked content as watched")
        
        # Wait a moment for background processing
        print("Waiting for background processing...")
        time.sleep(3)
        
        # Step 4: Submit 5 more votes to reach 15 votes (another milestone)
        print("\n📋 Step 4: Submit 5 more votes to reach 15 votes (another milestone)")
        vote_success = self.simulate_voting_to_threshold(use_auth=True, target_votes=15)
        if not vote_success:
            print("❌ Failed to submit additional votes")
            return False
        
        print("✅ Successfully submitted 5 more votes (total: 15)")
        
        # Check if recommendations are still available
        _, stats = self.test_get_stats(use_auth=True)
        if stats.get('recommendations_available'):
            print("✅ Recommendations are available after 15 votes")
        else:
            print("❌ Recommendations are not available after 15 votes")
        
        # Get recommendations again to verify they were refreshed
        success, recommendations = self.test_get_recommendations(use_auth=True)
        if success and len(recommendations) > 0:
            print(f"✅ Recommendations available after milestone: {len(recommendations)} items")
        else:
            print("❌ No recommendations found after milestone")
        
        print("\n✅ Automatic trigger testing completed")
        return True

def main():
    tester = MoviePreferenceAPITester()
    
    # Test the automatic triggers with debugging enabled
    tester.test_automatic_triggers()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Print detailed results
    print("\n📋 Test Results:")
    for result in tester.test_results:
        status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
