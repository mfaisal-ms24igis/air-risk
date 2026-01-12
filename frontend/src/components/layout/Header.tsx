/**
 * Modern Navigation Header
 * 
 * Main application header with logo, branding, and navigation.
 * @module components/layout/Header
 */

import { motion } from 'framer-motion';
import { Menu, X, User, LogOut, LogIn, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store';
import { AnimatedLogo } from '@/components/AnimatedLogo';

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { user, isAuthenticated, isPremium, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    setIsMenuOpen(false);
    navigate('/login');
  };

  const navItems = [
    { label: 'Dashboard', href: '/' },
    { label: 'Map', href: '/map' },
    { label: 'Stations', href: '/stations' },
    { label: 'Reports', href: '/reports' },
    { label: 'Exposure Analysis', href: '/exposure' },
  ];

  return (
    <header className="bg-white/5 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
        <div className="flex items-center justify-between">
          {/* Logo & Branding */}
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity group">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2"
            >
              <AnimatedLogo size="md" />
              <div className="hidden sm:block">
                <div className="flex items-baseline gap-1">
                  <p className="text-lg font-bold text-white">Air</p>
                  <p className="text-lg font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">RISK</p>
                </div>
                <p className="text-xs text-gray-400 leading-tight">Real-time Intelligence<br/>Spatial Knowledge</p>
              </div>
            </motion.div>
          </Link>

          {/* Desktop Navigation */}
          {isAuthenticated && (
            <motion.nav
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="hidden md:flex items-center gap-8"
            >
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  to={item.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </motion.nav>
          )}

          {/* Right Side - User & Auth */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="hidden md:flex items-center gap-4"
          >
            {isAuthenticated ? (
              <>
                {isPremium && (
                  <span className="px-3 py-1 bg-yellow-500/20 border border-yellow-500/50 rounded-full text-xs text-yellow-400 font-semibold flex items-center gap-1">
                    ⭐ Premium
                  </span>
                )}
                <button
                  onClick={() => navigate('/profile')}
                  className="p-2 hover:bg-white/10 rounded-lg transition-all"
                  title="User profile"
                >
                  <User size={20} className="text-muted-foreground" />
                </button>
                <button
                  onClick={handleLogout}
                  className="p-2 hover:bg-white/10 rounded-lg transition-all"
                  title="Logout"
                >
                  <LogOut size={20} className="text-muted-foreground" />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => navigate('/login')}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-white/10 rounded-lg transition-colors"
                >
                  <LogIn size={18} />
                  Login
                </button>
                <button
                  onClick={() => navigate('/register')}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
                >
                  <UserPlus size={18} />
                  Sign Up
                </button>
              </>
            )}
          </motion.div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 hover:bg-white/10 rounded-lg transition-all"
          >
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <motion.nav
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="md:hidden mt-4 space-y-2 border-t border-white/10 pt-4"
          >
            {isAuthenticated ? (
              <>
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    to={item.href}
                    className="block px-4 py-2 text-sm text-muted-foreground hover:bg-white/10 rounded-lg transition-all"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {item.label}
                  </Link>
                ))}
                <div className="px-4 py-2 border-t border-white/10 mt-4 space-y-2">
                  {isPremium && (
                    <div className="inline-block mb-2 px-3 py-1 bg-yellow-500/20 border border-yellow-500/50 rounded-full text-xs text-yellow-400 font-semibold">
                      ⭐ Premium
                    </div>
                  )}
                  <button
                    onClick={() => {
                      navigate('/profile');
                      setIsMenuOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-muted-foreground hover:bg-white/10 rounded-lg transition-all flex items-center gap-2"
                  >
                    <User size={16} />
                    Profile
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-all flex items-center gap-2"
                  >
                    <LogOut size={16} />
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <div className="space-y-2">
                <button
                  onClick={() => {
                    navigate('/login');
                    setIsMenuOpen(false);
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-muted-foreground hover:bg-white/10 rounded-lg transition-all flex items-center gap-2"
                >
                  <LogIn size={16} />
                  Login
                </button>
                <button
                  onClick={() => {
                    navigate('/register');
                    setIsMenuOpen(false);
                  }}
                  className="w-full text-left px-4 py-2 text-sm bg-blue-600/50 hover:bg-blue-600 text-white rounded-lg transition-all flex items-center gap-2"
                >
                  <UserPlus size={16} />
                  Sign Up
                </button>
              </div>
            )}
          </motion.nav>
        )}
      </div>
    </header>
  );
}
