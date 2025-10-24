/**
 * Firebase Authentication Service
 * Handles user authentication and token management
 */

import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged, User } from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

export interface AuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  emailVerified: boolean;
}

class AuthService {
  private currentUser: AuthUser | null = null;
  private authToken: string | null = null;
  private callbacks: ((user: AuthUser | null) => void)[] = [];

  constructor() {
    // Listen for auth state changes
    onAuthStateChanged(auth, async (user) => {
      if (user) {
        this.currentUser = {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL,
          emailVerified: user.emailVerified,
        };
        
        // Get ID token
        this.authToken = await user.getIdToken();
      } else {
        this.currentUser = null;
        this.authToken = null;
      }
      
      // Notify callbacks
      this.callbacks.forEach(callback => callback(this.currentUser));
    });
  }

  async signInWithGoogle(): Promise<AuthUser> {
    try {
      const result = await signInWithPopup(auth, provider);
      const user = result.user;
      
      this.currentUser = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        photoURL: user.photoURL,
        emailVerified: user.emailVerified,
      };
      
      this.authToken = await user.getIdToken();
      
      return this.currentUser;
    } catch (error) {
      console.error('Sign in error:', error);
      throw error;
    }
  }

  async signOut(): Promise<void> {
    try {
      await signOut(auth);
      this.currentUser = null;
      this.authToken = null;
    } catch (error) {
      console.error('Sign out error:', error);
      throw error;
    }
  }

  getCurrentUser(): AuthUser | null {
    return this.currentUser;
  }

  getAuthToken(): string | null {
    return this.authToken;
  }

  async refreshToken(): Promise<string | null> {
    const user = auth.currentUser;
    if (user) {
      this.authToken = await user.getIdToken(true);
      return this.authToken;
    }
    return null;
  }

  isAuthenticated(): boolean {
    return this.currentUser !== null;
  }

  onAuthStateChange(callback: (user: AuthUser | null) => void): () => void {
    this.callbacks.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.callbacks.indexOf(callback);
      if (index > -1) {
        this.callbacks.splice(index, 1);
      }
    };
  }

  // Utility method to check if user is verified
  isEmailVerified(): boolean {
    return this.currentUser?.emailVerified || false;
  }

  // Utility method to get user display name or email
  getUserDisplayName(): string {
    if (!this.currentUser) return 'Anonymous';
    return this.currentUser.displayName || this.currentUser.email || 'Anonymous';
  }
}

export const authService = new AuthService();
export { auth };
