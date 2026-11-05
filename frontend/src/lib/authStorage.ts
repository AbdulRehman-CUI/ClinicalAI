const ACCESS_TOKEN_KEY = "clinicalai_access_token";
const REFRESH_TOKEN_KEY = "clinicalai_refresh_token";
const USER_KEY = "clinicalai_user";

export function getStoredAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setStoredAuthState(accessToken: string, refreshToken: string, user: unknown) {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  window.sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredAuthState() {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  window.sessionStorage.removeItem(USER_KEY);
}
