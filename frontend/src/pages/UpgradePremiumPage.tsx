/**
 * Premium Upgrade Checkout Page
 * 
 * Allows users to upgrade to premium with mock card information.
 * @module pages/UpgradePremiumPage
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store';
import { motion } from 'framer-motion';
import { Check, Lock, ArrowLeft, AlertCircle } from 'lucide-react';

export default function UpgradePremiumPage() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [formData, setFormData] = useState({
    cardName: 'John Doe',
    cardNumber: '4532 1234 5678 9010',
    expiryMonth: '12',
    expiryYear: '2026',
    cvv: '123',
  });

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle size={48} className="mx-auto text-red-400 mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Not Authenticated</h1>
          <p className="text-gray-300 mb-6">Please log in to upgrade to premium.</p>
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

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);

    try {
      // Call backend API to upgrade to premium
      const response = await fetch('/api/v1/auth/upgrade-premium/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to upgrade to premium');
      }

      const data = await response.json();

      // Update user in Zustand store with backend response
      setUser(data.user);

      setIsProcessing(false);
      setShowSuccess(true);

      // Redirect to profile after 2 seconds
      setTimeout(() => {
        navigate('/profile');
      }, 2000);
    } catch (error) {
      console.error('Premium upgrade failed:', error);
      setIsProcessing(false);
      // You could add error state here
    }
  };

  const premiumPrices = [
    { duration: '1 Month', price: '$9.99', value: 'monthly' },
    { duration: '6 Months', price: '$49.99', value: 'semi-annual', savings: 'Save 20%' },
    { duration: '1 Year', price: '$89.99', value: 'annual', savings: 'Save 25%' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 py-12 px-4 pb-24">
      <div className="max-w-5xl mx-auto">
        {/* Back Button */}
        <button
          onClick={() => navigate('/profile')}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors"
        >
          <ArrowLeft size={20} />
          Back to Profile
        </button>

        {showSuccess ? (
          // Success Screen
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center"
          >
            <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-3xl p-12 border border-green-500/30 max-w-md mx-auto">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 }}
                className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6"
              >
                <Check size={40} className="text-green-400" />
              </motion.div>
              <h2 className="text-3xl font-bold text-white mb-2">Welcome to Premium! 🎉</h2>
              <p className="text-gray-300 mb-6">Your account has been upgraded successfully.</p>
              <p className="text-sm text-gray-400">Redirecting to your profile...</p>
            </div>
          </motion.div>
        ) : (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Pricing Cards */}
            <div className="lg:col-span-1">
              <h3 className="text-2xl font-bold text-white mb-6">Choose Plan</h3>
              <div className="space-y-4">
                {premiumPrices.map((plan) => (
                  <motion.button
                    key={plan.value}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/20 text-left transition-all"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-white font-semibold">{plan.duration}</span>
                      <span className="text-xl font-bold text-cyan-400">{plan.price}</span>
                    </div>
                    {plan.savings && (
                      <span className="inline-block text-xs bg-green-500/30 text-green-400 px-2 py-1 rounded">
                        {plan.savings}
                      </span>
                    )}
                  </motion.button>
                ))}
              </div>

              {/* Premium Features List */}
              <div className="mt-10 p-6 rounded-xl bg-white/5 border border-white/20">
                <h4 className="text-white font-semibold mb-4">What's Included</h4>
                <ul className="space-y-3 text-sm text-gray-300">
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    District drill-down analysis
                  </li>
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    Satellite exposure data
                  </li>
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    Pollutant layer switching
                  </li>
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    Custom location reports
                  </li>
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    30-day trend analysis
                  </li>
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    PDF export
                  </li>
                  <li className="flex items-center gap-2">
                    <Check size={16} className="text-green-400 flex-shrink-0" />
                    Priority support
                  </li>
                </ul>
              </div>
            </div>

            {/* Payment Form */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="lg:col-span-2"
            >
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
                <div className="flex items-center gap-3 mb-4">
                  <img src="/Air_RISK_logo_onlyicon_removedbg.png" alt="Air RISK" className="w-12 h-12" />
                  <div className="flex items-baseline gap-1">
                    <h2 className="text-2xl font-bold text-white">Air</h2>
                    <h2 className="text-2xl font-bold text-transparent bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text">RISK</h2>
                    <span className="text-2xl font-bold text-yellow-400 ml-2">Premium</span>
                  </div>
                </div>
                <p className="text-gray-400 mb-8">Complete your payment to unlock all premium features.</p>

                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Order Summary */}
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10 mb-8">
                    <div className="flex justify-between mb-2">
                      <span className="text-gray-400">Premium 1 Year</span>
                      <span className="text-white font-semibold">$89.99</span>
                    </div>
                    <div className="border-t border-white/10 pt-4 flex justify-between">
                      <span className="text-white font-semibold">Total</span>
                      <span className="text-2xl font-bold text-cyan-400">$89.99</span>
                    </div>
                  </div>

                  {/* Cardholder Info */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2">
                      Cardholder Name
                    </label>
                    <input
                      type="text"
                      name="cardName"
                      value={formData.cardName}
                      onChange={handleInputChange}
                      placeholder="John Doe"
                      className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors"
                      required
                    />
                  </div>

                  {/* Card Number */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2">
                      Card Number
                    </label>
                    <input
                      type="text"
                      name="cardNumber"
                      value={formData.cardNumber}
                      onChange={handleInputChange}
                      placeholder="4532 1234 5678 9010"
                      maxLength={19}
                      className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-2">💳 Mock card: 4532 1234 5678 9010</p>
                  </div>

                  {/* Expiry & CVV */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-300 mb-2">
                        Expiry Date
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          name="expiryMonth"
                          value={formData.expiryMonth}
                          onChange={handleInputChange}
                          placeholder="MM"
                          min="1"
                          max="12"
                          maxLength={2}
                          className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors text-center"
                          required
                        />
                        <span className="text-white flex items-center">/</span>
                        <input
                          type="number"
                          name="expiryYear"
                          value={formData.expiryYear}
                          onChange={handleInputChange}
                          placeholder="YY"
                          min="2024"
                          max="2034"
                          maxLength={4}
                          className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors text-center"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-300 mb-2">
                        CVV
                      </label>
                      <input
                        type="password"
                        name="cvv"
                        value={formData.cvv}
                        onChange={handleInputChange}
                        placeholder="123"
                          maxLength={4}
                        className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors text-center font-mono"
                        required
                      />
                      <p className="text-xs text-gray-500 mt-2">Mock CVV: 123</p>
                    </div>
                  </div>

                  {/* Security Notice */}
                  <div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/20 flex items-start gap-3">
                    <Lock size={20} className="text-blue-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-300">
                      <strong>Demo Mode:</strong> This is a mock payment form for demonstration. No real charges will be made. Use the pre-filled test card details above.
                    </p>
                  </div>

                  {/* Submit Button */}
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    type="submit"
                    disabled={isProcessing}
                    className="w-full py-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-600 text-white font-bold rounded-lg transition-all flex items-center justify-center gap-2"
                  >
                    {isProcessing ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        Processing Payment...
                      </>
                    ) : (
                      <>
                        <Lock size={20} />
                        Complete Purchase
                      </>
                    )}
                  </motion.button>

                  {/* Terms */}
                  <p className="text-xs text-gray-500 text-center">
                    By clicking "Complete Purchase", you agree to our Terms of Service and will be charged ${formData.cardNumber ? '89.99' : '0.00'} annually.
                  </p>
                </form>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
