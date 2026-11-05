import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import axios, { type InternalAxiosRequestConfig } from "axios";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { apiClient } from "../api/client";
import {
  clearStoredAuthState,
  getStoredAccessToken,
  getStoredRefreshToken,
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
  register: (
    fullName: string,
    email: string,
    password: string,
    role: string,
  ) => Promise<void>;
  logout: () => void;
};
const AuthContext = createContext<AuthState | undefined>(undefined);

async function loadCurrentUser(accessToken: string): Promise<AuthUser> {
  const response = await apiClient.get<ApiResponse<AuthUser>>(
    "/auth/users/me",
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  const profile = response.data.data;
  if (!response.data.success || !profile?.id || !profile.is_active)
    throw new Error(
      "The server could not verify your account. Please sign in again.",
    );
  return profile;
}

async function refreshSession(refreshToken: string) {
  const response = await apiClient.post<ApiResponse<AuthPayload>>(
    "/auth/refresh",
    { refresh_token: refreshToken },
  );
  const tokens = response.data.data;
  if (!response.data.success || !tokens?.access_token || !tokens.refresh_token)
    throw new Error("Your session could not be renewed. Please sign in again.");
  const profile = await loadCurrentUser(tokens.access_token);
  return { tokens, profile };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const version = useRef(0);
  const renewal = useRef<ReturnType<typeof refreshSession> | null>(null);
  const navigate = useNavigate();

  function acceptSession(tokens: AuthPayload, profile: AuthUser) {
    setStoredAuthState(tokens.access_token, tokens.refresh_token, profile);
    setUser(profile);
    setAccessToken(tokens.access_token);
  }
  function clearSession() {
    clearStoredAuthState();
    setUser(null);
    setAccessToken(null);
  }

  useEffect(() => {
    let cancelled = false;
    const attempt = version.current;
    async function restore() {
      const token = getStoredAccessToken();
      if (!token) {
        clearStoredAuthState();
        setIsLoading(false);
        return;
      }
      try {
        let next: { tokens: AuthPayload; profile: AuthUser };
        try {
          next = {
            tokens: {
              access_token: token,
              refresh_token: getStoredRefreshToken() || "",
              token_type: "bearer",
            },
            profile: await loadCurrentUser(token),
          };
        } catch (error) {
          const refreshToken = getStoredRefreshToken();
          if (
            !axios.isAxiosError(error) ||
            error.response?.status !== 401 ||
            !refreshToken
          )
            throw error;
          const pending = (renewal.current ??= refreshSession(refreshToken));
          try {
            next = await pending;
          } finally {
            if (renewal.current === pending) renewal.current = null;
          }
        }
        if (!cancelled && attempt === version.current)
          acceptSession(next.tokens, next.profile);
      } catch {
        if (!cancelled && attempt === version.current) clearSession();
      } finally {
        if (!cancelled && attempt === version.current) setIsLoading(false);
      }
    }
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const requestInterceptor = apiClient.interceptors.request.use((config) => {
      const token = getStoredAccessToken();
      // Preserve an explicit token when validating a newly issued session.
      if (token && !config.headers.has("Authorization"))
        config.headers.set("Authorization", `Bearer ${token}`);
      return config;
    });
    const responseInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error: unknown) => {
        if (!axios.isAxiosError(error)) return Promise.reject(error);
        const request = error.config as
          (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
        if (
          error.response?.status !== 401 ||
          !request ||
          request._retry ||
          !user ||
          request.url?.startsWith("/auth/")
        )
          return Promise.reject(error);
        request._retry = true;
        const refreshToken = getStoredRefreshToken();
        const attempt = version.current;
        if (!refreshToken) {
          clearSession();
          navigate("/login", { replace: true });
          return Promise.reject(error);
        }
        const pending = (renewal.current ??= refreshSession(refreshToken));
        try {
          const next = await pending;
          if (attempt !== version.current) return Promise.reject(error);
          acceptSession(next.tokens, next.profile);
          request.headers.set(
            "Authorization",
            `Bearer ${next.tokens.access_token}`,
          );
          return apiClient(request);
        } catch (refreshError) {
          if (attempt === version.current) {
            clearSession();
            navigate("/login", { replace: true });
            toast.error(
              "Your session could not be verified. Please sign in again.",
            );
          }
          return Promise.reject(refreshError);
        } finally {
          if (renewal.current === pending) renewal.current = null;
        }
      },
    );
    return () => {
      apiClient.interceptors.request.eject(requestInterceptor);
      apiClient.interceptors.response.eject(responseInterceptor);
    };
  }, [user, navigate]);

  async function authenticate(
    path: "login" | "register",
    payload: Record<string, string>,
  ) {
    const attempt = ++version.current;
    renewal.current = null;
    clearSession();
    setIsLoading(true);
    try {
      const response = await apiClient.post<ApiResponse<AuthPayload>>(
        `/auth/${path}`,
        payload,
      );
      const tokens = response.data.data;
      if (
        !response.data.success ||
        !tokens?.access_token ||
        !tokens.refresh_token
      )
        throw new Error(
          "The server did not return a valid session. Please try again.",
        );
      const profile = await loadCurrentUser(tokens.access_token);
      if (attempt !== version.current) return;
      acceptSession(tokens, profile);
      toast.success(
        path === "login" ? "Login successful." : "Registration successful.",
      );
      navigate("/");
    } catch (error) {
      if (attempt === version.current) clearSession();
      throw error;
    } finally {
      if (attempt === version.current) setIsLoading(false);
    }
  }
  async function login(email: string, password: string) {
    await authenticate("login", { email, password });
  }
  async function register(
    fullName: string,
    email: string,
    password: string,
    role: string,
  ) {
    await authenticate("register", {
      full_name: fullName,
      email,
      password,
      role,
    });
  }
  function logout() {
    version.current++;
    renewal.current = null;
    clearSession();
    setIsLoading(false);
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
    [user, accessToken, isLoading],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
