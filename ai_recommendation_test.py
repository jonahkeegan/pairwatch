import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class AIRecommendationTester:
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
        
        print(f"🔍 Testing AI Recommendation System at: {self.base_url}")
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

    def test_initialize_content(self):
        """Test content initialization"""
        success, response = self.run_test(
            "Initialize Content",
            "POST",
            "initialize-content",
            200,
            data={}
        )
        
        if success:
            print(f"✅ Content initialized successfully")
        
        return success, response

    def test_get_voting_pair(self):
        """Test getting a voting pair"""
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=True
        )
        
        if success and 'item1' in response and 'item2' in response:
            print(f"✅ Got voting pair: {response['item1']['title']} vs {response['item2']['title']}")
            return True, response
        
        return success, response

    def test_content_interaction(self, content_id, interaction_type):
        """Test content interaction (watched, want_to_watch, not_interested)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        success, response = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=True
        )
        
        if success and response.get('success') == True:
            print(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response

    def test_get_content_user_status(self, content_id):
        """Test getting user's interaction status with content"""
        success, response = self.run_test(
            "Get Content User Status",
            "GET",
            f"content/{content_id}/user-status",
            200,
            auth=True
        )
        
        if success:
            print(f"✅ Content status retrieved:")
            print(f"  Has watched: {response.get('has_watched', False)}")
            print(f"  Wants to watch: {response.get('wants_to_watch', False)}")
            print(f"  Not interested: {response.get('not_interested', False)}")
            
            return True, response
        
        return False, response

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
        
        if success and response.get('vote_recorded') == True:
            print(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_generate_ml_recommendations(self):
        """Test generating ML-powered recommendations"""
        success, response = self.run_test(
            "Generate ML Recommendations",
            "POST",
            "recommendations/generate",
            200,
            data={},
            auth=True
        )
        
        if success:
            print(f"✅ ML Recommendations generated: {response.get('recommendations_generated', 0)} items")
            return True, response
        
        return False, response

    def test_get_watchlist(self, watchlist_type="algo_predicted"):
        """Test getting user watchlist"""
        success, response = self.run_test(
            f"Get Watchlist ({watchlist_type})",
            "GET",
            f"watchlist/{watchlist_type}",
            200,
            auth=True
        )
        
        if success:
            print(f"✅ Retrieved {watchlist_type} watchlist with {response.get('total_count', 0)} items")
            
            # Print watchlist items
            if response.get('items'):
                for i, item in enumerate(response['items']):
                    print(f"  {i+1}. {item['content']['title']} ({item['content']['year']})")
            
            return True, response
        
        return False, response

    def test_remove_from_watchlist(self, watchlist_id):
        """Test removing item from watchlist"""
        success, response = self.run_test(
            "Remove from Watchlist",
            "DELETE",
            f"watchlist/{watchlist_id}",
            200,
            auth=True
        )
        
        if success and response.get('success') == True:
            print(f"✅ Item removed from watchlist successfully")
            return True, response
        
        return False, response

    def simulate_voting_to_threshold(self, num_votes=10):
        """Simulate voting to generate enough data for recommendations"""
        print(f"\n🔄 Simulating {num_votes} votes to build user profile...")
        
        for i in range(num_votes):
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
                print(f"Progress: {i+1}/{num_votes} votes")
        
        print(f"✅ Successfully completed {num_votes} votes")
        return True

    def test_ai_recommendation_tile_removal(self):
        """Test the AI recommendation tile removal system"""
        print("\n🧪 Testing AI Recommendation Tile Removal System")
        
        # 1. Get the watchlist
        watchlist_success, watchlist = self.test_get_watchlist("algo_predicted")
        if not watchlist_success or not watchlist.get('items'):
            print("❌ Failed to get algo watchlist or watchlist is empty")
            return False
        
        # 2. Test "Watched" button functionality
        if len(watchlist['items']) > 0:
            first_item = watchlist['items'][0]
            content_id = first_item['content']['id']
            watchlist_id = first_item['watchlist_id']
            
            # Mark as watched
            watched_success, _ = self.test_content_interaction(content_id, "watched")
            if not watched_success:
                print("❌ Failed to mark recommendation as watched")
                return False
            
            # Verify content status updated
            status_success, status = self.test_get_content_user_status(content_id)
            if not status_success or not status.get('has_watched', False):
                print("❌ Failed to verify content was marked as watched")
                return False
            
            print("✅ Successfully tested 'Watched' recommendation removal")
        
        # 3. Test "Not Interested" button functionality
        if len(watchlist['items']) > 1:
            second_item = watchlist['items'][1]
            content_id = second_item['content']['id']
            watchlist_id = second_item['watchlist_id']
            
            # Mark as not interested
            not_interested_success, _ = self.test_content_interaction(content_id, "not_interested")
            if not not_interested_success:
                print("❌ Failed to mark recommendation as not interested")
                return False
            
            # Verify content status updated
            status_success, status = self.test_get_content_user_status(content_id)
            if not status_success or not status.get('not_interested', False):
                print("❌ Failed to verify content was marked as not interested")
                return False
            
            print("✅ Successfully tested 'Not Interested' recommendation removal")
        
        # 4. Get updated watchlist to verify removals
        updated_success, updated_watchlist = self.test_get_watchlist("algo_predicted")
        if not updated_success:
            print("❌ Failed to get updated watchlist")
            return False
        
        # Check if items were removed from the watchlist
        removed_items = []
        for item in watchlist['items']:
            if not any(updated_item['watchlist_id'] == item['watchlist_id'] for updated_item in updated_watchlist.get('items', [])):
                removed_items.append(item['content']['title'])
        
        if removed_items:
            print(f"✅ Verified {len(removed_items)} items were removed from watchlist:")
            for title in removed_items:
                print(f"  - {title}")
            return True
        else:
            print("⚠️ No items were removed from watchlist as expected")
            return False

    def run_all_tests(self):
        """Run all AI recommendation interaction system tests"""
        print("\n🚀 Starting AI Recommendation Interaction System Tests\n")
        
        # 1. Initialize content
        init_success, _ = self.test_initialize_content()
        if not init_success:
            print("❌ Failed to initialize content, stopping tests")
            return False
        
        # 2. Register a new user
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            print("❌ Failed to register user, stopping tests")
            return False
        
        # 3. Simulate voting to build user profile
        self.simulate_voting_to_threshold(10)
        
        # 4. Generate ML recommendations
        gen_success, _ = self.test_generate_ml_recommendations()
        if not gen_success:
            print("❌ Failed to generate ML recommendations, stopping tests")
            return False
        
        # 5. Test AI recommendation tile removal system
        tile_removal_success = self.test_ai_recommendation_tile_removal()
        if not tile_removal_success:
            print("⚠️ AI recommendation tile removal test had issues")
        
        # Print results
        print(f"\n📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        # Print detailed results
        print("\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = AIRecommendationTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())