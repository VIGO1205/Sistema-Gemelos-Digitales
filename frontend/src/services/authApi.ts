import api from './api';
import { UserRole } from '../types';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  avatar_url?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export const authApi = {
  login: (credentials: LoginCredentials) =>
    api.post<LoginResponse>('/api/auth/login-json', credentials),

  getMe: () =>
    api.get<AuthUser>('/api/auth/me'),
};

export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem('m6_auth_token', token);
  } else {
    localStorage.removeItem('m6_auth_token');
  }
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem('m6_auth_token');
};
