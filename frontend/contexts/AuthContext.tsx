'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { devLog } from '@/lib/devLog'

/** Demo auth only — pairs with mocked firebase.ts; not secure for production. */
interface MockUser {
  uid: string
  email: string | null
  displayName: string | null
  /** Optional; mock auth usually omits this */
  photoURL?: string | null
}

interface AuthContextType {
  user: MockUser | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signInWithApple: () => Promise<void>
  signInAnonymously: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  signUpWithEmail: (email: string, password: string, displayName?: string) => Promise<void>
  signOut: () => Promise<void>
  resetPassword: (email: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: false,
  signInWithGoogle: async () => {},
  signInWithApple: async () => {},
  signInAnonymously: async () => {},
  signInWithEmail: async () => {},
  signUpWithEmail: async () => {},
  signOut: async () => {},
  resetPassword: async () => {},
})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Mock user - always signed in as anonymous guest
  const [user, setUser] = useState<MockUser | null>({
    uid: 'guest-user',
    email: null,
    displayName: 'Guest User',
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Simulate loading complete
    setLoading(false)
  }, [])

  const signInWithGoogle = async () => {
    // Mock sign in - just set a user
    setUser({
      uid: 'google-user',
      email: 'user@example.com',
      displayName: 'Google User',
    })
  }

  const signInWithApple = async () => {
    // Mock sign in - just set a user
    setUser({
      uid: 'apple-user',
      email: 'user@example.com',
      displayName: 'Apple User',
    })
  }

  const signInAnonymously = async () => {
    // Mock anonymous sign in
    setUser({
      uid: 'guest-user',
      email: null,
      displayName: 'Guest User',
    })
  }

  const signInWithEmail = async (email: string, password: string) => {
    // Mock email sign in
    setUser({
      uid: `email-user-${Date.now()}`,
      email: email,
      displayName: email.split('@')[0],
    })
  }

  const signUpWithEmail = async (email: string, password: string, displayName?: string) => {
    // Mock sign up
    setUser({
      uid: `email-user-${Date.now()}`,
      email: email,
      displayName: displayName || email.split('@')[0],
    })
  }

  const resetPassword = async (email: string) => {
    devLog('Password reset (demo — no email sent):', email)
  }

  const signOut = async () => {
    // Mock sign out - set back to guest
    setUser({
      uid: 'guest-user',
      email: null,
      displayName: 'Guest User',
    })
  }

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      signInWithGoogle, 
      signInWithApple,
      signInAnonymously,
      signInWithEmail,
      signUpWithEmail,
      signOut,
      resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
