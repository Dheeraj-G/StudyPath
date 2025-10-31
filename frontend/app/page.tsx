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
  const [parsingProgress, setParsingProgress] = useState<{[key: string]: {parsed: number, total: number, percentage: number}}>({})
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

    // Load user documents immediately on initial page load
    const loadUserDocuments = async (user: AuthUser) => {
      // Set auth token for file upload service
      const token = authService.getAuthToken()
      if (token) {
        fileUploadService.setAuthToken(token)
      }
      
      // Load previously uploaded files for this user (don't wait for WebSocket)
      try {
        const files = await fileUploadService.getUserFiles()
        setUploadedFiles(files)
      } catch (e) {
        console.error('Failed to load uploaded files:', e)
      }

      // Connect to WebSocket (non-blocking, failures won't prevent document loading)
      try {
        await webSocketService.connect(user.uid)
      } catch (e) {
        console.warn('WebSocket connection failed (this is non-critical):', e)
        // WebSocket failures are not critical for document loading
      }
    }

    // Load documents immediately if user is already authenticated
    loadUserDocuments(currentUser)

    // Set up auth state listener for subsequent auth changes
    const unsubscribe = authService.onAuthStateChange((user) => {
      setUser(user)
      if (!user) {
        router.push('/signin')
        return
      }
      
      // Load documents when auth state changes (e.g., user signs in)
      loadUserDocuments(user)
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
      },
      onParsingProgress: (progress: {file_type: string, parsed: number, total: number, percentage: number}) => {
        setParsingProgress(prev => ({
          ...prev,
          [progress.file_type]: {
            parsed: progress.parsed,
            total: progress.total,
            percentage: progress.percentage
          }
        }))
      },
      onProcessingComplete: (message: string) => {
        // Add completion message to chat
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: message,
          timestamp: new Date().toISOString()
        }])
        // Set processing to false
        setIsProcessing(false)
        console.log('✅ Processing completed:', message)
      },
      onProcessingError: (message: string, error?: string) => {
        // Add error message to chat
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: message,
          timestamp: new Date().toISOString()
        }])
        // Set processing to false
        setIsProcessing(false)
        console.error('❌ Processing failed:', message, error)
      }
    })

    return () => {
      unsubscribe()
      webSocketService.disconnect()
    }
  }, [router])

  const handleFilesAdded = (newFiles: File[]) => {
    // Build a set of existing keys (name-size) from local and server files to avoid duplicates
    const existingKeys = new Set<string>()
    for (const f of files) existingKeys.add(`${f.name}-${f.size}`)
    for (const uf of uploadedFiles) existingKeys.add(`${uf.file_name}-${uf.file_size}`)

    const deduped = newFiles.filter(f => !existingKeys.has(`${f.name}-${f.size}`))
    if (deduped.length === 0) return
    setFiles((prev) => [...prev, ...deduped])
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

  const handleStartProcessing = async () => {
    if (uploadedFiles.length === 0) return

    setIsProcessing(true)
    setParsingProgress({}) // Reset parsing progress for new session
    // Ensure WS is connected before sending
    try {
      const u = authService.getCurrentUser()
      if (u && !isConnected) {
        await webSocketService.connectAndWait(u.uid)
        setIsConnected(true)
      }
    } catch (e) {
      console.error('WebSocket connect failed:', e)
    }
    
    // Send file upload notification to WebSocket
    const fileIds = uploadedFiles.map(f => f.file_id)
    webSocketService.sendFileUploadNotification(fileIds)
    
    // Add initial processing message
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: 'Starting to process your uploaded materials. This may take a few moments...',
      timestamp: new Date().toISOString()
    }])

    // Trigger backend learning session to start parsing pipeline
    try {
      const token = authService.getAuthToken()
      if (token) fileUploadService.setAuthToken(token)
      const topic = 'Learning Session'
      const goals = ['Parse uploaded materials']
      const res = await fileUploadService.startLearningSession(topic, goals)
      console.log('Learning session started:', res)
    } catch (e) {
      console.error('Failed to start learning session:', e)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Failed to start learning session. Please try again.',
        timestamp: new Date().toISOString()
      }])
    }
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

      {/* Test Section: Parsing Progress Display */}
      {isProcessing && Object.keys(parsingProgress).length > 0 && (
        <div className="border-b border-border bg-muted/30 px-6 py-3">
          <div className="mx-auto max-w-3xl">
            <h3 className="mb-2 text-sm font-semibold text-foreground">Test: Document Parsing Progress</h3>
            <div className="space-y-2">
              {Object.entries(parsingProgress).map(([fileType, progress]) => (
                <div key={fileType} className="text-xs">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-medium text-card-foreground capitalize">{fileType} Files:</span>
                    <span className="text-muted-foreground">
                      {progress.parsed} / {progress.total} ({progress.percentage}%)
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${progress.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <FileUploadSidebar
          files={files}
          onFilesAdded={handleFilesAdded}
          onFileRemove={handleFileRemove}
          onServerFileRemove={async (fileId: string) => {
            try {
              const token = authService.getAuthToken()
              if (token) fileUploadService.setAuthToken(token)
              await fileUploadService.deleteFile(fileId)
              setUploadedFiles(prev => prev.filter(uf => uf.file_id !== fileId))
            } catch (error) {
              console.error('Error deleting server file:', error)
              setUploadedFiles(prev => prev.filter(uf => uf.file_id !== fileId))
            }
          }}
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