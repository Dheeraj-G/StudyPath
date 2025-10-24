"use client"

import { useState, useEffect } from "react"
import { FileUploadSidebar } from "@/components/file-upload-sidebar"
import { ChatPanel } from "@/components/chat-panel"
import { ProgressBar } from "@/components/progress-bar"
import { RoadmapModal } from "@/components/roadmap-modal"
import { webSocketService, type ChatMessage } from "@/lib/websocket-service"
import { authService, type AuthUser } from "@/lib/auth-service"
import { fileUploadService, type UploadedFile } from "@/lib/file-upload-service"

export default function Home() {
  const [files, setFiles] = useState<File[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [showRoadmap, setShowRoadmap] = useState(false)
  const [roadmapData, setRoadmapData] = useState<string[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  // Initialize authentication and WebSocket
  useEffect(() => {
    // Set up auth state listener
    const unsubscribe = authService.onAuthStateChange((user) => {
      setUser(user)
      
      if (user) {
        // Set auth token for file upload service
        const token = authService.getAuthToken()
        if (token) {
          fileUploadService.setAuthToken(token)
        }
        
        // Connect to WebSocket
        webSocketService.connect(user.uid)
      } else {
        // Disconnect WebSocket
        webSocketService.disconnect()
        setIsConnected(false)
      }
    })

    // Set up WebSocket callbacks
    webSocketService.setCallbacks({
      onConnect: () => {
        setIsConnected(true)
        console.log('WebSocket connected')
      },
      onDisconnect: () => {
        setIsConnected(false)
        console.log('WebSocket disconnected')
      },
      onMessage: (message: ChatMessage) => {
        setMessages(prev => [...prev, message])
      },
      onError: (error: string) => {
        console.error('WebSocket error:', error)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${error}`,
          timestamp: new Date().toISOString()
        }])
      },
      onAgentResponse: (agentType: string, response: any) => {
        console.log(`Agent response from ${agentType}:`, response)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `[${agentType}] ${response.message || 'Processing...'}`,
          timestamp: new Date().toISOString()
        }])
      }
    })

    return () => {
      unsubscribe()
      webSocketService.disconnect()
    }
  }, [])

  const handleFilesAdded = (newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles])
  }

  const handleFileRemove = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleStartProcessing = () => {
    if (uploadedFiles.length === 0) return

    setIsProcessing(true)
    
    // Send file upload notification to WebSocket
    const fileIds = uploadedFiles.map(f => f.file_id)
    webSocketService.sendFileUploadNotification(fileIds)
    
    // Add initial processing message
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: 'Starting to process your uploaded materials. This may take a few moments...',
      timestamp: new Date().toISOString()
    }])
  }

  const handleSendMessage = (message: string) => {
    // Send message via WebSocket
    webSocketService.sendChatMessage(message)
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      {isProcessing && totalQuestions > 0 && <ProgressBar current={currentQuestion} total={totalQuestions} />}

      <div className="flex flex-1 overflow-hidden">
        <FileUploadSidebar
          files={files}
          onFilesAdded={handleFilesAdded}
          onFileRemove={handleFileRemove}
          onStartProcessing={handleStartProcessing}
          isProcessing={isProcessing}
          uploadedFiles={uploadedFiles}
          onUploadedFilesChange={setUploadedFiles}
        />

        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          isProcessing={isProcessing}
          hasFiles={uploadedFiles.length > 0}
          isConnected={isConnected}
          user={user}
        />
      </div>

      <RoadmapModal isOpen={showRoadmap} onClose={() => setShowRoadmap(false)} topics={roadmapData} />
    </div>
  )
}
