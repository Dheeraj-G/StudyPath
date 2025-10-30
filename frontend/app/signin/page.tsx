"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { BookOpen, LogIn, Loader2 } from "lucide-react"
import { authService, type AuthUser } from "@/lib/auth-service"

export default function SignInPage() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  useEffect(() => {
    // Check if user is already authenticated
    const currentUser = authService.getCurrentUser()
    if (currentUser) {
      setUser(currentUser)
      router.push('/')
      return
    }

    // Listen for auth state changes
    const unsubscribe = authService.onAuthStateChange((user) => {
      setUser(user)
      if (user) {
        router.push('/')
      }
    })

    return () => unsubscribe()
  }, [router])

  const handleSignIn = async () => {
    try {
      setIsLoading(true)
      await authService.signInWithGoogle()
    } catch (error) {
      console.error('Sign in error:', error)
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-8">
        <div className="text-center space-y-6">
          {/* Logo/Icon */}
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>

          {/* Title */}
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-foreground">Welcome to StudyPath</h1>
            <p className="text-muted-foreground">
              Sign in to start your personalized learning journey
            </p>
          </div>

          {/* Sign In Button */}
          <div className="space-y-4">
            <Button
              onClick={handleSignIn}
              disabled={isLoading}
              className="w-full"
              size="lg"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <LogIn className="h-4 w-4" />
                  Sign in with Google
                </>
              )}
            </Button>

            <p className="text-xs text-muted-foreground">
              By signing in, you agree to our terms of service and privacy policy
            </p>
          </div>

          {/* Features */}
          <div className="space-y-3 pt-4 border-t">
            <h3 className="text-sm font-medium text-foreground">What you can do:</h3>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>• Upload learning materials (audio, video, documents)</li>
              <li>• Get personalized Q&A sessions</li>
              <li>• Track your learning progress</li>
              <li>• Generate custom study roadmaps</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}
