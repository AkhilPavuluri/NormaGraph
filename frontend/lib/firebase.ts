/**
 * Intentional mock Firebase layer for local / reference runs without project credentials.
 * Replace with firebase/app + firebase/auth if you need production auth.
 */

// Mock Firebase objects — no network calls
const mockAuth = {
  currentUser: null,
  onAuthStateChanged: () => () => {},
} as any;

const mockDb = {} as any;

const mockApp = {} as any;

const mockGoogleProvider = {} as any;

const mockAppleProvider = {} as any;

export const app = mockApp;
export const auth = mockAuth;
export const db = mockDb;
export const googleProvider = mockGoogleProvider;
export const appleProvider = mockAppleProvider;
