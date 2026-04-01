'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { BrandMark } from '@/components/BrandMark'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Brain, Loader2, Eye, EyeOff, UserX } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'
import { toast } from 'sonner'

export default function LoginPage() {
  const router = useRouter()
  const { signInWithGoogle, signInWithApple, signInAnonymously, signInWithEmail, resetPassword } = useAuth()
  const [signingIn, setSigningIn] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [errors, setErrors] = useState<{
    email?: string
    password?: string
  }>({})

  const validateForm = () => {
    const newErrors: typeof errors = {}

    if (!formData.email) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format'
    }

    if (!formData.password) {
      newErrors.password = 'Password is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setSigningIn(true)
    try {
      await signInWithEmail(formData.email, formData.password)
      toast.success('Signed in successfully!')
      router.push('/chat')
    } catch (error: any) {
      console.error('Login error:', error)
      if (error.code === 'auth/user-not-found') {
        toast.error('No account found with this email. Please sign up.')
      } else if (error.code === 'auth/wrong-password') {
        toast.error('Incorrect password. Please try again.')
      } else if (error.code === 'auth/invalid-email') {
        toast.error('Invalid email address.')
      } else if (error.code === 'auth/user-disabled') {
        toast.error('This account has been disabled.')
      } else {
        toast.error(error.message || 'Failed to sign in. Please try again.')
      }
    } finally {
      setSigningIn(false)
    }
  }

  const handleGoogleSignIn = async () => {
    setSigningIn(true)
    try {
      await signInWithGoogle()
      toast.success('Signed in with Google!')
      router.push('/chat')
    } catch (error: any) {
      console.error('Google signin error:', error)
      if (error.code !== 'auth/popup-closed-by-user') {
        toast.error('Failed to sign in with Google. Please try again.')
      }
    } finally {
      setSigningIn(false)
    }
  }

  const handleAppleSignIn = async () => {
    setSigningIn(true)
    try {
      await signInWithApple()
      toast.success('Signed in with Apple!')
      router.push('/chat')
    } catch (error: any) {
      console.error('Apple signin error:', error)
      if (error.code !== 'auth/popup-closed-by-user') {
        toast.error('Failed to sign in with Apple. Please try again.')
      }
    } finally {
      setSigningIn(false)
    }
  }

  const handleAnonymousSignIn = async () => {
    setSigningIn(true)
    try {
      await signInAnonymously()
      toast.success('Signed in anonymously!')
      router.push('/chat')
    } catch (error: any) {
      console.error('Anonymous signin error:', error)
      toast.error('Failed to sign in anonymously. Please try again.')
    } finally {
      setSigningIn(false)
    }
  }

  const handleForgotPassword = async () => {
    if (!formData.email) {
      toast.error('Please enter your email address first.')
      return
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      toast.error('Please enter a valid email address.')
      return
    }

    try {
      await resetPassword(formData.email)
      toast.success('Password reset email sent! Check your inbox.')
      setShowForgotPassword(false)
    } catch (error: any) {
      console.error('Password reset error:', error)
      toast.error(error.message || 'Failed to send password reset email.')
    }
  }

  return (
    <div className="h-screen bg-background text-foreground flex overflow-hidden">
      {/* Left Side - Branding Section */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-gradient-to-br from-primary via-indigo-700 to-slate-950 p-6 xl:p-8 flex-col justify-between overflow-hidden">
        {/* Logo */}
        <div className="z-10 flex-shrink-0">
          <BrandMark
            className="border-white/20 bg-white/10 p-2.5 text-white"
            iconClassName="h-9 w-9 sm:h-10 sm:w-10 text-white"
          />
        </div>

        {/* Content */}
        <div className="z-10 text-white space-y-4 max-w-md flex-1 flex flex-col justify-center">
          <div className="space-y-3">
            <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
              <Brain className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl xl:text-4xl font-bold leading-tight">
              Welcome to NormaGraph
            </h1>
            <p className="text-base xl:text-lg text-white/90 leading-relaxed">
              Domain-aware policy intelligence — structured retrieval and explainable findings for regulatory and policy documents.
            </p>
          </div>
          <div className="space-y-2 pt-2">
            <div className="flex items-center gap-2 text-sm text-white/90">
              <div className="w-1.5 h-1.5 bg-white rounded-full flex-shrink-0"></div>
              <span>Hybrid semantic + structured retrieval</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-white/90">
              <div className="w-1.5 h-1.5 bg-white rounded-full flex-shrink-0"></div>
              <span>Traceable sources &amp; context</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-white/90">
              <div className="w-1.5 h-1.5 bg-white rounded-full flex-shrink-0"></div>
              <span>Observable analysis pipeline</span>
            </div>
          </div>
        </div>

        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 -left-48 w-96 h-96 bg-white/10 rounded-full blur-3xl"></div>
          <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-white/10 rounded-full blur-3xl"></div>
        </div>
      </div>

      {/* Right Side - Form Section */}
      <div className="w-full lg:w-1/2 flex flex-col relative overflow-y-auto">
        {/* Logo and Theme Toggle for mobile */}
        <div className="flex items-center justify-between p-4 sm:p-6 lg:absolute lg:top-4 lg:right-4 lg:left-4 lg:p-0 flex-shrink-0">
          <div className="lg:hidden">
            <BrandMark className="p-1.5 backdrop-blur-sm" />
          </div>
          <ThemeToggle />
        </div>

        {/* Form Container */}
        <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8 max-w-2xl w-full mx-auto min-h-0">
          <Card className="w-full bg-card border-border backdrop-blur-sm shadow-lg">
        <CardHeader className="space-y-3 p-4 sm:p-6">
          <div className="flex justify-center lg:justify-start">
            <div className="w-12 h-12 sm:w-14 sm:h-14 bg-primary/10 rounded-xl flex items-center justify-center">
              <Brain className="h-6 w-6 sm:h-8 sm:w-8 text-primary" />
            </div>
          </div>
          <div className="space-y-1.5">
            <CardTitle className="text-2xl sm:text-3xl lg:text-4xl font-bold text-center lg:text-left text-foreground">
              Welcome Back
            </CardTitle>
            <CardDescription className="text-center lg:text-left text-muted-foreground text-sm sm:text-base">
              Sign in to access the intelligence engine (demo auth — see README)
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 p-4 sm:p-6 pt-0">
          {/* OAuth Buttons */}
          <div className="space-y-2.5">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5">
              <Button
                onClick={handleGoogleSignIn}
                disabled={signingIn}
                className="w-full bg-white hover:bg-gray-50 text-gray-900 font-medium py-5 text-sm sm:text-base border border-gray-300"
                size="lg"
              >
                {signingIn ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                      <path
                        fill="currentColor"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="currentColor"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="currentColor"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      />
                      <path
                        fill="currentColor"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                    Continue with Google
                  </>
                )}
              </Button>

              <Button
                onClick={handleAppleSignIn}
                disabled={signingIn}
                className="w-full bg-black hover:bg-gray-900 text-white font-medium py-5 text-sm sm:text-base"
                size="lg"
              >
                {signingIn ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                    </svg>
                    Continue with Apple
                  </>
                )}
              </Button>
            </div>

            <Button
              onClick={handleAnonymousSignIn}
              disabled={signingIn}
              className="w-full bg-muted hover:bg-muted/80 text-foreground font-medium py-5 text-sm sm:text-base border border-border"
              size="lg"
              variant="outline"
            >
              {signingIn ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <UserX className="mr-2 h-5 w-5" />
                  Continue as Guest
                </>
              )}
            </Button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Or continue with email
              </span>
            </div>
          </div>

          {/* Email Sign In Form */}
          <form onSubmit={handleEmailSignIn} className="space-y-3.5">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                disabled={signingIn}
                className={errors.email ? 'border-destructive' : ''}
                required
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email}</p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(!showForgotPassword)}
                  className="text-sm text-primary hover:text-primary/90"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  disabled={signingIn}
                  className={errors.password ? 'border-destructive pr-10' : 'pr-10'}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password}</p>
              )}
            </div>

            {showForgotPassword && (
              <div className="p-2.5 bg-muted rounded-lg space-y-2">
                <p className="text-xs sm:text-sm text-muted-foreground">
                  Enter your email address and we&apos;ll send you a link to reset your password.
                </p>
                <Button
                  type="button"
                  onClick={handleForgotPassword}
                  className="w-full"
                  variant="outline"
                  size="sm"
                >
                  Send Reset Email
                </Button>
              </div>
            )}

            <Button
              type="submit"
              disabled={signingIn}
              className="w-full signal-glow font-medium py-5 text-sm sm:text-base"
              size="lg"
            >
              {signingIn ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          <div className="text-center text-xs sm:text-sm text-muted-foreground pt-1">
            Don&apos;t have an account?{' '}
            <Link href="/signup" className="text-primary hover:text-primary/90 font-medium">
              Sign up
            </Link>
          </div>

          <div className="text-center text-[10px] sm:text-xs text-muted-foreground px-2 pt-1">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </div>
        </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
