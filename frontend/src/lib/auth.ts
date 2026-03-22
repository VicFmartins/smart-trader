const TOKEN_STORAGE_KEY = "carteiraconsol.access_token";
export const UNAUTHORIZED_SESSION_EVENT = "carteiraconsol:unauthorized";

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getStoredAccessToken() {
  if (!canUseStorage()) {
    return null;
  }
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredAccessToken(token: string) {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredAccessToken() {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function emitUnauthorizedSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(UNAUTHORIZED_SESSION_EVENT));
}
