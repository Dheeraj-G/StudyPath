"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Send, BookOpen, Wifi, WifiOff, LogOut, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { authService, type AuthUser } from "@/lib/auth-service"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp?: string
}

interface Question {
  question: string
  options: {
    A: string
    B: string
    C: string
    D: string
  }
  correct_answer: string
  explanation: string
}

interface ChatPanelProps {
  messages: Message[]
  onSendMessage: (message: string) => void
  isProcessing: boolean
  hasFiles: boolean
  isConnected?: boolean
  user: AuthUser
  isQuizActive?: boolean
  currentQuestion?: Question
  onAnswerClick?: (answer: string) => void
  isGeneratingQuestions?: boolean
  isQuestionAnswered?: boolean
}

export function ChatPanel({ 
  messages, 
  onSendMessage, 
  isProcessing, 
  hasFiles, 
  isConnected = false, 
  user,
  isQuizActive = false,
  currentQuestion,
  onAnswerClick,
  isGeneratingQuestions = false,
  isQuestionAnswered = false
}: ChatPanelProps) {
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
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">{user.displayName || user.email}</span>
              <Button variant="outline" size="sm" onClick={handleSignOut}>
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isGeneratingQuestions ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                Generating Questions
              </h2>
              <p className="text-balance text-sm text-muted-foreground">
                Creating personalized questions from your learning materials...
              </p>
            </div>
          </div>
        ) : messages.length === 0 ? (
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
                  <p className="text-sm leading-relaxed whitespace-pre-line">{message.content}</p>
                </Card>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {!isGeneratingQuestions && (
        <div className="border-t border-border bg-card p-4" style={{ minHeight: '30vh', maxHeight: '30vh' }}>
          <div className="mx-auto max-w-4xl h-full flex items-center justify-center">
            <div className="grid grid-cols-2 grid-rows-2 gap-4 w-full h-full">
              {/* Top Left: A */}
              <Button
                onClick={() => isQuizActive && currentQuestion && !isQuestionAnswered && onAnswerClick?.('A')}
                disabled={!isQuizActive || !currentQuestion || isQuestionAnswered}
                className="h-full w-full flex flex-col items-start justify-start p-4 text-left overflow-hidden"
                variant="outline"
              >
                <span className="text-lg font-bold mb-2">A.</span>
                <span className="text-sm leading-relaxed break-words overflow-hidden">{currentQuestion?.options.A || ''}</span>
              </Button>
              {/* Top Right: B */}
              <Button
                onClick={() => isQuizActive && currentQuestion && !isQuestionAnswered && onAnswerClick?.('B')}
                disabled={!isQuizActive || !currentQuestion || isQuestionAnswered}
                className="h-full w-full flex flex-col items-start justify-start p-4 text-left overflow-hidden"
                variant="outline"
              >
                <span className="text-lg font-bold mb-2">B.</span>
                <span className="text-sm leading-relaxed break-words overflow-hidden">{currentQuestion?.options.B || ''}</span>
              </Button>
              {/* Bottom Left: C */}
              <Button
                onClick={() => isQuizActive && currentQuestion && !isQuestionAnswered && onAnswerClick?.('C')}
                disabled={!isQuizActive || !currentQuestion || isQuestionAnswered}
                className="h-full w-full flex flex-col items-start justify-start p-4 text-left overflow-hidden"
                variant="outline"
              >
                <span className="text-lg font-bold mb-2">C.</span>
                <span className="text-sm leading-relaxed break-words overflow-hidden">{currentQuestion?.options.C || ''}</span>
              </Button>
              {/* Bottom Right: D */}
              <Button
                onClick={() => isQuizActive && currentQuestion && !isQuestionAnswered && onAnswerClick?.('D')}
                disabled={!isQuizActive || !currentQuestion || isQuestionAnswered}
                className="h-full w-full flex flex-col items-start justify-start p-4 text-left overflow-hidden"
                variant="outline"
              >
                <span className="text-lg font-bold mb-2">D.</span>
                <span className="text-sm leading-relaxed break-words overflow-hidden">{currentQuestion?.options.D || ''}</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
