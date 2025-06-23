import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class AutoRecommendationTester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
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
        
        print(f"🔍 Testing Automatic AI Recommendation System at: {self.base_url}")
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
            start_time = time.time()
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            response_time = time.time() - start_time
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}, Response time: {response_time:.2f}s")
                self.test_results.append({
                    "name": name, 
                    "status": "PASS", 
                    "details": f"Status: {response.status_code}, Response time: {response_time:.2f}s"
                })
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({
                    "name": name, 
                    "status": "FAIL", 
                    "details": f"Expected {expected_status}, got {response.status_code}"
                })

            try:
                return success, response.json() if response.text else {}, response_time
            except:
                return success, {}, response_time

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({"name": name, "status": "ERROR", "details": str(e)})
            return False, {}, 0

    def test_user_registration(self):
        """Test user registration"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
            "name": self.test_user_name
        }
        
        success, response, _ = self.run_test(
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

    def test_get_stats(self):
        """Test getting user stats"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Get Stats", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response, _ = self.run_test(
            "Get User Stats",
            "GET",
            "stats",
            200,
            auth=True
        )
        
        if success:
            print(f"Total votes: {response.get('total_votes')}")
            print(f"Movie votes: {response.get('movie_votes')}")
            print(f"Series votes: {response.get('series_votes')}")
            print(f"Votes until recommendations: {response.get('votes_until_recommendations')}")
            print(f"Recommendations available: {response.get('recommendations_available')}")
            print(f"User authenticated: {response.get('user_authenticated')}")
        
        return success, response

    def test_get_voting_pair(self):
        """Test getting a voting pair"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Get Voting Pair", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response, _ = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=True
        )
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type):
        """Test submitting a vote"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Submit Vote", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        success, response, response_time = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=True
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            print(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response, response_time
        
        return success, response, response_time

    def test_get_recommendations(self):
        """Test getting recommendations"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response, response_time = self.run_test(
            "Get Recommendations",
            "GET",
            "recommendations",
            200,
            auth=True
        )
        
        if success and isinstance(response, list):
            print(f"✅ Received {len(response)} recommendations in {response_time:.2f}s")
            
            # Check for recommendation content
            for i, rec in enumerate(response[:3]):  # Show first 3 recommendations
                print(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
        
        return success, response, response_time

    def test_content_interaction(self, content_id, interaction_type):
        """Test content interaction (watched, want_to_watch, not_interested)"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": f"Content Interaction ({interaction_type})", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        success, response, response_time = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=True
        )
        
        if success and response.get('success') == True:
            print(f"✅ Content interaction '{interaction_type}' recorded successfully in {response_time:.2f}s")
            return True, response, response_time
        
        return success, response, response_time

    def simulate_voting_to_threshold(self, target_votes=10):
        """Simulate voting until we reach the recommendation threshold"""
        print(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes)...")
        
        # Get current vote count
        _, stats = self.test_get_stats()
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        print(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        vote_response_times = []
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair()
            if not success:
                print(f"❌ Failed to get voting pair on iteration {i+1}")
                return False, []
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _, response_time = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type']
            )
            
            vote_response_times.append(response_time)
            
            if not vote_success:
                print(f"❌ Failed to submit vote on iteration {i+1}")
                return False, []
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                print(f"Progress: {i+1}/{votes_needed} votes")
        
        print(f"✅ Successfully completed {votes_needed} votes")
        return True, vote_response_times

    def test_automatic_recommendation_system(self):
        """Test the complete automatic AI recommendation system"""
        print("\n🚀 Testing Automatic AI Recommendation System\n")
        
        # Step 1: User Registration & Initial Voting
        print("\n📋 Step 1: User Registration & Initial Voting")
        
        # Register a new user
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            print("❌ Failed to register user, stopping test")
            return False
        
        # Get initial stats - should show 10 votes until recommendations
        _, stats = self.test_get_stats()
        if stats.get('recommendations_available') == True:
            print("❌ Failed: New user should not have recommendations available")
            return False
        
        # Submit exactly 10 votes to reach recommendation threshold
        vote_success, vote_times = self.simulate_voting_to_threshold(target_votes=10)
        if not vote_success:
            print("❌ Failed to submit votes, stopping test")
            return False
        
        # Calculate average vote response time
        avg_vote_time = sum(vote_times) / len(vote_times) if vote_times else 0
        print(f"Average vote submission response time: {avg_vote_time:.2f}s")
        
        # Step 2: Automatic Storage & Retrieval
        print("\n📋 Step 2: Automatic Storage & Retrieval")
        
        # Wait a moment for background recommendation generation
        print("Waiting for background recommendation generation (5 seconds)...")
        time.sleep(5)
        
        # Call /api/stats to confirm recommendations_available = true
        stats_success, stats = self.test_get_stats()
        if not stats_success or not stats.get('recommendations_available'):
            print("❌ Failed: Recommendations should be available after 10 votes")
            return False
        
        print("✅ Verified: recommendations_available = true after 10 votes")
        
        # Call /api/recommendations to verify stored recommendations are returned
        rec_success, recommendations, rec_time = self.test_get_recommendations()
        if not rec_success or not recommendations:
            print("❌ Failed: No recommendations returned")
            return False
        
        print(f"✅ Verified: {len(recommendations)} recommendations returned in {rec_time:.2f}s")
        
        # Verify recommendations are returned quickly (stored, not generated on-demand)
        if rec_time > 1.0:  # If it takes more than 1 second, it might be generating on-demand
            print(f"⚠️ Warning: Recommendations took {rec_time:.2f}s to return, which suggests they might be generated on-demand")
        else:
            print(f"✅ Verified: Recommendations returned quickly ({rec_time:.2f}s), indicating they were stored")
        
        # Step 3: Automatic Refresh Triggers
        print("\n📋 Step 3: Automatic Refresh Triggers")
        
        # Submit 5 more votes (total 15) to test milestone trigger
        print("\nSubmitting 5 more votes to reach milestone trigger (15 votes)...")
        vote_success, _ = self.simulate_voting_to_threshold(target_votes=15)
        if not vote_success:
            print("❌ Failed to submit additional votes, stopping test")
            return False
        
        # Wait a moment for background recommendation regeneration
        print("Waiting for background recommendation regeneration (5 seconds)...")
        time.sleep(5)
        
        # Get recommendations again to verify they've been refreshed
        _, new_recommendations, new_rec_time = self.test_get_recommendations()
        
        # Check if recommendations have changed
        if len(new_recommendations) == len(recommendations):
            # Compare first recommendation title to see if they've changed
            if new_recommendations and recommendations and new_recommendations[0].get('title') == recommendations[0].get('title'):
                print("⚠️ Warning: Recommendations may not have been refreshed after milestone trigger")
            else:
                print("✅ Verified: Recommendations were refreshed after milestone trigger")
        else:
            print(f"✅ Verified: Number of recommendations changed from {len(recommendations)} to {len(new_recommendations)}")
        
        # Mark content as "watched" to test interaction triggers
        if new_recommendations:
            content_id = None
            for rec in new_recommendations:
                if 'imdb_id' in rec:
                    content_id = rec.get('imdb_id')
                    break
            
            if content_id:
                print(f"\nMarking content as 'watched' to test interaction trigger...")
                interaction_success, _, _ = self.test_content_interaction(content_id, "watched")
                if interaction_success:
                    print("✅ Successfully marked content as 'watched'")
                    
                    # Wait a moment for background recommendation regeneration
                    print("Waiting for background recommendation regeneration (5 seconds)...")
                    time.sleep(5)
                    
                    # Get recommendations again to verify they've been refreshed
                    _, watched_recommendations, _ = self.test_get_recommendations()
                    
                    # Check if recommendations have changed
                    if len(watched_recommendations) != len(new_recommendations):
                        print(f"✅ Verified: Number of recommendations changed after 'watched' interaction")
                    else:
                        print("⚠️ Note: Number of recommendations didn't change after 'watched' interaction")
                
                # Mark another content as "not_interested" to test interaction triggers
                if len(new_recommendations) > 1:
                    content_id = new_recommendations[1].get('imdb_id')
                    if content_id:
                        print(f"\nMarking content as 'not_interested' to test interaction trigger...")
                        interaction_success, _, _ = self.test_content_interaction(content_id, "not_interested")
                        if interaction_success:
                            print("✅ Successfully marked content as 'not_interested'")
                            
                            # Wait a moment for background recommendation regeneration
                            print("Waiting for background recommendation regeneration (5 seconds)...")
                            time.sleep(5)
                            
                            # Get recommendations again to verify they've been refreshed
                            _, not_interested_recommendations, _ = self.test_get_recommendations()
                            
                            # Check if recommendations have changed
                            if len(not_interested_recommendations) != len(watched_recommendations):
                                print(f"✅ Verified: Number of recommendations changed after 'not_interested' interaction")
                            else:
                                print("⚠️ Note: Number of recommendations didn't change after 'not_interested' interaction")
        
        # Step 4: Performance & Background Processing
        print("\n📋 Step 4: Performance & Background Processing")
        
        # Verify vote submission APIs respond quickly even during background generation
        print("\nTesting vote submission performance during background processing...")
        
        # Submit a vote to trigger background processing
        success, pair = self.test_get_voting_pair()
        if success:
            _, _, vote_time = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type']
            )
            
            # Submit another vote immediately to check if it's blocked
            success, pair = self.test_get_voting_pair()
            if success:
                _, _, second_vote_time = self.test_submit_vote(
                    pair['item1']['id'], 
                    pair['item2']['id'],
                    pair['content_type']
                )
                
                print(f"First vote response time: {vote_time:.2f}s")
                print(f"Second vote response time: {second_vote_time:.2f}s")
                
                if second_vote_time > vote_time * 2:
                    print(f"⚠️ Warning: Second vote took significantly longer ({second_vote_time:.2f}s vs {vote_time:.2f}s)")
                else:
                    print(f"✅ Verified: Vote submission APIs respond quickly even during background processing")
        
        # Test rapid votes to check system efficiency
        print("\nTesting system efficiency with rapid votes...")
        rapid_vote_times = []
        
        for i in range(5):
            success, pair = self.test_get_voting_pair()
            if success:
                _, _, vote_time = self.test_submit_vote(
                    pair['item1']['id'], 
                    pair['item2']['id'],
                    pair['content_type']
                )
                rapid_vote_times.append(vote_time)
        
        if rapid_vote_times:
            avg_rapid_vote_time = sum(rapid_vote_times) / len(rapid_vote_times)
            print(f"Average rapid vote response time: {avg_rapid_vote_time:.2f}s")
            
            if avg_rapid_vote_time > avg_vote_time * 1.5:
                print(f"⚠️ Warning: Rapid votes took longer on average ({avg_rapid_vote_time:.2f}s vs {avg_vote_time:.2f}s)")
            else:
                print(f"✅ Verified: System handles multiple rapid votes efficiently")
        
        # Print results
        print(f"\n📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        # Print detailed results
        print("\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = AutoRecommendationTester()
    success = tester.test_automatic_recommendation_system()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())