import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Button, Form, Input, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '@/store';
import './Auth.css';

export default function LoginPage() {
    const [error, setError] = useState<string | null>(null);
    const { login, isLoading } = useAuth();
    const { setTokens, setUser } = useAuthStore();
    const navigate = useNavigate();

    const handleSubmit = async (values: any) => {
        setError(null);
        try {
            // Backend expects 'username' field, even if we use email
            await login({ username: values.email, password: values.password });
            
            // Also update Zustand store for Header/Profile components
            const accessToken = localStorage.getItem('access_token');
            const refreshToken = localStorage.getItem('refresh_token');
            
            if (accessToken && refreshToken) {
              // Set tokens first
              setTokens({ access: accessToken, refresh: refreshToken });
              
              // Fetch and set user in Zustand store
              try {
                const profileResponse = await fetch('/api/v1/auth/profile/', {
                  headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json',
                  },
                });
                if (profileResponse.ok) {
                  const userData = await profileResponse.json();
                  setUser(userData);
                  
                  // Small delay to ensure store is updated before navigation
                  setTimeout(() => {
                    navigate('/profile');
                  }, 100);
                } else {
                  navigate('/');
                }
              } catch (err) {
                console.error('Failed to fetch user profile:', err);
                navigate('/');
              }
            } else {
              navigate('/');
            }
        } catch (err: any) {
            console.error("Login Handler Error:", err);
            let msg = 'Failed to log in. Please check your credentials.';

            if (err.status === 'error') {
                if (err.message) {
                    msg = err.message;
                }
                // Handle field errors (e.g. { detail: "No active account found with the given credentials" })
                if (err.errors) {
                    const errorMessages = Object.entries(err.errors).map(([, val]) => {
                        // Simplify validation messages for login
                        return Array.isArray(val) ? val.join(' ') : String(val);
                    });
                    if (errorMessages.length > 0) msg = errorMessages.join('\n');
                }
            } else if (err.response?.data?.detail) {
                msg = err.response.data.detail;
            }

            setError(msg);
            message.error(msg);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-header">
                <div className="flex items-center justify-center gap-3 mb-4">
                    <img src="/Air_RISK_logo_onlyicon_removedbg.png" alt="Air RISK" className="w-16 h-16" />
                    <div className="flex items-baseline gap-1">
                        <h1 className="text-3xl font-bold text-gray-900">Air</h1>
                        <h1 className="text-3xl font-bold text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 bg-clip-text">RISK</h1>
                    </div>
                </div>
                <h2 className="auth-title">
                    Sign in to your account
                </h2>
                <p className="auth-subtitle">
                    Or{' '}
                    <Link to="/register">
                        start your 14-day free trial
                    </Link>
                </p>
            </div>

            <div className="auth-card-container">
                <div className="auth-card">
                    {error && <div className="auth-error">{error}</div>}

                    <Form
                        name="login"
                        onFinish={handleSubmit}
                        layout="vertical"
                        initialValues={{ remember: true }}
                        className="space-y-6"
                    >
                        <Form.Item
                            label="Email address"
                            name="email"
                            rules={[
                                { required: true, message: 'Please input your email!' },
                                { type: 'email', message: 'Please enter a valid email!' }
                            ]}
                        >
                            <Input
                                prefix={<UserOutlined className="site-form-item-icon" />}
                                placeholder="you@example.com"
                                size="large"
                            />
                        </Form.Item>

                        <Form.Item
                            label="Password"
                            name="password"
                            rules={[{ required: true, message: 'Please input your password!' }]}
                        >
                            <Input.Password
                                prefix={<LockOutlined className="site-form-item-icon" />}
                                placeholder="••••••••"
                                size="large"
                            />
                        </Form.Item>

                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <input
                                    id="remember-me"
                                    name="remember-me"
                                    type="checkbox"
                                    style={{ marginRight: '0.5rem' }}
                                />
                                <label htmlFor="remember-me" style={{ fontSize: '0.875rem' }}>
                                    Remember me
                                </label>
                            </div>

                            <div style={{ fontSize: '0.875rem' }}>
                                <a href="#" style={{ color: '#2563eb', textDecoration: 'none' }}>
                                    Forgot your password?
                                </a>
                            </div>
                        </div>

                        <div>
                            <Button
                                type="primary"
                                htmlType="submit"
                                loading={isLoading}
                                block
                                size="large"
                                style={{ height: '3rem', fontSize: '1.125rem', fontWeight: 600 }}
                            >
                                Sign in
                            </Button>
                        </div>
                    </Form>

                    <div className="auth-separator">
                        <div className="auth-separator-line">
                            <div />
                        </div>
                        <div className="auth-separator-text">
                            <span>Or continue with</span>
                        </div>
                    </div>

                    <div className="social-buttons">
                        <button className="social-btn">
                            <span className="sr-only">Sign in with Google</span>
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true" style={{ width: '1.25rem', height: '1.25rem' }}>
                                <path d="M12.48 10.92v3.26h7.96c-.16 1.05-.72 2.22-1.74 3.29-1.39 1.48-3.48 2.22-6.22 2.22-5.4 0-9.68-4.54-9.68-10.03 0-5.5 4.28-10.03 9.68-10.03 2.87 0 4.88 1.05 6.13 2.22l2.36-2.52C19.26 5.86 16.29 5 12.48 5 6.64 5 1.7 9.87 1.7 15.6s4.94 10.6 10.78 10.6c3.15 0 5.61-1.05 7.42-2.92 1.89-1.92 2.45-5.06 2.45-7.03 0-.61-.06-1.12-.14-1.63h-9.73z" />
                            </svg>
                        </button>
                        <button className="social-btn">
                            <span className="sr-only">Sign in with GitHub</span>
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true" style={{ width: '1.25rem', height: '1.25rem' }}>
                                <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
