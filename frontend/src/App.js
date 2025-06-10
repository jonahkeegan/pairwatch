import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  // Authentication state
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  
  // App state
  const [sessionId, setSessionId] = useState(null);
  const [currentPair, setCurrentPair] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [voting, setVoting] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [votingHistory, setVotingHistory] = useState([]);
  const [contentInitialized, setContentInitialized] = useState(false);

  // Auth form state
  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    name: ''
  });

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    name: '',
    bio: '',
    avatar_url: ''
  });

  // Configure axios with auth token
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      getCurrentUser();
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Initialize app
  useEffect(() => {
    initializeApp();
  }, []);

  const getCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
      setProfileForm({
        name: response.data.name,
        bio: response.data.bio || '',
        avatar_url: response.data.avatar_url || ''
      });
    } catch (error) {
      console.error('Failed to get current user:', error);
      logout();
    }
  };

  const initializeApp = async () => {
    try {
      setLoading(true);
      
      // Initialize content first
      if (!contentInitialized) {
        console.log('Initializing content...');
        await axios.post(`${API}/initialize-content`);
        setContentInitialized(true);
      }
      
      // If not logged in, create a guest session
      if (!token) {
        const sessionResponse = await axios.post(`${API}/session`);
        setSessionId(sessionResponse.data.session_id);
      }
      
      // Get initial stats and voting pair
      await updateStats();
      await getNextPair();
      
    } catch (error) {
      console.error('Initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateStats = async () => {
    try {
      const params = {};
      if (!user && sessionId) {
        params.session_id = sessionId;
      }
      
      const statsResponse = await axios.get(`${API}/stats`, { params });
      setUserStats(statsResponse.data);
      
      // Check if recommendations are available
      if (statsResponse.data.recommendations_available && !showRecommendations) {
        const recResponse = await axios.get(`${API}/recommendations`, { params });
        setRecommendations(recResponse.data);
      }
    } catch (error) {
      console.error('Stats error:', error);
    }
  };

  const getNextPair = async () => {
    try {
      const params = {};
      if (!user && sessionId) {
        params.session_id = sessionId;
      }
      
      const pairResponse = await axios.get(`${API}/voting-pair`, { params });
      setCurrentPair(pairResponse.data);
    } catch (error) {
      console.error('Pair error:', error);
    }
  };

  const handleVote = async (winnerId, loserId) => {
    if (voting || !currentPair) return;
    
    try {
      setVoting(true);
      
      const voteData = {
        winner_id: winnerId,
        loser_id: loserId,
        content_type: currentPair.content_type
      };
      
      if (!user && sessionId) {
        voteData.session_id = sessionId;
      }
      
      await axios.post(`${API}/vote`, voteData);
      
      // Update stats and get next pair
      await updateStats();
      await getNextPair();
      
    } catch (error) {
      console.error('Vote error:', error);
    } finally {
      setVoting(false);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    
    try {
      const endpoint = authMode === 'login' ? 'login' : 'register';
      const response = await axios.post(`${API}/auth/${endpoint}`, authForm);
      
      const { access_token, user: userData } = response.data;
      
      // Store token and set user
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      setShowAuth(false);
      
      // Reset form
      setAuthForm({ email: '', password: '', name: '' });
      
      // Refresh app state
      await updateStats();
      await getNextPair();
      
    } catch (error) {
      console.error('Auth error:', error);
      alert(error.response?.data?.detail || 'Authentication failed');
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    axios.defaults.headers.common['Authorization'] = '';
    
    // Reinitialize as guest
    initializeApp();
  };

  const updateProfile = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.put(`${API}/auth/profile`, profileForm);
      setUser(response.data);
      alert('Profile updated successfully!');
    } catch (error) {
      console.error('Profile update error:', error);
      alert('Failed to update profile');
    }
  };

  const getVotingHistory = async () => {
    try {
      const response = await axios.get(`${API}/profile/voting-history`);
      setVotingHistory(response.data);
    } catch (error) {
      console.error('Voting history error:', error);
    }
  };

  const toggleRecommendations = () => {
    setShowRecommendations(!showRecommendations);
  };

  const toggleProfile = async () => {
    if (!showProfile && user) {
      await getVotingHistory();
    }
    setShowProfile(!showProfile);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-xl">Setting up your movie preferences...</p>
        </div>
      </div>
    );
  }

  // Authentication Modal
  if (showAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
        <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-8 w-full max-w-md">
          <h2 className="text-3xl font-bold text-white mb-6 text-center">
            {authMode === 'login' ? 'Login' : 'Sign Up'}
          </h2>
          
          <form onSubmit={handleAuth} className="space-y-4">
            {authMode === 'register' && (
              <input
                type="text"
                placeholder="Your Name"
                value={authForm.name}
                onChange={(e) => setAuthForm({...authForm, name: e.target.value})}
                className="w-full p-3 rounded-lg bg-white bg-opacity-20 text-white placeholder-gray-300 border border-white border-opacity-30 focus:outline-none focus:border-opacity-50"
                required
              />
            )}
            
            <input
              type="email"
              placeholder="Email"
              value={authForm.email}
              onChange={(e) => setAuthForm({...authForm, email: e.target.value})}
              className="w-full p-3 rounded-lg bg-white bg-opacity-20 text-white placeholder-gray-300 border border-white border-opacity-30 focus:outline-none focus:border-opacity-50"
              required
            />
            
            <input
              type="password"
              placeholder="Password"
              value={authForm.password}
              onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
              className="w-full p-3 rounded-lg bg-white bg-opacity-20 text-white placeholder-gray-300 border border-white border-opacity-30 focus:outline-none focus:border-opacity-50"
              required
            />
            
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors"
            >
              {authMode === 'login' ? 'Login' : 'Sign Up'}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <p className="text-white mb-4">
              {authMode === 'login' ? "Don't have an account?" : "Already have an account?"}
            </p>
            <button
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
              className="text-blue-300 hover:text-blue-200 underline"
            >
              {authMode === 'login' ? 'Sign Up' : 'Login'}
            </button>
          </div>
          
          <div className="mt-4 text-center">
            <button
              onClick={() => setShowAuth(false)}
              className="text-gray-300 hover:text-white"
            >
              Continue as Guest
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Profile Page
  if (showProfile && user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-8">
            <div className="flex justify-between items-center mb-8">
              <h1 className="text-4xl font-bold text-white">My Profile</h1>
              <button
                onClick={toggleProfile}
                className="text-blue-300 hover:text-blue-200"
              >
                Back to Voting
              </button>
            </div>
            
            {/* Profile Info */}
            <div className="grid md:grid-cols-2 gap-8 mb-8">
              <div>
                <h2 className="text-2xl font-bold text-white mb-4">Profile Information</h2>
                <form onSubmit={updateProfile} className="space-y-4">
                  <input
                    type="text"
                    placeholder="Your Name"
                    value={profileForm.name}
                    onChange={(e) => setProfileForm({...profileForm, name: e.target.value})}
                    className="w-full p-3 rounded-lg bg-white bg-opacity-20 text-white placeholder-gray-300 border border-white border-opacity-30 focus:outline-none focus:border-opacity-50"
                  />
                  
                  <textarea
                    placeholder="Bio (optional)"
                    value={profileForm.bio}
                    onChange={(e) => setProfileForm({...profileForm, bio: e.target.value})}
                    rows={3}
                    className="w-full p-3 rounded-lg bg-white bg-opacity-20 text-white placeholder-gray-300 border border-white border-opacity-30 focus:outline-none focus:border-opacity-50"
                  />
                  
                  <input
                    type="url"
                    placeholder="Avatar URL (optional)"
                    value={profileForm.avatar_url}
                    onChange={(e) => setProfileForm({...profileForm, avatar_url: e.target.value})}
                    className="w-full p-3 rounded-lg bg-white bg-opacity-20 text-white placeholder-gray-300 border border-white border-opacity-30 focus:outline-none focus:border-opacity-50"
                  />
                  
                  <button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors"
                  >
                    Update Profile
                  </button>
                </form>
              </div>
              
              <div>
                <h2 className="text-2xl font-bold text-white mb-4">Statistics</h2>
                <div className="space-y-4 text-white">
                  <div className="bg-white bg-opacity-10 rounded-lg p-4">
                    <div className="text-3xl font-bold">{user.total_votes}</div>
                    <div className="text-blue-200">Total Votes</div>
                  </div>
                  <div className="bg-white bg-opacity-10 rounded-lg p-4">
                    <div className="text-lg">Member since</div>
                    <div className="text-blue-200">{new Date(user.created_at).toLocaleDateString()}</div>
                  </div>
                  {user.last_login && (
                    <div className="bg-white bg-opacity-10 rounded-lg p-4">
                      <div className="text-lg">Last active</div>
                      <div className="text-blue-200">{new Date(user.last_login).toLocaleDateString()}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Voting History */}
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Recent Voting History</h2>
              <div className="grid gap-4 max-h-96 overflow-y-auto">
                {votingHistory.slice(0, 20).map((vote) => (
                  <div key={vote.id} className="bg-white bg-opacity-10 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="text-green-400 font-bold">✓</div>
                      <div>
                        <div className="text-white font-bold">{vote.winner.title}</div>
                        <div className="text-gray-300 text-sm">beat {vote.loser.title}</div>
                      </div>
                    </div>
                    <div className="text-blue-200 text-sm">
                      {new Date(vote.voted_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Recommendations Page
  if (showRecommendations && recommendations.length > 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-white mb-2">Your Recommendations</h1>
            <p className="text-blue-200">Based on your {userStats?.total_votes} votes</p>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-8">
            {recommendations.map((rec, index) => (
              <div key={index} className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-6 text-white">
                {rec.poster && (
                  <img 
                    src={rec.poster} 
                    alt={rec.title}
                    className="w-full h-64 object-cover rounded-lg mb-4"
                  />
                )}
                <h3 className="text-xl font-bold mb-2">{rec.title}</h3>
                <p className="text-blue-200 text-sm">{rec.reason}</p>
              </div>
            ))}
          </div>
          
          <div className="text-center">
            <button
              onClick={toggleRecommendations}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
            >
              Continue Voting
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      {/* Header */}
      <div className="flex justify-between items-center p-4">
        <div className="text-white">
          <h1 className="text-2xl font-bold">Movie Preferences</h1>
        </div>
        
        <div className="flex items-center space-x-4">
          {user ? (
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleProfile}
                className="text-white hover:text-blue-200 flex items-center"
              >
                {user.avatar_url && (
                  <img src={user.avatar_url} alt={user.name} className="w-8 h-8 rounded-full mr-2" />
                )}
                {user.name}
              </button>
              <button
                onClick={logout}
                className="text-red-300 hover:text-red-200"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuth(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
            >
              Login / Sign Up
            </button>
          )}
        </div>
      </div>

      {/* Stats and Voting Interface */}
      <div className="text-center py-6 px-4">
        <p className="text-blue-200 mb-4">Choose your favorites to discover your taste</p>
        
        {userStats && (
          <div className="mt-4 flex justify-center space-x-8 text-white">
            <div className="text-center">
              <div className="text-2xl font-bold">{userStats.total_votes}</div>
              <div className="text-sm text-blue-200">Total Votes</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{userStats.votes_until_recommendations}</div>
              <div className="text-sm text-blue-200">Until Recommendations</div>
            </div>
          </div>
        )}
        
        {userStats?.recommendations_available && (
          <button
            onClick={toggleRecommendations}
            className="mt-4 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
          >
            View My Recommendations
          </button>
        )}
      </div>

      {/* Voting Interface */}
      {currentPair && (
        <div className="max-w-6xl mx-auto px-4 pb-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white mb-2">
              Which {currentPair.content_type === 'movie' ? 'movie' : 'TV show'} do you prefer?
            </h2>
            <p className="text-blue-200">Tap the one you like more</p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8">
            {/* Item 1 */}
            <div 
              className={`bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden cursor-pointer transform transition-all duration-200 hover:scale-105 hover:bg-opacity-20 ${voting ? 'pointer-events-none opacity-75' : ''}`}
              onClick={() => handleVote(currentPair.item1.id, currentPair.item2.id)}
            >
              {currentPair.item1.poster && (
                <img 
                  src={currentPair.item1.poster} 
                  alt={currentPair.item1.title}
                  className="w-full h-80 object-cover"
                />
              )}
              <div className="p-6 text-white">
                <h3 className="text-2xl font-bold mb-2">{currentPair.item1.title}</h3>
                <p className="text-blue-200 mb-2">({currentPair.item1.year})</p>
                <p className="text-sm text-blue-100">{currentPair.item1.genre}</p>
                {currentPair.item1.plot && (
                  <p className="text-sm text-gray-300 mt-2 line-clamp-3">{currentPair.item1.plot}</p>
                )}
              </div>
            </div>

            {/* VS Divider */}
            <div className="md:hidden flex items-center justify-center py-4">
              <div className="bg-white bg-opacity-20 rounded-full px-6 py-2">
                <span className="text-white font-bold text-xl">VS</span>
              </div>
            </div>

            {/* Item 2 */}
            <div 
              className={`bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden cursor-pointer transform transition-all duration-200 hover:scale-105 hover:bg-opacity-20 ${voting ? 'pointer-events-none opacity-75' : ''}`}
              onClick={() => handleVote(currentPair.item2.id, currentPair.item1.id)}
            >
              {currentPair.item2.poster && (
                <img 
                  src={currentPair.item2.poster} 
                  alt={currentPair.item2.title}
                  className="w-full h-80 object-cover"
                />
              )}
              <div className="p-6 text-white">
                <h3 className="text-2xl font-bold mb-2">{currentPair.item2.title}</h3>
                <p className="text-blue-200 mb-2">({currentPair.item2.year})</p>
                <p className="text-sm text-blue-100">{currentPair.item2.genre}</p>
                {currentPair.item2.plot && (
                  <p className="text-sm text-gray-300 mt-2 line-clamp-3">{currentPair.item2.plot}</p>
                )}
              </div>
            </div>
          </div>

          {/* Hidden VS on desktop */}
          <div className="hidden md:flex absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
            <div className="bg-white bg-opacity-20 rounded-full px-8 py-4">
              <span className="text-white font-bold text-2xl">VS</span>
            </div>
          </div>
        </div>
      )}

      {voting && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-8 text-white">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
            <p>Recording your vote...</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
