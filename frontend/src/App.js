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
  const [showPosterModal, setShowPosterModal] = useState(false);
  const [selectedPoster, setSelectedPoster] = useState(null);
  const [userWatchlist, setUserWatchlist] = useState([]);
  const [algoWatchlist, setAlgoWatchlist] = useState([]);
  const [showWatchlist, setShowWatchlist] = useState(false);
  const [contentInteractions, setContentInteractions] = useState({}); // Track interactions per content ID
  const [removedRecommendations, setRemovedRecommendations] = useState(new Set()); // Track removed recommendation IDs
  const [undoModal, setUndoModal] = useState({ show: false, item: null, action: null }); // Undo modal state
  const [watchlistType, setWatchlistType] = useState('user_defined'); // 'user_defined' or 'algo_predicted'

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

  // Store session in localStorage for persistence
  useEffect(() => {
    const storedSessionId = localStorage.getItem('guestSessionId');
    if (!user && !sessionId && storedSessionId) {
      setSessionId(storedSessionId);
    }
  }, [user, sessionId]);

  // Save session to localStorage when it changes
  useEffect(() => {
    if (sessionId && !user) {
      localStorage.setItem('guestSessionId', sessionId);
    } else if (user) {
      localStorage.removeItem('guestSessionId');
    }
  }, [sessionId, user]);

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
      let currentSessionId = sessionId;
      if (!token && !currentSessionId) {
        const sessionResponse = await axios.post(`${API}/session`);
        currentSessionId = sessionResponse.data.session_id;
        setSessionId(currentSessionId);
      }
      
      // Get initial stats and voting pair (with proper session ID)
      await updateStats(currentSessionId);
      await getNextPair(currentSessionId);
      
    } catch (error) {
      console.error('Initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateStats = async (currentSessionId = sessionId) => {
    try {
      const params = {};
      if (!user && currentSessionId) {
        params.session_id = currentSessionId;
      }
      
      const statsResponse = await axios.get(`${API}/stats`, { params });
      setUserStats(statsResponse.data);
      
      // Check if recommendations are available - use different logic for users vs guests
      if (user) {
        // For authenticated users, check if they have ML recommendations
        try {
          const algoWatchlistResponse = await axios.get(`${API}/watchlist/algo_predicted`);
          if (algoWatchlistResponse.data.items && algoWatchlistResponse.data.items.length > 0) {
            setRecommendations(algoWatchlistResponse.data.items);
            // Update stats to show recommendations are available
            setUserStats(prev => ({ ...prev, recommendations_available: true }));
          }
        } catch (error) {
          console.error('Algo recommendations error:', error);
        }
      } else {
        // For guests, use the old system (36 votes)
        if (statsResponse.data.recommendations_available && !showRecommendations) {
          const recResponse = await axios.get(`${API}/recommendations`, { params });
          setRecommendations(recResponse.data);
        }
      }
    } catch (error) {
      console.error('Stats error:', error);
    }
  };

  const getNextPair = async (currentSessionId = sessionId) => {
    try {
      const params = {};
      if (!user && currentSessionId) {
        params.session_id = currentSessionId;
      }
      
      const pairResponse = await axios.get(`${API}/voting-pair`, { params });
      setCurrentPair(pairResponse.data);
      
      // Load interaction status for both items in the pair
      if (user || currentSessionId) {
        await loadContentInteractions([pairResponse.data.item1.id, pairResponse.data.item2.id], currentSessionId);
      }
    } catch (error) {
      console.error('Pair error:', error);
    }
  };

  const loadContentInteractions = async (contentIds, sessionId = null) => {
    try {
      const interactions = {};
      
      for (const contentId of contentIds) {
        const params = {};
        if (!user && sessionId) {
          params.session_id = sessionId;
        }
        
        const response = await axios.get(`${API}/content/${contentId}/user-status`, { params });
        
        // Determine the primary interaction (prioritize in order: watched > want_to_watch > not_interested)
        if (response.data.has_watched) {
          interactions[contentId] = 'watched';
        } else if (response.data.wants_to_watch) {
          interactions[contentId] = 'want_to_watch';
        } else if (response.data.not_interested) {
          interactions[contentId] = 'not_interested';
        }
      }
      
      setContentInteractions(prev => ({ ...prev, ...interactions }));
    } catch (error) {
      console.error('Content interaction loading error:', error);
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
      
      const voteResponse = await axios.post(`${API}/vote`, voteData);
      
      // Update stats immediately with response data
      if (voteResponse.data.total_votes) {
        setUserStats(prev => ({
          ...prev,
          total_votes: voteResponse.data.total_votes,
          votes_until_recommendations: Math.max(0, 36 - voteResponse.data.total_votes),
          recommendations_available: voteResponse.data.recommendations_available
        }));
      }
      
      // Get next pair
      await getNextPair();
      
      // Check if recommendations are now available
      if (user) {
        // For authenticated users, check if they have enough interactions for ML recommendations
        const userInteractionCount = (voteResponse.data.total_votes || 0);
        if (userInteractionCount >= 10) { // Lower threshold for ML recommendations
          setUserStats(prev => ({ ...prev, recommendations_available: true }));
        }
      } else {
        // For guests, use original 36-vote threshold
        if (voteResponse.data.recommendations_available && !showRecommendations) {
          const params = {};
          if (!user && sessionId) {
            params.session_id = sessionId;
          }
          const recResponse = await axios.get(`${API}/recommendations`, { params });
          setRecommendations(recResponse.data);
        }
      }
      
    } catch (error) {
      console.error('Vote error:', error);
    } finally {
      setVoting(false);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
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
      
      // Clear any existing session since we're now authenticated
      setSessionId(null);
      
      // Small delay to ensure token is set before making requests
      setTimeout(async () => {
        await updateStats();
        await getNextPair();
        setLoading(false);
      }, 100);
      
    } catch (error) {
      console.error('Auth error:', error);
      alert(error.response?.data?.detail || 'Authentication failed');
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      
      // Clear auth state
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      setShowProfile(false);
      setShowRecommendations(false);
      delete axios.defaults.headers.common['Authorization'];
      
      // Reset app state
      setCurrentPair(null);
      setUserStats(null);
      setRecommendations([]);
      setVotingHistory([]);
      
      // Reinitialize as guest with a fresh session
      const sessionResponse = await axios.post(`${API}/session`);
      const newSessionId = sessionResponse.data.session_id;
      setSessionId(newSessionId);
      
      // Get fresh data for guest session
      await updateStats(newSessionId);
      await getNextPair(newSessionId);
      
    } catch (error) {
      console.error('Error during logout:', error);
      // Force reload as fallback
      window.location.reload();
    } finally {
      setLoading(false);
    }
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

  const toggleRecommendations = async () => {
    if (!showRecommendations) {
      // Load recommendations when showing
      if (user) {
        // For authenticated users, load from ML watchlist
        try {
          const algoWatchlistResponse = await axios.get(`${API}/watchlist/algo_predicted`);
          if (algoWatchlistResponse.data.items && algoWatchlistResponse.data.items.length > 0) {
            setRecommendations(algoWatchlistResponse.data.items);
          } else {
            // No ML recommendations yet, suggest generating them
            alert('No ML recommendations yet. Use the "🔮 Generate New Recommendations" button in your watchlist to create personalized suggestions!');
            return;
          }
        } catch (error) {
          console.error('Failed to load ML recommendations:', error);
          alert('Failed to load recommendations. Please try again.');
          return;
        }
      } else {
        // For guests, use original recommendation system
        try {
          const params = { session_id: sessionId };
          const recResponse = await axios.get(`${API}/recommendations`, { params });
          setRecommendations(recResponse.data);
        } catch (error) {
          console.error('Failed to load recommendations:', error);
          alert('Need at least 36 votes for recommendations!');
          return;
        }
      }
    }
    setShowRecommendations(!showRecommendations);
  };

  const toggleProfile = async () => {
    if (!showProfile && user) {
      await getVotingHistory();
    }
    setShowProfile(!showProfile);
  };

  const openPosterModal = (item) => {
    setSelectedPoster(item);
    setShowPosterModal(true);
  };

  const closePosterModal = () => {
    setShowPosterModal(false);
    setSelectedPoster(null);
  };

  const handleContentInteraction = async (contentId, interactionType, priority = 1) => {
    if (!user && interactionType !== 'not_interested') {
      alert('Please login to use this feature');
      return;
    }

    try {
      // Check if this interaction is already selected - if so, deselect it
      const currentInteraction = getInteractionForContent(contentId);
      
      if (currentInteraction === interactionType) {
        // Deselect: remove the interaction
        console.log(`Deselecting ${interactionType} for content ${contentId}`);
        
        // Remove from local state immediately for instant feedback
        setContentInteractions(prev => {
          const updated = { ...prev };
          delete updated[contentId];
          return updated;
        });
        
        // TODO: Add backend endpoint to remove interaction
        // For now, we'll just handle it locally
        
        return;
      }

      const data = {
        content_id: contentId,
        interaction_type: interactionType,
        priority: priority
      };

      if (!user) {
        data.session_id = sessionId;
      }

      // Update local interaction state immediately for instant feedback
      setContentInteractions(prev => ({
        ...prev,
        [contentId]: interactionType
      }));

      await axios.post(`${API}/content/interact`, data);
      
      // Refresh watchlists if needed
      if (user) {
        await loadWatchlists();
      }
      
      // Show feedback
      const messages = {
        'watched': '✅ Marked as watched!',
        'want_to_watch': '📝 Added to your watchlist!',
        'not_interested': '❌ Noted - we won\'t recommend similar content'
      };
      
      console.log(messages[interactionType]);
      
    } catch (error) {
      console.error('Content interaction error:', error);
      
      // Revert local state on error
      setContentInteractions(prev => {
        const updated = { ...prev };
        delete updated[contentId];
        return updated;
      });
      
      alert('Failed to record interaction');
    }
  };

  const getInteractionForContent = (contentId) => {
    return contentInteractions[contentId] || null;
  };

  const getButtonStyle = (contentId, interactionType) => {
    const currentInteraction = getInteractionForContent(contentId);
    const isActive = currentInteraction === interactionType;
    
    const baseStyle = "px-3 py-1 rounded text-xs transition-all duration-200 cursor-pointer select-none";
    
    if (isActive) {
      // Active/selected state with hover effect to indicate it can be deselected
      switch (interactionType) {
        case 'watched':
          return `${baseStyle} bg-green-700 text-white border-2 border-green-500 hover:bg-green-600 hover:border-green-400 shadow-lg`;
        case 'want_to_watch':
          return `${baseStyle} bg-blue-700 text-white border-2 border-blue-500 hover:bg-blue-600 hover:border-blue-400 shadow-lg`;
        case 'not_interested':
          return `${baseStyle} bg-gray-700 text-white border-2 border-gray-500 hover:bg-gray-600 hover:border-gray-400 shadow-lg`;
        default:
          return baseStyle;
      }
    } else {
      // Inactive/unselected state
      switch (interactionType) {
        case 'watched':
          return `${baseStyle} bg-green-600 hover:bg-green-700 text-white border-2 border-transparent hover:border-green-400`;
        case 'want_to_watch':
          return `${baseStyle} bg-blue-600 hover:bg-blue-700 text-white border-2 border-transparent hover:border-blue-400`;
        case 'not_interested':
          return `${baseStyle} bg-gray-600 hover:bg-gray-700 text-white border-2 border-transparent hover:border-gray-400`;
        default:
          return baseStyle;
      }
    }
  };

  const getButtonText = (contentId, interactionType) => {
    const currentInteraction = getInteractionForContent(contentId);
    const isActive = currentInteraction === interactionType;
    
    if (isActive) {
      switch (interactionType) {
        case 'watched':
          return '✅ Watched (click to undo)';
        case 'want_to_watch':
          return '📋 In Watchlist (click to undo)';
        case 'not_interested':
          return '🚫 Passed (click to undo)';
        default:
          return '';
      }
    } else {
      switch (interactionType) {
        case 'watched':
          return '✓ Watched';
        case 'want_to_watch':
          return '📝 Want to Watch';
        case 'not_interested':
          return '❌ Pass';
        default:
          return '';
      }
    }
  };

  const loadWatchlists = async () => {
    if (!user) return;
    
    try {
      const [userResponse, algoResponse] = await Promise.all([
        axios.get(`${API}/watchlist/user_defined`),
        axios.get(`${API}/watchlist/algo_predicted`)
      ]);
      
      setUserWatchlist(userResponse.data.items);
      setAlgoWatchlist(algoResponse.data.items);
    } catch (error) {
      console.error('Watchlist loading error:', error);
    }
  };

  const generateRecommendations = async () => {
    if (!user) {
      alert('Please login to get personalized recommendations');
      return;
    }

    try {
      setLoading(true);
      const response = await axios.post(`${API}/recommendations/generate`);
      
      alert(response.data.message);
      await loadWatchlists(); // Refresh to show new recommendations
      
    } catch (error) {
      console.error('Recommendation generation error:', error);
      alert(error.response?.data?.detail || 'Failed to generate recommendations');
    } finally {
      setLoading(false);
    }
  };

  const removeFromWatchlist = async (watchlistId) => {
    try {
      await axios.delete(`${API}/watchlist/${watchlistId}`);
      await loadWatchlists();
    } catch (error) {
      console.error('Remove from watchlist error:', error);
    }
  };

  const toggleWatchlist = async () => {
    if (!user) {
      alert('Please login to view your watchlists');
      return;
    }
    
    if (!showWatchlist) {
      await loadWatchlists();
    }
    setShowWatchlist(!showWatchlist);
  };

  const handleRecommendationAction = async (item, action) => {
    // Prevent rapid clicking
    if (removedRecommendations.has(item.watchlist_id)) {
      return; // Already removed
    }
    
    try {
      // Immediately remove from display
      setRemovedRecommendations(prev => new Set([...prev, item.watchlist_id]));
      
      // Record the interaction
      await handleContentInteraction(item.content.id, action);
      
      // Close any existing undo modal first
      if (undoModal.show) {
        setUndoModal({ show: false, item: null, action: null });
        await new Promise(resolve => setTimeout(resolve, 100)); // Small delay
      }
      
      // Show undo modal
      setUndoModal({
        show: true,
        item: item,
        action: action
      });
      
      // Auto-hide undo modal after 5 seconds
      setTimeout(() => {
        setUndoModal(current => {
          // Only close if this is still the current modal
          if (current.item?.watchlist_id === item.watchlist_id && current.action === action) {
            return { show: false, item: null, action: null };
          }
          return current;
        });
      }, 5000);
      
    } catch (error) {
      console.error('Recommendation action error:', error);
      // Revert removal on error
      setRemovedRecommendations(prev => {
        const updated = new Set(prev);
        updated.delete(item.watchlist_id);
        return updated;
      });
    }
  };

  const handleUndoRecommendationAction = async () => {
    if (!undoModal.item) return;
    
    try {
      // Remove the interaction from backend
      // Note: We'll need to implement this endpoint or handle it differently
      console.log('Undoing action for:', undoModal.item.content.title);
      
      // Restore the item to display
      setRemovedRecommendations(prev => {
        const updated = new Set(prev);
        updated.delete(undoModal.item.watchlist_id);
        return updated;
      });
      
      // Close modal
      setUndoModal({ show: false, item: null, action: null });
      
      // Reload watchlists to ensure consistency
      await loadWatchlists();
      
    } catch (error) {
      console.error('Undo action error:', error);
    }
  };

  const closeUndoModal = () => {
    setUndoModal({ show: false, item: null, action: null });
  };

  // Poster Modal
  if (showPosterModal && selectedPoster) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4" onClick={closePosterModal}>
        <div className="max-w-2xl max-h-full bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
          <div className="relative">
            <button
              onClick={closePosterModal}
              className="absolute top-4 right-4 text-white bg-black bg-opacity-50 rounded-full w-10 h-10 flex items-center justify-center hover:bg-opacity-70 transition-all z-10"
            >
              ✕
            </button>
            {selectedPoster.poster && (
              <img 
                src={selectedPoster.poster} 
                alt={selectedPoster.title}
                className="w-full max-h-screen object-contain"
              />
            )}
          </div>
          <div className="p-6 text-white">
            <h2 className="text-3xl font-bold mb-2">{selectedPoster.title}</h2>
            <p className="text-blue-200 mb-2">({selectedPoster.year})</p>
            <p className="text-lg text-blue-100 mb-4">{selectedPoster.genre}</p>
            {selectedPoster.director && (
              <p className="text-gray-300 mb-2"><strong>Director:</strong> {selectedPoster.director}</p>
            )}
            {selectedPoster.actors && (
              <p className="text-gray-300 mb-4"><strong>Starring:</strong> {selectedPoster.actors}</p>
            )}
            {selectedPoster.plot && (
              <p className="text-gray-200 leading-relaxed">{selectedPoster.plot}</p>
            )}
            {selectedPoster.rating && selectedPoster.rating !== "N/A" && (
              <div className="mt-4 inline-block bg-yellow-600 text-white px-3 py-1 rounded-full">
                ⭐ {selectedPoster.rating}/10
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Undo Modal for Recommendation Actions
  if (undoModal.show && undoModal.item) {
    const actionMessages = {
      'watched': 'marked as watched',
      'not_interested': 'marked as not interested'
    };
    
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={closeUndoModal}>
        <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-6 max-w-md mx-auto" onClick={(e) => e.stopPropagation()}>
          <div className="text-center text-white">
            <div className="text-4xl mb-4">↩️</div>
            <h3 className="text-xl font-bold mb-2">Action Completed</h3>
            <p className="text-blue-200 mb-4">
              "{undoModal.item.content.title}" has been {actionMessages[undoModal.action]} and removed from your recommendations.
            </p>
            <div className="flex space-x-4 justify-center">
              <button
                onClick={handleUndoRecommendationAction}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors"
              >
                ↩️ Undo
              </button>
              <button
                onClick={closeUndoModal}
                className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded transition-colors"
              >
                Keep Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

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

  // Watchlist Page
  if (showWatchlist && user) {
    const currentWatchlist = watchlistType === 'user_defined' ? userWatchlist : algoWatchlist;
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-4">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-8">
            <div className="flex justify-between items-center mb-8">
              <h1 className="text-4xl font-bold text-white">My Watchlists</h1>
              <button
                onClick={toggleWatchlist}
                className="text-blue-300 hover:text-blue-200"
              >
                Back to Voting
              </button>
            </div>
            
            {/* Watchlist Type Selector */}
            <div className="flex space-x-4 mb-8">
              <button
                onClick={() => setWatchlistType('user_defined')}
                className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
                  watchlistType === 'user_defined'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white bg-opacity-20 text-blue-200 hover:bg-opacity-30'
                }`}
              >
                My Watchlist ({userWatchlist.length})
              </button>
              <button
                onClick={() => setWatchlistType('algo_predicted')}
                className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
                  watchlistType === 'algo_predicted'
                    ? 'bg-green-600 text-white'
                    : 'bg-white bg-opacity-20 text-green-200 hover:bg-opacity-30'
                }`}
              >
                AI Recommendations ({algoWatchlist.length})
              </button>
              <button
                onClick={generateRecommendations}
                className="px-6 py-3 rounded-lg font-semibold bg-purple-600 text-white hover:bg-purple-700 transition-colors"
              >
                🔮 Generate New Recommendations
              </button>
            </div>
            
            {/* Watchlist Content */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {currentWatchlist.filter(item => !removedRecommendations.has(item.watchlist_id)).map((item) => (
                <div 
                  key={item.watchlist_id} 
                  className={`bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden transition-all duration-300 ${
                    removedRecommendations.has(item.watchlist_id) ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
                  }`}
                >
                  <div className="relative">
                    {item.content.poster && (
                      <img 
                        src={item.content.poster} 
                        alt={item.content.title}
                        className="w-full h-64 object-cover cursor-pointer"
                        onClick={() => openPosterModal(item.content)}
                      />
                    )}
                    <div className="absolute top-2 right-2">
                      <button
                        onClick={() => removeFromWatchlist(item.watchlist_id)}
                        className="bg-red-600 text-white p-2 rounded-full hover:bg-red-700 transition-colors"
                        title="Remove from watchlist"
                      >
                        ✕
                      </button>
                    </div>
                    {watchlistType === 'algo_predicted' && (
                      <div className="absolute bottom-2 left-2">
                        <div className="bg-green-600 bg-opacity-90 text-white px-3 py-1 rounded-full text-sm">
                          AI Recommended
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="p-6 text-white">
                    <h3 className="text-xl font-bold mb-2">{item.content.title}</h3>
                    <p className="text-blue-200 mb-2">({item.content.year})</p>
                    
                    {watchlistType === 'algo_predicted' && item.reasoning && (
                      <p className="text-sm text-green-200 mb-4">{item.reasoning}</p>
                    )}
                    
                    <div className="flex justify-between items-center">
                      <div className="flex space-x-2">
                        {watchlistType === 'algo_predicted' ? (
                          // AI Recommendations - use special handler with undo modal
                          <>
                            <button
                              onClick={() => handleRecommendationAction(item, 'watched')}
                              disabled={removedRecommendations.has(item.watchlist_id)}
                              className={`px-3 py-2 rounded text-sm transition-colors recommendation-action-btn ${
                                removedRecommendations.has(item.watchlist_id) 
                                  ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                                  : 'bg-blue-600 hover:bg-blue-700 text-white'
                              }`}
                            >
                              ✓ Watched
                            </button>
                            <button
                              onClick={() => handleRecommendationAction(item, 'not_interested')}
                              disabled={removedRecommendations.has(item.watchlist_id)}
                              className={`px-3 py-2 rounded text-sm transition-colors recommendation-action-btn ${
                                removedRecommendations.has(item.watchlist_id)
                                  ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                                  : 'bg-gray-600 hover:bg-gray-700 text-white'
                              }`}
                            >
                              Not Interested
                            </button>
                          </>
                        ) : (
                          // User-defined watchlist - use regular handler
                          <>
                            <button
                              onClick={() => handleContentInteraction(item.content.id, 'watched')}
                              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm transition-colors"
                            >
                              ✓ Watched
                            </button>
                            <button
                              onClick={() => handleContentInteraction(item.content.id, 'not_interested')}
                              className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded text-sm transition-colors"
                            >
                              Not Interested
                            </button>
                          </>
                        )}
                      </div>
                      <div className="text-sm text-gray-300">
                        Priority: {item.priority || 1}/5
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {currentWatchlist.filter(item => !removedRecommendations.has(item.watchlist_id)).length === 0 && (
              <div className="text-center py-12 col-span-full">
                <div className="text-6xl mb-4">📝</div>
                <h3 className="text-2xl font-bold text-white mb-4">
                  {watchlistType === 'user_defined' ? 'Your watchlist is empty' : 
                   currentWatchlist.length > 0 ? 'All recommendations processed!' : 'No AI recommendations yet'}
                </h3>
                <p className="text-blue-200">
                  {watchlistType === 'user_defined' 
                    ? 'Start adding movies and shows you want to watch!' 
                    : currentWatchlist.length > 0 
                      ? 'You\'ve interacted with all your recommendations. Generate new ones to discover more content!'
                      : 'Generate recommendations based on your preferences!'}
                </p>
                {watchlistType === 'algo_predicted' && currentWatchlist.length > 0 && (
                  <button
                    onClick={generateRecommendations}
                    className="mt-4 bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
                  >
                    🔮 Generate New Recommendations
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
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
            {recommendations.map((rec, index) => {
              // Handle both old recommendation format and new ML watchlist format
              const isMLRecommendation = rec.content && rec.reasoning;
              const contentItem = isMLRecommendation ? rec.content : rec;
              const reasoning = isMLRecommendation ? rec.reasoning : rec.reason;
              const poster = contentItem.poster;
              const title = contentItem.title;
              
              return (
                <div key={index} className="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden text-white hover:bg-opacity-20 transition-all">
                  <div className="relative group">
                    {poster ? (
                      <>
                        <img 
                          src={poster} 
                          alt={title}
                          className="w-full h-64 object-cover cursor-pointer"
                          onClick={() => openPosterModal(contentItem)}
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-60"></div>
                        <button
                          onClick={() => openPosterModal(contentItem)}
                          className="absolute top-2 right-2 bg-black bg-opacity-50 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-opacity-70"
                          title="View full poster"
                        >
                          🔍
                        </button>
                        <div className="absolute bottom-0 left-0 right-0 p-3 text-white">
                          <div className="text-xs bg-green-600 bg-opacity-80 px-2 py-1 rounded-full inline-block mb-2">
                            {isMLRecommendation ? 'AI Recommended' : 'Recommended for You'}
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="w-full h-64 bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center">
                        <div className="text-center text-gray-300">
                          <div className="text-4xl mb-2">🎬</div>
                          <div className="text-sm">No Poster Available</div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="p-6">
                    <h3 className="text-xl font-bold mb-2">{title}</h3>
                    <p className="text-blue-200 text-sm">{reasoning}</p>
                  </div>
                </div>
              );
            })}
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 space-y-2 sm:space-y-0">
        <div className="text-white">
          <h1 className="text-xl sm:text-2xl font-bold">Movie Preferences</h1>
        </div>
        
        <div className="flex items-center space-x-2 sm:space-x-4">
          {user ? (
            <div className="flex items-center space-x-2 sm:space-x-4">
              <button
                onClick={toggleWatchlist}
                className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-3 sm:px-4 rounded-lg transition-colors text-sm sm:text-base"
              >
                📝 Watchlists
              </button>
              <button
                onClick={toggleProfile}
                className="text-white hover:text-blue-200 flex items-center text-sm sm:text-base"
              >
                {user.avatar_url && (
                  <img src={user.avatar_url} alt={user.name} className="w-6 h-6 sm:w-8 sm:h-8 rounded-full mr-2" />
                )}
                <span className="truncate max-w-24 sm:max-w-none">{user.name}</span>
              </button>
              <button
                onClick={logout}
                className="text-red-300 hover:text-red-200 text-sm sm:text-base"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuth(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-3 sm:px-4 rounded-lg transition-colors text-sm sm:text-base"
            >
              Login / Sign Up
            </button>
          )}
        </div>
      </div>

      {/* Stats and Voting Interface */}
      <div className="text-center py-4 px-4">
        <p className="text-blue-200 mb-4 text-sm sm:text-base">Choose your favorites to discover your taste</p>
        
        {userStats && (
          <div className="mt-4 flex justify-center space-x-4 sm:space-x-8 text-white">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold">{userStats.total_votes}</div>
              <div className="text-xs sm:text-sm text-blue-200">Total Votes</div>
            </div>
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold">{userStats.votes_until_recommendations}</div>
              <div className="text-xs sm:text-sm text-blue-200">Until Recommendations</div>
            </div>
          </div>
        )}
        
        {userStats?.recommendations_available && (
          <button
            onClick={toggleRecommendations}
            className="mt-4 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 sm:px-4 rounded-lg transition-colors text-sm sm:text-base"
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
          
          <div className="grid md:grid-cols-2 gap-4 md:gap-8 relative">
            {/* Item 1 */}
            <div 
              className={`bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden cursor-pointer transform transition-all duration-200 hover:scale-105 hover:bg-opacity-20 ${voting ? 'pointer-events-none opacity-75' : ''}`}
              onClick={() => handleVote(currentPair.item1.id, currentPair.item2.id)}
            >
              <div className="relative group">
                {currentPair.item1.poster ? (
                  <>
                    <img 
                      src={currentPair.item1.poster} 
                      alt={currentPair.item1.title}
                      className="w-full h-48 md:h-80 object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-60"></div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openPosterModal(currentPair.item1);
                      }}
                      className="absolute top-2 right-2 bg-black bg-opacity-50 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-opacity-70"
                      title="View full poster"
                    >
                      🔍
                    </button>
                    <div className="absolute bottom-0 left-0 right-0 p-3 text-white">
                      <div className="text-xs bg-blue-600 bg-opacity-80 px-2 py-1 rounded-full inline-block mb-2">
                        Official OMDB Poster
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="w-full h-48 md:h-80 bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center">
                    <div className="text-center text-gray-300">
                      <div className="text-4xl mb-2">🎬</div>
                      <div className="text-sm">No Poster Available</div>
                    </div>
                  </div>
                )}
              </div>
              <div className="p-4 md:p-6 text-white">
                <h3 className="text-lg md:text-2xl font-bold mb-2">{currentPair.item1.title}</h3>
                <p className="text-blue-200 mb-2">({currentPair.item1.year})</p>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-blue-100">{currentPair.item1.genre}</p>
                  {currentPair.item1.rating && currentPair.item1.rating !== "N/A" && (
                    <div className="bg-yellow-600 text-white px-2 py-1 rounded text-xs">
                      ⭐ {currentPair.item1.rating}
                    </div>
                  )}
                </div>
                {currentPair.item1.plot && (
                  <p className="text-xs md:text-sm text-gray-300 line-clamp-3 mb-4">{currentPair.item1.plot}</p>
                )}
                
                {/* Action Buttons */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContentInteraction(currentPair.item1.id, 'watched');
                    }}
                    className={getButtonStyle(currentPair.item1.id, 'watched')}
                    title="Mark as watched"
                  >
                    {getInteractionForContent(currentPair.item1.id) === 'watched' ? '✅ Watched' : '✓ Watched'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContentInteraction(currentPair.item1.id, 'want_to_watch');
                    }}
                    className={getButtonStyle(currentPair.item1.id, 'want_to_watch')}
                    title="Add to watchlist"
                  >
                    {getInteractionForContent(currentPair.item1.id) === 'want_to_watch' ? '📋 In Watchlist' : '📝 Want to Watch'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContentInteraction(currentPair.item1.id, 'not_interested');
                    }}
                    className={getButtonStyle(currentPair.item1.id, 'not_interested')}
                    title="Not interested"
                  >
                    {getInteractionForContent(currentPair.item1.id) === 'not_interested' ? '🚫 Passed' : '❌ Pass'}
                  </button>
                </div>
              </div>
            </div>

            {/* VS Divider - Mobile */}
            <div className="md:hidden flex items-center justify-center py-2">
              <div className="bg-white bg-opacity-20 rounded-full px-4 py-2">
                <span className="text-white font-bold text-lg">VS</span>
              </div>
            </div>

            {/* VS Divider - Desktop */}
            <div className="hidden md:flex absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
              <div className="bg-white bg-opacity-20 rounded-full px-6 py-3">
                <span className="text-white font-bold text-xl">VS</span>
              </div>
            </div>

            {/* Item 2 */}
            <div 
              className={`bg-white bg-opacity-10 backdrop-blur-lg rounded-xl overflow-hidden cursor-pointer transform transition-all duration-200 hover:scale-105 hover:bg-opacity-20 ${voting ? 'pointer-events-none opacity-75' : ''}`}
              onClick={() => handleVote(currentPair.item2.id, currentPair.item1.id)}
            >
              <div className="relative group">
                {currentPair.item2.poster ? (
                  <>
                    <img 
                      src={currentPair.item2.poster} 
                      alt={currentPair.item2.title}
                      className="w-full h-48 md:h-80 object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-60"></div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openPosterModal(currentPair.item2);
                      }}
                      className="absolute top-2 right-2 bg-black bg-opacity-50 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-opacity-70"
                      title="View full poster"
                    >
                      🔍
                    </button>
                    <div className="absolute bottom-0 left-0 right-0 p-3 text-white">
                      <div className="text-xs bg-blue-600 bg-opacity-80 px-2 py-1 rounded-full inline-block mb-2">
                        Official OMDB Poster
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="w-full h-48 md:h-80 bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center">
                    <div className="text-center text-gray-300">
                      <div className="text-4xl mb-2">🎬</div>
                      <div className="text-sm">No Poster Available</div>
                    </div>
                  </div>
                )}
              </div>
              <div className="p-4 md:p-6 text-white">
                <h3 className="text-lg md:text-2xl font-bold mb-2">{currentPair.item2.title}</h3>
                <p className="text-blue-200 mb-2">({currentPair.item2.year})</p>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-blue-100">{currentPair.item2.genre}</p>
                  {currentPair.item2.rating && currentPair.item2.rating !== "N/A" && (
                    <div className="bg-yellow-600 text-white px-2 py-1 rounded text-xs">
                      ⭐ {currentPair.item2.rating}
                    </div>
                  )}
                </div>
                {currentPair.item2.plot && (
                  <p className="text-xs md:text-sm text-gray-300 line-clamp-3 mb-4">{currentPair.item2.plot}</p>
                )}
                
                {/* Action Buttons */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContentInteraction(currentPair.item2.id, 'watched');
                    }}
                    className={getButtonStyle(currentPair.item2.id, 'watched')}
                    title="Mark as watched"
                  >
                    {getInteractionForContent(currentPair.item2.id) === 'watched' ? '✅ Watched' : '✓ Watched'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContentInteraction(currentPair.item2.id, 'want_to_watch');
                    }}
                    className={getButtonStyle(currentPair.item2.id, 'want_to_watch')}
                    title="Add to watchlist"
                  >
                    {getInteractionForContent(currentPair.item2.id) === 'want_to_watch' ? '📋 In Watchlist' : '📝 Want to Watch'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContentInteraction(currentPair.item2.id, 'not_interested');
                    }}
                    className={getButtonStyle(currentPair.item2.id, 'not_interested')}
                    title="Not interested"
                  >
                    {getInteractionForContent(currentPair.item2.id) === 'not_interested' ? '🚫 Passed' : '❌ Pass'}
                  </button>
                </div>
              </div>
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
