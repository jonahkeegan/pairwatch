import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class MoviePreferenceAPITester:
    def __init__(self, base_url="https://c62d4176-fc83-406e-a031-ac397638707a.preview.emergentagent.com/api"):
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
    
    def test_get_current_user(self):
        """Test getting current user profile"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Get Current User", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200,
            auth=True
        )
        
        if success and 'id' in response:
            print(f"✅ Retrieved user profile for: {response.get('name')}")
            return True, response
        
        return False, response
    
    def test_update_profile(self):
        """Test updating user profile"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Update Profile", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        data = {
            "name": f"{self.test_user_name} Updated",
            "bio": "This is a test bio for the user profile",
            "avatar_url": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"
        }
        
        success, response = self.run_test(
            "Update Profile",
            "PUT",
            "auth/profile",
            200,
            data=data,
            auth=True
        )
        
        if success and response.get('name') == data['name']:
            print(f"✅ Profile updated successfully: {response.get('name')}")
            return True, response
        
        return False, response
    
    def test_get_voting_history(self):
        """Test getting user voting history"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Get Voting History", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Voting History",
            "GET",
            "profile/voting-history",
            200,
            auth=True
        )
        
        if success:
            print(f"✅ Retrieved voting history with {len(response)} entries")
            return True, response
        
        return False, response

    def test_initialize_content(self):
        """Test content initialization"""
        success, response = self.run_test(
            "Initialize Content",
            "POST",
            "initialize-content",
            200,
            data={}
        )
        return success, response

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

    def test_get_session(self):
        """Test getting session info"""
        if not self.session_id:
            print("❌ No session ID available")
            self.test_results.append({"name": "Get Session", "status": "SKIP", "details": "No session ID available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Session",
            "GET",
            f"session/{self.session_id}",
            200
        )
        return success, response

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
        
        # Verify that the pair contains items of the same type
        if success and 'item1' in response and 'item2' in response:
            if response['item1']['content_type'] == response['item2']['content_type']:
                print(f"✅ Verified: Both items are of type '{response['item1']['content_type']}'")
                
                # Verify OMDB poster data is present
                poster_checks = []
                
                # Check item1 poster
                if response['item1'].get('poster'):
                    poster_checks.append(f"✅ Item 1 ({response['item1']['title']}) has a poster URL")
                else:
                    poster_checks.append(f"⚠️ Item 1 ({response['item1']['title']}) is missing a poster URL")
                
                # Check item2 poster
                if response['item2'].get('poster'):
                    poster_checks.append(f"✅ Item 2 ({response['item2']['title']}) has a poster URL")
                else:
                    poster_checks.append(f"⚠️ Item 2 ({response['item2']['title']}) is missing a poster URL")
                
                # Check for additional OMDB metadata
                for idx, item in enumerate([response['item1'], response['item2']], 1):
                    if item.get('rating'):
                        poster_checks.append(f"✅ Item {idx} has IMDB rating: {item['rating']}")
                    if item.get('plot'):
                        poster_checks.append(f"✅ Item {idx} has plot description")
                    if item.get('director'):
                        poster_checks.append(f"✅ Item {idx} has director info: {item['director']}")
                    if item.get('actors'):
                        poster_checks.append(f"✅ Item {idx} has actors info")
                
                for check in poster_checks:
                    print(check)
                
                return True, response
            else:
                print(f"❌ Failed: Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'")
                self.test_results.append({"name": "Verify Same Content Type", "status": "FAIL", 
                                         "details": f"Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'"})
                return False, response
        
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

    def test_get_recommendations(self, use_auth=False):
        """Test getting recommendations (requires 36+ votes)"""
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
        
        # First check if we have enough votes
        _, stats = self.test_get_stats(use_auth)
        if not stats.get('recommendations_available', False):
            print(f"⚠️ Not enough votes for recommendations. Current: {stats.get('total_votes', 0)}, Required: 36")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", 
                                     "details": f"Not enough votes. Current: {stats.get('total_votes', 0)}, Required: 36"})
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

    def simulate_voting_to_threshold(self, use_auth=False):
        """Simulate voting until we reach the recommendation threshold (36 votes)"""
        print(f"\n🔄 Simulating votes to reach recommendation threshold using {'authenticated user' if use_auth else 'guest session'}...")
        
        for i in range(36):
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
            if (i+1) % 5 == 0:
                print(f"Progress: {i+1}/36 votes")
        
        print("✅ Successfully completed 36 votes")
        return True
    
    def test_auth_flow(self):
        """Test the complete authentication flow"""
        print("\n🔑 Testing Authentication Flow")
        
        # Register a new user
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            print("❌ Failed to register user, stopping auth flow tests")
            return False
        
        # Get current user profile
        self.test_get_current_user()
        
        # Update profile
        self.test_update_profile()
        
        # Get voting pair as authenticated user
        pair_success, pair = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            print("❌ Failed to get voting pair as authenticated user")
            return False
        
        # Submit a vote as authenticated user
        vote_success, _ = self.test_submit_vote(
            pair['item1']['id'], 
            pair['item2']['id'],
            pair['content_type'],
            use_auth=True
        )
        
        if not vote_success:
            print("❌ Failed to submit vote as authenticated user")
            return False
        
        # Get stats as authenticated user
        self.test_get_stats(use_auth=True)
        
        # Get voting history (should be empty or have one vote)
        self.test_get_voting_history()
        
        # Logout (clear token)
        old_token = self.auth_token
        self.auth_token = None
        
        # Login again
        login_success, _ = self.test_user_login()
        if not login_success:
            print("❌ Failed to login with existing user")
            return False
        
        # Verify token changed
        if old_token == self.auth_token:
            print("⚠️ Warning: Login token is the same as registration token")
        else:
            print("✅ Login token differs from registration token")
        
        # Get current user profile again
        self.test_get_current_user()
        
        return True

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("\n🚀 Starting Movie Preference API Tests\n")
        
        # Initialize content
        self.test_initialize_content()
        
        # Test 1: Guest Session Flow
        print("\n📋 Testing Guest Session Flow")
        
        # Create session
        session_success, _ = self.test_create_session()
        if not session_success:
            print("❌ Failed to create session, stopping tests")
            return
        
        # Get session info
        self.test_get_session()
        
        # Get a voting pair
        pair_success, pair = self.test_get_voting_pair()
        if not pair_success:
            print("❌ Failed to get voting pair, stopping tests")
            return
        
        # Submit a vote
        self.test_submit_vote(
            pair['item1']['id'], 
            pair['item2']['id'],
            pair['content_type']
        )
        
        # Get user stats
        self.test_get_stats()
        
        # Try to get recommendations (should fail with not enough votes)
        self.test_get_recommendations()
        
        # Simulate voting to threshold
        if self.simulate_voting_to_threshold():
            # Now we should be able to get recommendations
            self.test_get_recommendations()
        
        # Test 2: Authentication Flow
        print("\n📋 Testing Authentication Flow")
        self.test_auth_flow()
        
        # Test 3: Authenticated Voting Flow
        print("\n📋 Testing Authenticated Voting Flow")
        
        # Simulate voting to threshold with authenticated user
        if self.auth_token and self.simulate_voting_to_threshold(use_auth=True):
            # Get recommendations as authenticated user
            self.test_get_recommendations(use_auth=True)
            
            # Get voting history after multiple votes
            self.test_get_voting_history()
        
        # Print results
        print(f"\n📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        # Print detailed results
        print("\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = MoviePreferenceAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
