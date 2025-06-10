import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [currentPair, setCurrentPair] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [voting, setVoting] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [contentInitialized, setContentInitialized] = useState(false);

  // Initialize session and content
  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setLoading(true);
      
      // Initialize content first
      if (!contentInitialized) {
        console.log('Initializing content...');
        await axios.post(`${API}/initialize-content`);
        setContentInitialized(true);
      }
      
      // Create session
      const sessionResponse = await axios.post(`${API}/session`);
      setSessionId(sessionResponse.data.session_id);
      
      // Get initial stats
      await updateStats(sessionResponse.data.session_id);
      
      // Get first voting pair
      await getNextPair(sessionResponse.data.session_id);
      
    } catch (error) {
      console.error('Initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateStats = async (session) => {
    try {
      const statsResponse = await axios.get(`${API}/stats/${session}`);
      setUserStats(statsResponse.data);
      
      // Check if recommendations are available
      if (statsResponse.data.recommendations_available && !showRecommendations) {
        const recResponse = await axios.get(`${API}/recommendations/${session}`);
        setRecommendations(recResponse.data);
      }
    } catch (error) {
      console.error('Stats error:', error);
    }
  };

  const getNextPair = async (session) => {
    try {
      const pairResponse = await axios.get(`${API}/voting-pair/${session}`);
      setCurrentPair(pairResponse.data);
    } catch (error) {
      console.error('Pair error:', error);
    }
  };

  const handleVote = async (winnerId, loserId) => {
    if (voting || !currentPair) return;
    
    try {
      setVoting(true);
      
      await axios.post(`${API}/vote`, {
        session_id: sessionId,
        winner_id: winnerId,
        loser_id: loserId,
        content_type: currentPair.content_type
      });
      
      // Update stats
      await updateStats(sessionId);
      
      // Get next pair
      await getNextPair(sessionId);
      
    } catch (error) {
      console.error('Vote error:', error);
    } finally {
      setVoting(false);
    }
  };

  const toggleRecommendations = () => {
    setShowRecommendations(!showRecommendations);
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
      <div className="text-center py-6 px-4">
        <h1 className="text-4xl font-bold text-white mb-2">Movie & TV Preferences</h1>
        <p className="text-blue-200">Choose your favorites to discover your taste</p>
        
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
