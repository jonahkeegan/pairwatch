import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class VoteCountdownTester:
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

    def test_create_session(self):
        """Test session creation"""
        success, response = self.run_test(
            "Create Session",
            "POST",
            "session",
            200,
            data={}
        )
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            print(f"Session ID: {self.session_id}")
            return True, response
        return False, response

    def test_get_voting_pair(self, use_auth=False):
        """Test getting a voting pair"""
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

    def test_submit_vote(self, winner_id, loser_id, content_type, use_auth=False):
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

    def test_get_stats(self, use_auth=False):
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

    def simulate_voting(self, num_votes, use_auth=False):
        """Simulate a specific number of votes"""
        print(f"\n🔄 Simulating {num_votes} votes using {'authenticated user' if use_auth else 'guest session'}...")
        
        for i in range(num_votes):
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
            if (i+1) % 5 == 0 or i == num_votes - 1:
                print(f"Progress: {i+1}/{num_votes} votes")
        
        print(f"✅ Successfully completed {num_votes} votes")
        return True

    def test_vote_countdown(self):
        """Test the vote countdown functionality with the new 10-vote threshold"""
        print("\n🔍 Testing Vote Countdown Functionality with 10-vote threshold...")
        
        # Scenario 1: New user with 0 votes
        print("\n📋 Scenario 1: New user with 0 votes")
        # Register a new user
        self.test_user_registration()
        
        # Get stats for new user (0 votes)
        success, stats = self.test_get_stats(use_auth=True)
        if success:
            if stats.get('total_votes') == 0 and stats.get('votes_until_recommendations') == 10:
                print("✅ PASS: New user with 0 votes shows votes_until_recommendations = 10")
                self.test_results.append({
                    "name": "Vote Countdown - New User (0 votes)", 
                    "status": "PASS", 
                    "details": "New user with 0 votes correctly shows votes_until_recommendations = 10"
                })
            else:
                print(f"❌ FAIL: New user with 0 votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 10")
                self.test_results.append({
                    "name": "Vote Countdown - New User (0 votes)", 
                    "status": "FAIL", 
                    "details": f"New user with 0 votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 10"
                })
        
        # Scenario 2: User with 5 votes
        print("\n📋 Scenario 2: User with 5 votes")
        # Simulate 5 votes
        self.simulate_voting(5, use_auth=True)
        
        # Get stats for user with 5 votes
        success, stats = self.test_get_stats(use_auth=True)
        if success:
            if stats.get('total_votes') == 5 and stats.get('votes_until_recommendations') == 5:
                print("✅ PASS: User with 5 votes shows votes_until_recommendations = 5")
                self.test_results.append({
                    "name": "Vote Countdown - User with 5 votes", 
                    "status": "PASS", 
                    "details": "User with 5 votes correctly shows votes_until_recommendations = 5"
                })
            else:
                print(f"❌ FAIL: User with 5 votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 5")
                self.test_results.append({
                    "name": "Vote Countdown - User with 5 votes", 
                    "status": "FAIL", 
                    "details": f"User with 5 votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 5"
                })
        
        # Scenario 3: User with 10+ votes
        print("\n📋 Scenario 3: User with 10+ votes")
        # Simulate 5 more votes to reach 10
        self.simulate_voting(5, use_auth=True)
        
        # Get stats for user with 10 votes
        success, stats = self.test_get_stats(use_auth=True)
        if success:
            if stats.get('total_votes') >= 10 and stats.get('votes_until_recommendations') == 0 and stats.get('recommendations_available') == True:
                print("✅ PASS: User with 10+ votes shows votes_until_recommendations = 0 and recommendations_available = true")
                self.test_results.append({
                    "name": "Vote Countdown - User with 10+ votes", 
                    "status": "PASS", 
                    "details": "User with 10+ votes correctly shows votes_until_recommendations = 0 and recommendations_available = true"
                })
            else:
                print(f"❌ FAIL: User with 10+ votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 0")
                print(f"❌ FAIL: User with 10+ votes shows recommendations_available = {stats.get('recommendations_available')}, expected true")
                self.test_results.append({
                    "name": "Vote Countdown - User with 10+ votes", 
                    "status": "FAIL", 
                    "details": f"User with 10+ votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 0, recommendations_available = {stats.get('recommendations_available')}, expected true"
                })
        
        # Test with guest session as well
        print("\n📋 Testing with guest session")
        # Create a new session
        self.auth_token = None  # Clear auth token to use guest session
        self.test_create_session()
        
        # Scenario 1: New guest with 0 votes
        success, stats = self.test_get_stats(use_auth=False)
        if success:
            if stats.get('total_votes') == 0 and stats.get('votes_until_recommendations') == 10:
                print("✅ PASS: New guest with 0 votes shows votes_until_recommendations = 10")
                self.test_results.append({
                    "name": "Vote Countdown - New Guest (0 votes)", 
                    "status": "PASS", 
                    "details": "New guest with 0 votes correctly shows votes_until_recommendations = 10"
                })
            else:
                print(f"❌ FAIL: New guest with 0 votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 10")
                self.test_results.append({
                    "name": "Vote Countdown - New Guest (0 votes)", 
                    "status": "FAIL", 
                    "details": f"New guest with 0 votes shows votes_until_recommendations = {stats.get('votes_until_recommendations')}, expected 10"
                })
        
        # Print results
        print("\n📊 Vote Countdown Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        # Return overall success
        return all(result["status"] == "PASS" for result in self.test_results)

def main():
    tester = VoteCountdownTester()
    success = tester.test_vote_countdown()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())