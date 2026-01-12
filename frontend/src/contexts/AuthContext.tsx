import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, LoginResponse } from '@/types/auth'; // Ensure this path is correct
import api from '@/lib/axios';

// =============================================================================
// Types
// =============================================================================

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (credentials: any) => Promise<void>;
    register: (data: any) => Promise<void>;
    logout: () => void;
    updateProfile: (data: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Define logout first so it can be used in initAuth
    const logout = React.useCallback(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
        // Optional: Call logout endpoint to blacklist token
    }, []);

    // Load user from local storage or verify token on mount
    useEffect(() => {
        const initAuth = async () => {
            const token = localStorage.getItem('access_token');
            if (token) {
                try {
                    // Verify token and get user profile
                    // Override baseURL because auth endpoints are at /api/v1/auth/, not /api/v1/air-quality/auth/
                    const userProfile = await api.get<User, User>('/auth/profile/', { baseURL: '/api/v1' });
                    setUser(userProfile);
                } catch (error) {
                    console.error("Auth init failed:", error);
                    logout(); // Invalid token
                }
            }
            setIsLoading(false);
        };

        initAuth();
    }, [logout]); // Now logout is in dependencies

    const login = async (credentials: any) => {
        try {
            // The backend returns { access, refresh, user }
            const response = await api.post<LoginResponse, LoginResponse>('/auth/login/', credentials, { baseURL: '/api/v1' });

            const { access, refresh, user: userData } = response;

            localStorage.setItem('access_token', access);
            localStorage.setItem('refresh_token', refresh);
            setUser(userData);

        } catch (error) {
            console.error("Login failed:", error);
            throw error;
        }
    };

    const register = async (data: any) => {
        try {
            // Registration usually returns the user or tokens directly
            const response = await api.post<LoginResponse, LoginResponse>('/auth/register/', data, { baseURL: '/api/v1' });

            const { access, refresh, user: userData } = response;
            localStorage.setItem('access_token', access);
            localStorage.setItem('refresh_token', refresh);
            setUser(userData);

        } catch (error) {
            console.error("Registration failed:", error);
            throw error;
        }
    };

    // logout is defined above as useCallback

    const updateProfile = async (data: Partial<User>) => {
        try {
            const updatedUser = await api.put<User, User>('/auth/profile/', data, { baseURL: '/api/v1' });
            // Assuming axios interceptor unwraps the response, updatedUser is User
            setUser((prev) => prev ? { ...prev, ...updatedUser } : null);
        } catch (error) {
            console.error("Profile update failed:", error);
            throw error;
        }
    }

    return (
        <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, register, logout, updateProfile }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
