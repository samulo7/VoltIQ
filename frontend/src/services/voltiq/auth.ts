import { request } from '@umijs/max';

export type UserRole = 'operator' | 'sales' | 'manager';

export type AuthUser = {
  id: string;
  username: string;
  role: UserRole;
  status: 'active' | 'disabled';
};

export type TokenPair = {
  token_type: 'bearer';
  access_token: string;
  refresh_token: string;
  access_expires_in_seconds: number;
  refresh_expires_in_seconds: number;
};

export type LoginResponse = TokenPair & {
  user: AuthUser;
};

export type LoginPayload = {
  username: string;
  password: string;
};

const ACCESS_TOKEN_KEY = 'voltiq.access_token';
const REFRESH_TOKEN_KEY = 'voltiq.refresh_token';

const canUseStorage = () => typeof window !== 'undefined';

export const authStorage = {
  getAccessToken: (): string | null => {
    if (!canUseStorage()) return null;
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  getRefreshToken: (): string | null => {
    if (!canUseStorage()) return null;
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setTokens: (tokenPair: TokenPair) => {
    if (!canUseStorage()) return;
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokenPair.access_token);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokenPair.refresh_token);
  },
  clear: () => {
    if (!canUseStorage()) return;
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export async function loginByPassword(payload: LoginPayload) {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    data: payload,
  });
}

export async function refreshToken(refreshToken: string) {
  return request<TokenPair>('/auth/refresh', {
    method: 'POST',
    data: { refresh_token: refreshToken },
  });
}

export async function getCurrentUser() {
  return request<AuthUser>('/auth/me', {
    method: 'GET',
  });
}
