import { writable } from 'svelte/store';

const GUEST_SESSION = {
  user: 'guestuser',
  userID: 'guestuser',
  token: null,
  isGuest: true
};

export const session = writable(GUEST_SESSION);

export function setSession(sessionData) {
  session.set({
    user: sessionData.user || 'guestuser',
    userID: sessionData.userID || 'guestuser',
    token: sessionData.token ?? null,
    isGuest: sessionData.user === 'guestuser' && sessionData.userID === 'guestuser'
  });
}

export function initializeGuestSession() {
  session.set(GUEST_SESSION);
}
