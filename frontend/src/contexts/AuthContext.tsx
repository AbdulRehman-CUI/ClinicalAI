import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { apiClient, getApiErrorMessage } from "../api/client";
import {
  clearStoredAuthState,
  getStoredAccessToken,
  getStoredRefreshToken,
  getStoredUser,
  setStoredAuthState,
} from "../lib/authStorage";
import type { ApiResponse } from "../types/api";

type AuthUser = {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type AuthUserPayload = {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type AuthPayload = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type AuthState = {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string, role: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | undefined>(undefined);

function normalizeUser(payload: AuthUserPayload): AuthUser {
  return {
    id: payload.id,
    full_name: payload.full_name,
    email: payload.email,
    role: payload.role,
    is_active: payload.is_active,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

function decodeJwtPayload(token: string) {
  try {
    const tokenParts = token.split(".");
    if (tokenParts.length < 2) {
      return null;
    }

    const payload = tokenParts[1];
    const normalizedPayload = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padding = normalizedPayload.length % 4;
    const paddedPayload = padding === 0 ? normalizedPayload : normalizedPayload + "=".repeat(4 - padding);
    const decoded = window.atob(paddedPayload);
    return JSON.parse(decoded) as { sub?: string; role?: string };
  } catch {
    return null;
  }
}

async function loadCurrentUser(accessToken: string, fallbackUser?: AuthUserPayload | null): Promise<AuthUser> {
  try {
    const response = await apiClient.get<ApiResponse<AuthUserPayload>>("/auth/users/me", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    const profile = response.data.data;
    if (!profile) {
      throw new Error("Unable to load user profile.");
    }

    return normalizeUser(profile);
  } catch (error) {
    const decodedPayload = decodeJwtPayload(accessToken);
    if (decodedPayload?.role) {
      return {
        id: Number(decodedPayload.sub ?? 0),
        full_name: fallbackUser?.full_name ?? "",
        email: fallbackUser?.email ?? "",
        role: decodedPayload.role,
        is_active: true,
        created_at: fallbackUser?.created_at ?? new Date().toISOString(),
        updated_at: fallbackUser?.updated_at ?? new Date().toISOString(),
      };
    }

    throw error;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(getStoredAccessToken());
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function restoreStoredSession() {
      const storedUser = getStoredUser() as AuthUser | null;
      if (storedUser) {
        setUser(storedUser);
        setIsLoading(false);
        return;
      }

      const storedAccessToken = getStoredAccessToken();
      if (storedAccessToken) {
        try {
          const restoredUser = await loadCurrentUser(storedAccessToken);
          setUser(restoredUser);
          setStoredAuthState(storedAccessToken, getStoredRefreshToken() ?? "", restoredUser);
        } catch {
          clearStoredAuthState();
          setUser(null);
          setAccessToken(null);
        }
      }

      setIsLoading(false);
    }

    void restoreStoredSession();
  }, []);

  useEffect(() => {
    const interceptor = apiClient.interceptors.request.use((config) => {
      if (!accessToken) {
        return config;
      }
      config.headers.set("Authorization", `Bearer ${accessToken}`);
      return config;
    });

    return () => {
      apiClient.interceptors.request.eject(interceptor);
    };
  }, [accessToken]);

  async function login(email: string, password: string) {
    setIsLoading(true);
    try {
      const response = await apiClient.post<ApiResponse<AuthPayload>>(
        "/auth/login",
        { email, password },
      );
      const payload = response.data.data;
      if (!payload?.access_token) {
        throw new Error(response.data.message || "Login failed.");
      }

      const nextUser = await loadCurrentUser(payload.access_token);
      setUser(nextUser);
      setAccessToken(payload.access_token);
      setStoredAuthState(payload.access_token, payload.refresh_token, nextUser);
      toast.success("Login successful.");
      navigate("/");
    } catch (error) {
      const message = getApiErrorMessage(error, "Login failed.");
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }

  async function register(fullName: string, email: string, password: string, role: string) {
    setIsLoading(true);
    try {
      const response = await apiClient.post<ApiResponse<AuthPayload & AuthUserPayload>>(
        "/auth/register",
        { full_name: fullName, email, password, role },
      );
      const payload = response.data.data;
      if (!payload?.access_token) {
        throw new Error(response.data.message || "Registration failed.");
      }

      const nextUser = await loadCurrentUser(payload.access_token, payload);
      setUser(nextUser);
      setAccessToken(payload.access_token);
      setStoredAuthState(payload.access_token, payload.refresh_token, nextUser);
      toast.success("Registration successful.");
      navigate("/");
    } catch (error) {
      const message = getApiErrorMessage(error, "Registration failed.");
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }

  function logout() {
    clearStoredAuthState();
    setUser(null);
    setAccessToken(null);
    toast.success("You have been logged out.");
    navigate("/login");
  }

  const value = useMemo<AuthState>(
    () => ({
      user,
      accessToken,
      isAuthenticated: Boolean(user && accessToken),
      isLoading,
      login,
      register,
      logout,
    }),
    [accessToken, isLoading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
