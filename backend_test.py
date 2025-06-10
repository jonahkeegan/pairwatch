import requests
import unittest
import time
import sys
from datetime import datetime

class MoviePreferenceAPITester:
    def __init__(self, base_url="https://c62d4176-fc83-406e-a031-ac397638707a.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

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

    def test_get_voting_pair(self):
        """Test getting a voting pair"""
        if not self.session_id:
            print("❌ No session ID available")
            self.test_results.append({"name": "Get Voting Pair", "status": "SKIP", "details": "No session ID available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            f"voting-pair/{self.session_id}",
            200
        )
        
        # Verify that the pair contains items of the same type
        if success and 'item1' in response and 'item2' in response:
            if response['item1']['content_type'] == response['item2']['content_type']:
                print(f"✅ Verified: Both items are of type '{response['item1']['content_type']}'")
                return True, response
            else:
                print(f"❌ Failed: Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'")
                self.test_results.append({"name": "Verify Same Content Type", "status": "FAIL", 
                                         "details": f"Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'"})
                return False, response
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type):
        """Test submitting a vote"""
        if not self.session_id:
            print("❌ No session ID available")
            self.test_results.append({"name": "Submit Vote", "status": "SKIP", "details": "No session ID available"})
            return False, {}
        
        data = {
            "session_id": self.session_id,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            print(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_get_stats(self):
        """Test getting user stats"""
        if not self.session_id:
            print("❌ No session ID available")
            self.test_results.append({"name": "Get Stats", "status": "SKIP", "details": "No session ID available"})
            return False, {}
        
        success, response = self.run_test(
            "Get User Stats",
            "GET",
            f"stats/{self.session_id}",
            200
        )
        
        if success:
            print(f"Total votes: {response.get('total_votes')}")
            print(f"Movie votes: {response.get('movie_votes')}")
            print(f"Series votes: {response.get('series_votes')}")
            print(f"Votes until recommendations: {response.get('votes_until_recommendations')}")
            print(f"Recommendations available: {response.get('recommendations_available')}")
        
        return success, response

    def test_get_recommendations(self):
        """Test getting recommendations (requires 36+ votes)"""
        if not self.session_id:
            print("❌ No session ID available")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", "details": "No session ID available"})
            return False, {}
        
        # First check if we have enough votes
        _, stats = self.test_get_stats()
        if not stats.get('recommendations_available', False):
            print(f"⚠️ Not enough votes for recommendations. Current: {stats.get('total_votes', 0)}, Required: 36")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", 
                                     "details": f"Not enough votes. Current: {stats.get('total_votes', 0)}, Required: 36"})
            return False, {}
        
        success, response = self.run_test(
            "Get Recommendations",
            "GET",
            f"recommendations/{self.session_id}",
            200
        )
        
        if success and isinstance(response, list):
            print(f"✅ Received {len(response)} recommendations")
            for i, rec in enumerate(response):
                print(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
        
        return success, response

    def simulate_voting_to_threshold(self):
        """Simulate voting until we reach the recommendation threshold (36 votes)"""
        print("\n🔄 Simulating votes to reach recommendation threshold...")
        
        for i in range(36):
            # Get a voting pair
            success, pair = self.test_get_voting_pair()
            if not success:
                print(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type']
            )
            
            if not vote_success:
                print(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0:
                print(f"Progress: {i+1}/36 votes")
        
        print("✅ Successfully completed 36 votes")
        return True

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("\n🚀 Starting Movie Preference API Tests\n")
        
        # Initialize content
        self.test_initialize_content()
        
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
