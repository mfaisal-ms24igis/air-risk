export type SubscriptionTier = 'BASIC' | 'PREMIUM';

export interface User {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    username: string;
    subscription_tier: SubscriptionTier;
    is_premium: boolean;
    premium_until?: string | null;
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
    date_joined?: string;
    preferences?: UserPreferences;
}

export interface UserPreferences {
    email_notifications: boolean;
    push_notifications: boolean;
    theme: 'light' | 'dark' | 'system';
}

export interface AuthResponse {
    access: string;
    refresh: string;
    user?: User;
}

export interface LoginRequest {
    username: string;
    password: string;
}

export interface RegisterRequest {
    username: string;
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
}

export interface TokenPayload {
    token_type: string;
    exp: number;
    iat: number;
    jti: string;
    user_id: number;
    tier: SubscriptionTier;
    is_premium: boolean;
}
