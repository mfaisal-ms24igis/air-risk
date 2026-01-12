import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Button, Form, Input, message } from 'antd';
import { LockOutlined, MailOutlined } from '@ant-design/icons';
import './Auth.css';



export default function RegisterPage() {
    const [error, setError] = useState<string | null>(null);
    const { register, isLoading } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (values: any) => {
        setError(null);
        if (values.password !== values.confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        try {
            await register({
                username: values.email, // Use email as username
                email: values.email,
                password: values.password,
                password_confirm: values.confirmPassword,
                first_name: values.firstName,
                last_name: values.lastName
            });
            message.success("Registration successful! Welcome aboard.");
            navigate('/');
        } catch (err: any) {
            console.error("Registration Error:", err);
            let msg = 'Registration failed. Please try again.';

            // err is ApiError from axios interceptor
            if (err.status === 'error') {
                if (err.message) {
                    msg = err.message;
                }

                if (err.errors) {
                    const errorMessages = Object.entries(err.errors).map(([key, val]) => {
                        const errorText = Array.isArray(val) ? val.join(' ') : String(val);
                        const field = key.charAt(0).toUpperCase() + key.slice(1);
                        return `${field}: ${errorText}`;
                    });
                    if (errorMessages.length > 0) {
                        msg = errorMessages.join('\n');
                    }
                }
            } else if (err.response?.data) {
                // Fallback for unexpected errors that bypassed the interceptor
                const data = err.response.data;
                if (typeof data === 'string') msg = data;
                else if (data.detail) msg = data.detail;
            }

            setError(msg);
            message.error(msg); // Show toast as well
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
                    Create your account
                </h2>
                <p className="auth-subtitle">
                    Already have an account?{' '}
                    <Link to="/login">
                        Sign in
                    </Link>
                </p>
            </div>

            <div className="auth-card-container">
                <div className="auth-card">
                    {error && <div className="auth-error">{error}</div>}

                    <Form
                        name="register"
                        onFinish={handleSubmit}
                        layout="vertical"
                        className="space-y-6"
                    >
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '1rem', width: '100%' }}>
                            <Form.Item
                                label="First Name"
                                name="firstName"
                                rules={[{ required: true, message: 'Required' }]}
                                style={{ marginBottom: 0 }}
                            >
                                <Input size="large" />
                            </Form.Item>
                            <Form.Item
                                label="Last Name"
                                name="lastName"
                                rules={[{ required: true, message: 'Required' }]}
                                style={{ marginBottom: 0 }}
                            >
                                <Input size="large" />
                            </Form.Item>
                        </div>

                        <Form.Item
                            label="Email address"
                            name="email"
                            rules={[
                                { required: true, message: 'Please input your email!' },
                                { type: 'email', message: 'Invalid email format' }
                            ]}
                        >
                            <Input
                                prefix={<MailOutlined className="site-form-item-icon" />}
                                placeholder="you@example.com"
                                size="large"
                            />
                        </Form.Item>

                        <Form.Item
                            label="Password"
                            name="password"
                            rules={[{ required: true, message: 'Please input your password!' }, { min: 8, message: 'Min 8 characters' }]}
                        >
                            <Input.Password
                                prefix={<LockOutlined className="site-form-item-icon" />}
                                placeholder="••••••••"
                                size="large"
                            />
                        </Form.Item>

                        <Form.Item
                            label="Confirm Password"
                            name="confirmPassword"
                            rules={[{ required: true, message: 'Please confirm your password!' }]}
                        >
                            <Input.Password
                                prefix={<LockOutlined className="site-form-item-icon" />}
                                placeholder="••••••••"
                                size="large"
                            />
                        </Form.Item>

                        <div>
                            <Button
                                type="primary"
                                htmlType="submit"
                                loading={isLoading}
                                block
                                size="large"
                                style={{ height: '3rem', fontSize: '1.125rem', fontWeight: 600 }}
                            >
                                Create Account
                            </Button>
                        </div>
                    </Form>

                    <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                        <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                            By signing up, you agree to our <a href="#" style={{ color: '#2563eb', textDecoration: 'none' }}>Terms of Service</a> and <a href="#" style={{ color: '#2563eb', textDecoration: 'none' }}>Privacy Policy</a>.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
