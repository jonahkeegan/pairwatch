import requests
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backend_api_test")

# Base URL for the API
BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"

# Test user credentials
TEST_USER_EMAIL = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_USER_NAME = f"Test User {datetime.now().strftime('%H%M%S')}"

def test_session_creation():
    """Test session creation endpoint"""
    logger.info("Testing session creation...")
    
    try:
        response = requests.post(f"{BASE_URL}/session")
        
        if response.status_code == 200:
            session_data = response.json()
            if 'session_id' in session_data:
                logger.info(f"✅ Session created with ID: {session_data['session_id']}")
                return True, session_data
            else:
                logger.error("❌ Session creation response missing session_id")
                return False, None
        else:
            logger.error(f"❌ Session creation failed with status code: {response.status_code}")
            return False, None
    except Exception as e:
        logger.error(f"❌ Session creation error: {str(e)}")
        return False, None

def test_voting_pair(session_id):
    """Test voting pair endpoint with session_id"""
    logger.info("Testing voting pair endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/voting-pair", params={"session_id": session_id})
        
        if response.status_code == 200:
            voting_pair = response.json()
            if 'item1' in voting_pair and 'item2' in voting_pair:
                logger.info(f"✅ Voting pair retrieved: {voting_pair['item1']['title']} vs {voting_pair['item2']['title']}")
                
                # Check for poster URLs
                if voting_pair['item1'].get('poster'):
                    logger.info(f"✅ Item 1 has poster URL: {voting_pair['item1']['poster'][:50]}...")
                else:
                    logger.warning("⚠️ Item 1 missing poster URL")
                
                if voting_pair['item2'].get('poster'):
                    logger.info(f"✅ Item 2 has poster URL: {voting_pair['item2']['poster'][:50]}...")
                else:
                    logger.warning("⚠️ Item 2 missing poster URL")
                
                return True, voting_pair
            else:
                logger.error("❌ Voting pair response missing items")
                return False, None
        else:
            logger.error(f"❌ Voting pair retrieval failed with status code: {response.status_code}")
            return False, None
    except Exception as e:
        logger.error(f"❌ Voting pair error: {str(e)}")
        return False, None

def test_user_registration():
    """Test user registration endpoint"""
    logger.info("Testing user registration...")
    
    try:
        data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": TEST_USER_NAME
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=data)
        
        if response.status_code == 200:
            user_data = response.json()
            if 'access_token' in user_data and 'user' in user_data:
                logger.info(f"✅ User registered with ID: {user_data['user']['id']}")
                return True, user_data
            else:
                logger.error("❌ User registration response missing access_token or user data")
                return False, None
        else:
            logger.error(f"❌ User registration failed with status code: {response.status_code}")
            return False, None
    except Exception as e:
        logger.error(f"❌ User registration error: {str(e)}")
        return False, None

def test_user_login(email, password):
    """Test user login endpoint"""
    logger.info("Testing user login...")
    
    try:
        data = {
            "email": email,
            "password": password
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=data)
        
        if response.status_code == 200:
            login_data = response.json()
            if 'access_token' in login_data and 'user' in login_data:
                logger.info(f"✅ User logged in with ID: {login_data['user']['id']}")
                return True, login_data
            else:
                logger.error("❌ User login response missing access_token or user data")
                return False, None
        else:
            logger.error(f"❌ User login failed with status code: {response.status_code}")
            return False, None
    except Exception as e:
        logger.error(f"❌ User login error: {str(e)}")
        return False, None

def run_tests():
    """Run all tests"""
    logger.info("Starting backend API tests...")
    
    # Test session creation
    session_success, session_data = test_session_creation()
    if not session_success:
        logger.error("❌ Session creation test failed")
        return False
    
    session_id = session_data['session_id']
    
    # Test voting pair with session_id
    voting_pair_success, voting_pair = test_voting_pair(session_id)
    if not voting_pair_success:
        logger.error("❌ Voting pair test failed")
        return False
    
    # Test user registration
    registration_success, registration_data = test_user_registration()
    if not registration_success:
        logger.error("❌ User registration test failed")
        return False
    
    # Test user login
    login_success, login_data = test_user_login(TEST_USER_EMAIL, TEST_USER_PASSWORD)
    if not login_success:
        logger.error("❌ User login test failed")
        return False
    
    logger.info("✅ All backend API tests passed!")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)