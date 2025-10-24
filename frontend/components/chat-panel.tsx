"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Send, BookOpen, Wifi, WifiOff, LogIn, LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { authService, type AuthUser } from "@/lib/auth-service"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp?: string
}

interface ChatPanelProps {
  messages: Message[]
  onSendMessage: (message: string) => void
  isProcessing: boolean
  hasFiles: boolean
  isConnected?: boolean
  user?: AuthUser | null
}

export function ChatPanel({ messages, onSendMessage, isProcessing, hasFiles, isConnected = false, user }: ChatPanelProps) {
  const [input, setInput] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && isProcessing && isConnected) {
      onSendMessage(input.trim())
      setInput("")
    }
  }

  const handleSignIn = async () => {
    try {
      await authService.signInWithGoogle()
    } catch (error) {
      console.error('Sign in error:', error)
    }
  }

  const handleSignOut = async () => {
    try {
      await authService.signOut()
    } catch (error) {
      console.error('Sign out error:', error)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="border-b border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold text-card-foreground">Learning Session</h1>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Connection Status */}
            <div className="flex items-center gap-1">
              {isConnected ? (
                <Wifi className="h-4 w-4 text-green-500" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-500" />
              )}
              <span className="text-xs text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            {/* Authentication */}
            {user ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">{user.displayName || user.email}</span>
                <Button variant="outline" size="sm" onClick={handleSignOut}>
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button variant="outline" size="sm" onClick={handleSignIn}>
                <LogIn className="h-4 w-4 mr-1" />
                Sign In
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <BookOpen className="h-8 w-8 text-primary" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                {hasFiles ? "Ready to Begin" : "Upload Your Materials"}
              </h2>
              <p className="text-balance text-sm text-muted-foreground">
                {hasFiles
                  ? 'Click "Start Learning Session" to begin your personalized Q&A experience'
                  : "Add audio, visual, or text files to get started with your learning journey"}
              </p>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((message, index) => (
              <div key={index} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                <Card
                  className={cn(
                    "max-w-[80%] p-4",
                    message.role === "user" ? "bg-primary text-primary-foreground" : "bg-card text-card-foreground",
                  )}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                </Card>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="border-t border-border bg-card p-4">
        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                !user ? "Sign in to start chatting..." :
                !isConnected ? "Connecting..." :
                !isProcessing ? "Start a learning session to begin" :
                "Type your answer..."
              }
              disabled={!user || !isConnected || !isProcessing}
              className="flex-1"
            />
            <Button 
              type="submit" 
              disabled={!input.trim() || !user || !isConnected || !isProcessing}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
