"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { FileUploadSidebar } from "@/components/file-upload-sidebar"
import { ChatPanel } from "@/components/chat-panel"
import { ProgressBar } from "@/components/progress-bar"
import { RoadmapModal } from "@/components/roadmap-modal"
import { webSocketService, type ChatMessage } from "@/lib/websocket-service"
import { authService, type AuthUser } from "@/lib/auth-service"
import { fileUploadService, type UploadedFile } from "@/lib/file-upload-service"
import { Loader2 } from "lucide-react"

export default function Home() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [files, setFiles] = useState<File[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [showRoadmap, setShowRoadmap] = useState(false)
  const [roadmapData, setRoadmapData] = useState<string[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const router = useRouter()

  // Initialize authentication and WebSocket
  useEffect(() => {
    // Check initial auth state
    const currentUser = authService.getCurrentUser()
    setUser(currentUser)
    setIsLoading(false)

    if (!currentUser) {
      router.push('/signin')
      return
    }

    // Set up auth state listener
    const unsubscribe = authService.onAuthStateChange((user) => {
      setUser(user)
      if (!user) {
        router.push('/signin')
        return
      }
      
      // Set auth token for file upload service
      const token = authService.getAuthToken()
      if (token) {
        fileUploadService.setAuthToken(token)
      }
      
      // Connect to WebSocket
      webSocketService.connect(user.uid)
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
  }, [router])

  const handleFilesAdded = (newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles])
  }

  const handleFileRemove = async (index: number) => {
    const fileToRemove = files[index]
    
    // Check if this file has been uploaded to the server
    const uploadedFile = uploadedFiles.find(
      uf => uf.file_name === fileToRemove.name && uf.file_size === fileToRemove.size
    )
    
    // If file was uploaded, delete it from the server (database and storage)
    if (uploadedFile) {
      try {
        const token = authService.getAuthToken()
        if (token) {
          fileUploadService.setAuthToken(token)
        }
        
        await fileUploadService.deleteFile(uploadedFile.file_id)
        
        // Remove from uploadedFiles state
        setUploadedFiles(prev => prev.filter(uf => uf.file_id !== uploadedFile.file_id))
      } catch (error) {
        console.error('Error deleting file from server:', error)
        // Still remove from local state even if server delete fails
        setUploadedFiles(prev => prev.filter(uf => uf.file_id !== uploadedFile.file_id))
      }
    }
    
    // Remove from local files array
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

  // Show loading screen while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // Don't render anything if user is not authenticated (will redirect)
  if (!user) {
    return null
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