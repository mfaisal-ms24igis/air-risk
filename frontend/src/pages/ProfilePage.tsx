/**
 * User Profile Page
 * 
 * Displays user profile information, subscription tier, and account settings.
 * @module pages/ProfilePage
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store';
import { useUserTier } from '@/hooks/useUserTier';
import { motion } from 'framer-motion';
import { User, Mail, Shield, Calendar, AlertCircle, LogOut } from 'lucide-react';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated, accessToken, setUser } = useAuthStore();
  const { isPremium, tier: userTier } = useUserTier();
  const [firstName, setFirstName] = useState(user?.first_name || '');
  const [lastName, setLastName] = useState(user?.last_name || '');
  const [isLoading, setIsLoading] = useState(!user && isAuthenticated);

  // Update local state when user data changes
  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
    }
  }, [user]);

  // Always refresh user data when component mounts (in case of recent updates)
  useEffect(() => {
    if (isAuthenticated && accessToken) {
      fetch('/api/v1/auth/profile/', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      })
        .then(res => res.ok ? res.json() : null)
        .then(userData => {
          if (userData) {
            setUser(userData);
          }
        })
        .catch(err => {
          console.error('Failed to refresh user profile:', err);
        });
    }
  }, [isAuthenticated, accessToken, setUser]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block">
            <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
          <p className="text-gray-300 mt-4">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!user || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle size={48} className="mx-auto text-red-400 mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Not Authenticated</h1>
          <p className="text-gray-300 mb-6">Please log in to view your profile.</p>
          <button
            onClick={() => navigate('/login')}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Not available';
    
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Invalid date';
      
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch (error) {
      return 'Invalid date';
    }
  };

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 py-8 px-4 min-h-screen">
      <div className="max-w-4xl mx-auto pb-32">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Header */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-3 mb-4">
              <img src="/Air_RISK_logo_onlyicon_removedbg.png" alt="Air RISK" className="w-16 h-16" />
              <div className="flex items-baseline gap-1">
                <h1 className="text-4xl font-bold text-white">Air</h1>
                <h1 className="text-4xl font-bold text-transparent bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text">RISK</h1>
              </div>
            </div>
            <h2 className="text-2xl font-semibold text-white mb-2">My Profile</h2>
            <p className="text-gray-400">Manage your account and subscription</p>
          </div>

          {/* Profile Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/20"
          >
            {/* Avatar & Basic Info */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-8 pb-8 border-b border-white/10">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
                <User size={40} className="text-white" />
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-3xl font-bold text-white">
                    {firstName || lastName ? `${firstName} ${lastName}` : user.username}
                  </h2>
                  {isPremium && (
                    <span className="px-3 py-1 bg-yellow-500/20 border border-yellow-500/50 rounded-full text-sm text-yellow-400 font-semibold flex items-center gap-1">
                      ⭐ Premium
                    </span>
                  )}
                </div>
                <p className="text-gray-400">@{user.username}</p>
              </div>
            </div>

            {/* Account Info Grid */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              {/* Email */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/5 rounded-lg p-4 border border-white/10"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Mail size={18} className="text-cyan-400" />
                  <span className="text-sm font-semibold text-gray-300">Email</span>
                </div>
                <p className="text-white text-lg">{user.email}</p>
              </motion.div>

              {/* Subscription Tier */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/5 rounded-lg p-4 border border-white/10"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Shield size={18} className={isPremium ? 'text-yellow-400' : 'text-blue-400'} />
                  <span className="text-sm font-semibold text-gray-300">Subscription</span>
                </div>
                <p className="text-white text-lg font-semibold">
                  {isPremium ? '✨ Premium' : '📱 Basic'}
                </p>
                <p className="text-gray-400 text-xs mt-1">Tier: {userTier.toUpperCase()}</p>
              </motion.div>

              {/* Member Since */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white/5 rounded-lg p-4 border border-white/10"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Calendar size={18} className="text-green-400" />
                  <span className="text-sm font-semibold text-gray-300">Member Since</span>
                </div>
                <p className="text-white text-lg">{formatDate(user.created_at || user.date_joined)}</p>
              </motion.div>

              {/* Premium Until */}
              {isPremium && user.premium_until && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                  className="bg-gradient-to-br from-yellow-500/20 to-orange-500/20 rounded-lg p-4 border border-yellow-500/30"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Calendar size={18} className="text-yellow-400" />
                    <span className="text-sm font-semibold text-gray-300">Premium Until</span>
                  </div>
                  <p className="text-white text-lg font-semibold">{formatDate(user.premium_until)}</p>
                </motion.div>
              )}
            </div>

            {/* Premium Benefits */}
            {isPremium && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 rounded-lg p-6 border border-yellow-500/30 mb-8"
              >
                <h3 className="text-lg font-bold text-yellow-400 mb-4 flex items-center gap-2">
                  <Shield size={20} />
                  Premium Features
                </h3>
                <ul className="grid md:grid-cols-2 gap-3 text-gray-300">
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                    Detailed district drill-down analysis
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                    Real-time satellite exposure data
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                    Pollutant layer switching (PM2.5, NO₂, O₃)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                    Custom location reports & PDF export
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                    30-day trend analysis
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                    Priority support & updates
                  </li>
                </ul>
              </motion.div>
            )}

            {/* Actions */}
            <div className="flex gap-4 flex-wrap">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleLogout}
                className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold transition-colors"
              >
                <LogOut size={18} />
                Logout
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate('/map')}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
              >
                Back to Map
              </motion.button>
            </div>
          </motion.div>

          {/* Basic User Upgrade */}
          {!isPremium && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-2xl p-8 border border-blue-500/30 text-center"
            >
              <h3 className="text-2xl font-bold text-cyan-400 mb-3">Upgrade to Premium</h3>
              <p className="text-gray-300 mb-6 max-w-lg mx-auto">
                Unlock advanced features including district drill-down, satellite imagery, custom reports, and trend analysis.
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate('/upgrade-premium')}
                className="px-8 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-lg font-bold transition-all"
              >
                Upgrade Now
              </motion.button>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
