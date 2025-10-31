"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { FileUploadSidebar } from "@/components/file-upload-sidebar"
import { ChatPanel } from "@/components/chat-panel"
import { ProgressBar } from "@/components/progress-bar"
import { RoadmapModal } from "@/components/roadmap-modal"
import { QuizReadyModal } from "@/components/quiz-ready-modal"
import { QuizResultsModal } from "@/components/quiz-results-modal"
import { NotificationContainer, type Notification } from "@/components/notification"
import { webSocketService, type ChatMessage } from "@/lib/websocket-service"
import { authService, type AuthUser } from "@/lib/auth-service"
import { fileUploadService, type UploadedFile } from "@/lib/file-upload-service"
import { knowledgeTreeService, type Question } from "@/lib/knowledge-tree-service"
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
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [showQuizReadyModal, setShowQuizReadyModal] = useState(false)
  const [isQuizActive, setIsQuizActive] = useState(false)
  const [quizQuestions, setQuizQuestions] = useState<Array<{
    question: Question
    nodeInfo: {
      rootConcept: string
      concept: string
      level: number
    }
  }>>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [quizResults, setQuizResults] = useState<Array<{
    nodeInfo: {
      rootConcept: string
      concept: string
      level: number
    }
    correct: boolean
    userAnswer: string
    correctAnswer: string
  }>>([])
  const [isGeneratingQuestions, setIsGeneratingQuestions] = useState(false)
  const [answeredQuestionIndex, setAnsweredQuestionIndex] = useState<number | null>(null)
  const [knowledgeTrees, setKnowledgeTrees] = useState<any[]>([])
  const [showQuizResultsModal, setShowQuizResultsModal] = useState(false)
  const [hasLastQuizResults, setHasLastQuizResults] = useState(false)
  const router = useRouter()

  // Helper function to add notifications
  const addNotification = (message: string, type: Notification["type"] = "info") => {
    const id = `${Date.now()}-${Math.random()}`
    setNotifications((prev) => [...prev, { id, message, type }])
  }

  // Check if last quiz results exist when user is authenticated
  useEffect(() => {
    const checkLastQuizResults = async () => {
      if (!user) return
      
      try {
        const token = authService.getAuthToken()
        if (!token) return
        
        knowledgeTreeService.setAuthToken(token)
        const lastResults = await knowledgeTreeService.getLastQuizResults()
        
        if (lastResults && lastResults.message !== "No quiz results found") {
          setHasLastQuizResults(true)
        } else {
          setHasLastQuizResults(false)
        }
      } catch (error) {
        console.error('Error checking last quiz results:', error)
        setHasLastQuizResults(false)
      }
    }
    
    if (user) {
      checkLastQuizResults()
    }
  }, [user])

  const dismissNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

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
        addNotification(`Error: ${error}`, "error")
      },
      onAgentResponse: (agentType: string, response: any) => {
        console.log(`Agent response from ${agentType}:`, response)
        addNotification(`${agentType}: ${response.message || 'Processing...'}`, "info")
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
      onProcessingComplete: async (message: string, data?: any) => {
        console.log('✅ Processing completed:', message, data)
        
        // Check if this is a knowledge tree completion message
        const isKnowledgeTreeMessage = message && (
          message.toLowerCase().includes('knowledge tree') || 
          message.toLowerCase().includes('knowledge trees') ||
          message.includes('🌳') ||
          (data && (data.tree_id || data.status === 'completed'))
        )
        
        // Set processing to false if it's not a knowledge tree message
        // (knowledge tree messages should keep processing state until trees are fetched)
        if (!isKnowledgeTreeMessage) {
          setIsProcessing(false)
          addNotification(message, "success")
        } else {
          // This is a knowledge tree completion - fetch and display trees
          console.log('🌳 Knowledge tree generation completed, fetching trees...')
          setIsGeneratingQuestions(true)
          
          try {
            const token = authService.getAuthToken()
            if (!token) {
              console.error('No auth token available')
              setIsGeneratingQuestions(false)
              setIsProcessing(false)
              return
            }
            
            knowledgeTreeService.setAuthToken(token)
            
            // Retry logic to fetch trees (they might take a moment to be stored)
            const fetchTreesWithRetry = async (attempt: number = 0, maxAttempts: number = 5): Promise<void> => {
              try {
                console.log(`📦 Attempting to fetch knowledge trees (attempt ${attempt + 1}/${maxAttempts})...`)
                const trees = await knowledgeTreeService.getKnowledgeTrees()
                console.log('📦 Fetched knowledge trees:', trees)
                
                // Handle different response structures
                let treesArray: any[] = []
                if (trees && trees.trees && Array.isArray(trees.trees)) {
                  treesArray = trees.trees
                } else if (Array.isArray(trees)) {
                  treesArray = trees
                } else if (trees && typeof trees === 'object' && trees !== null) {
                  // Check if it's a single tree or wrapper object
                  const treesAny = trees as any
                  if (treesAny.root_concept || treesAny.tree) {
                    treesArray = [treesAny]
                  } else {
                    // Try to extract trees from the object
                    Object.values(treesAny).forEach((value: any) => {
                      if (Array.isArray(value)) {
                        treesArray.push(...value)
                      } else if (value && typeof value === 'object' && (value.root_concept || value.tree)) {
                        treesArray.push(value)
                      }
                    })
                  }
                }
                
                if (treesArray.length === 0 && attempt < maxAttempts - 1) {
                  // No trees found yet, retry after a delay
                  console.log(`⏳ No trees found yet, retrying in 2 seconds...`)
                  setTimeout(() => fetchTreesWithRetry(attempt + 1, maxAttempts), 2000)
                  return
                }
                
                console.log(`📝 Found ${treesArray.length} knowledge trees`)
                
                const questions = knowledgeTreeService.flattenQuestions(treesArray as any)
                console.log(`📝 Flattened ${questions.length} questions from ${treesArray.length} trees`)
                
                // Store the full trees for the results modal
                setKnowledgeTrees(treesArray)
                setIsGeneratingQuestions(false)
                setIsProcessing(false)
                
                if (questions.length > 0) {
                  setQuizQuestions(questions)
                  setShowQuizReadyModal(true)
                  addNotification(`Generated ${questions.length} quiz questions!`, "success")
                } else {
                  console.warn('⚠️ No questions found in knowledge trees')
                  addNotification('Knowledge trees generated, but no questions found', "warning")
                  setIsGeneratingQuestions(false)
                  setIsProcessing(false)
                }
                
                // Check for last quiz results after loading knowledge trees
                try {
                  const lastResults = await knowledgeTreeService.getLastQuizResults()
                  if (lastResults && lastResults.message !== "No quiz results found") {
                    setHasLastQuizResults(true)
                  } else {
                    setHasLastQuizResults(false)
                  }
                } catch (error) {
                  console.error('Error checking last quiz results:', error)
                  setHasLastQuizResults(false)
                }
                
              } catch (error) {
                console.error(`Error fetching knowledge trees (attempt ${attempt + 1}):`, error)
                if (attempt < maxAttempts - 1) {
                  // Retry after a delay
                  setTimeout(() => fetchTreesWithRetry(attempt + 1, maxAttempts), 2000)
                } else {
                  console.error('Failed to fetch knowledge trees after all retries')
                  addNotification('Failed to load knowledge trees. Please try again.', "error")
                  setIsGeneratingQuestions(false)
                  setIsProcessing(false)
                }
              }
            }
            
            // Start fetching with retry logic
            setTimeout(() => fetchTreesWithRetry(), 1000) // Wait 1 second before first attempt
            
          } catch (error) {
            console.error('Error setting up knowledge tree fetch:', error)
            addNotification('Failed to fetch knowledge trees', "error")
            setIsGeneratingQuestions(false)
            setIsProcessing(false)
          }
        }
      },
      onProcessingError: (message: string, error?: string) => {
        // Show notification instead of adding to chat
        addNotification(error ? `${message}: ${error}` : message, "error")
        // Set processing to false
        setIsProcessing(false)
        console.error('❌ Processing failed:', message, error)
      },
      onKnowledgeTreeProgress: (message: string, data?: any) => {
        // Set generating questions loading state when knowledge tree generation starts
        console.log('🌳 Knowledge tree generation started:', message)
        setIsGeneratingQuestions(true)
        // Don't show notification - the loading screen handles this
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
    
    // Show notification instead of adding to chat
    addNotification('Starting to process your uploaded materials. This may take a few moments...', "info")

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
      addNotification('Failed to start learning session. Please try again.', "error")
    }
  }

  const handleSendMessage = (message: string) => {
    // Send message via WebSocket
    webSocketService.sendChatMessage(message)
  }

  const handleStartQuiz = () => {
    setShowQuizReadyModal(false)
    setIsQuizActive(true)
    setCurrentQuestionIndex(0)
    setQuizResults([])
    setAnsweredQuestionIndex(null)
    
    // Show first question
    if (quizQuestions.length > 0) {
      const firstQuestion = quizQuestions[0]
      setMessages([{
        role: 'assistant',
        content: firstQuestion.question.question,
        timestamp: new Date().toISOString()
      }])
    }
  }

  const handleAnswerClick = (answer: string) => {
    if (!isQuizActive || currentQuestionIndex >= quizQuestions.length) return
    
    // Prevent answering the same question twice
    if (answeredQuestionIndex === currentQuestionIndex) return

    const currentQ = quizQuestions[currentQuestionIndex]
    const isCorrect = answer === currentQ.question.correct_answer
    const optionText = currentQ.question.options[answer as keyof typeof currentQ.question.options]
    
    // Mark this question as answered immediately
    setAnsweredQuestionIndex(currentQuestionIndex)
    
    // Add user's answer to chat
    setMessages(prev => [...prev, {
      role: 'user',
      content: `${answer}. ${optionText}`,
      timestamp: new Date().toISOString()
    }])
    
    // Add result and explanation
    const resultText = isCorrect ? '✅ Correct!' : `❌ Incorrect. The correct answer is ${currentQ.question.correct_answer}.`
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: `${resultText}\n\n${currentQ.question.explanation}`,
      timestamp: new Date().toISOString()
    }])
    
    // Track result - create the updated results array
    const updatedResults = [...quizResults, {
      nodeInfo: currentQ.nodeInfo,
      correct: isCorrect,
      userAnswer: answer,
      correctAnswer: currentQ.question.correct_answer
    }]
    
    if (currentQuestionIndex < quizQuestions.length - 1) {
      setTimeout(() => {
        const nextIndex = currentQuestionIndex + 1
        setCurrentQuestionIndex(nextIndex)
        setAnsweredQuestionIndex(null) // Reset answered state for next question
        setQuizResults(updatedResults)
        const nextQuestion = quizQuestions[nextIndex]
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: nextQuestion.question.question,
          timestamp: new Date().toISOString()
        }])
      }, 2000) // Wait 2 seconds before showing next question
    } else {
      // Quiz complete - log results to console
      setQuizResults(updatedResults)
      setTimeout(() => {
        console.log('📊 Quiz Results Summary:')
        console.log('='.repeat(80))
        console.log(`Total Questions: ${quizQuestions.length}`)
        const correctCount = updatedResults.filter(r => r.correct).length
        console.log(`Correct: ${correctCount}`)
        console.log(`Incorrect: ${quizQuestions.length - correctCount}`)
        console.log(`Accuracy: ${((correctCount / quizQuestions.length) * 100).toFixed(1)}%`)
        console.log('='.repeat(80))
        console.log('\n📝 Results by Node:')
        updatedResults.forEach((result, index) => {
          console.log(`\nQuestion ${index + 1}:`)
          console.log(`  Node: ${result.nodeInfo.concept} (Level ${result.nodeInfo.level})`)
          console.log(`  Root Concept: ${result.nodeInfo.rootConcept}`)
          console.log(`  Result: ${result.correct ? '✅ Correct' : '❌ Incorrect'}`)
          console.log(`  Your Answer: ${result.userAnswer}`)
          console.log(`  Correct Answer: ${result.correctAnswer}`)
        })
        console.log('\n📊 Summary by Node:')
        const nodeStats = new Map<string, { correct: number, total: number }>()
        updatedResults.forEach(result => {
          const key = `${result.nodeInfo.rootConcept} > ${result.nodeInfo.concept}`
          if (!nodeStats.has(key)) {
            nodeStats.set(key, { correct: 0, total: 0 })
          }
          const stats = nodeStats.get(key)!
          stats.total++
          if (result.correct) stats.correct++
        })
        nodeStats.forEach((stats, key) => {
          console.log(`  ${key}: ${stats.correct}/${stats.total} (${((stats.correct / stats.total) * 100).toFixed(1)}%)`)
        })
        console.log('='.repeat(80))
        
        setIsQuizActive(false)
        addNotification(`Quiz completed! You got ${correctCount} out of ${quizQuestions.length} questions correct.`, "success")
        
        // Store quiz results
        const storeResults = async () => {
          try {
            const token = authService.getAuthToken()
            if (token) {
              knowledgeTreeService.setAuthToken(token)
              await knowledgeTreeService.storeQuizResults(updatedResults, knowledgeTrees)
              console.log('✅ Quiz results stored successfully')
              setHasLastQuizResults(true)
            }
          } catch (error) {
            console.error('Error storing quiz results:', error)
            // Don't block the UI if storage fails
          }
        }
        storeResults()
        
        // Show results modal after a short delay
        setTimeout(() => {
          setShowQuizResultsModal(true)
        }, 500)
      }, 2000)
    }
  }

  const handleShowLastQuizResults = async () => {
    try {
      const token = authService.getAuthToken()
      if (!token) return
      
      knowledgeTreeService.setAuthToken(token)
      const lastResults = await knowledgeTreeService.getLastQuizResults()
      
      if (lastResults && lastResults.message === "No quiz results found") {
        addNotification('No previous quiz results found.', "info")
        return
      }
      
      if (lastResults && lastResults.quizResults && lastResults.trees) {
        setQuizResults(lastResults.quizResults)
        setKnowledgeTrees(lastResults.trees)
        setShowQuizResultsModal(true)
        addNotification('Loaded previous quiz results', "success")
      }
    } catch (error) {
      console.error('Error loading last quiz results:', error)
      addNotification('Failed to load previous quiz results', "error")
    }
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
      <NotificationContainer notifications={notifications} onDismiss={dismissNotification} />
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
          isQuizActive={isQuizActive}
          currentQuestion={quizQuestions[currentQuestionIndex]?.question}
          onAnswerClick={handleAnswerClick}
          isGeneratingQuestions={isGeneratingQuestions}
          isQuestionAnswered={answeredQuestionIndex === currentQuestionIndex}
          onShowLastQuizResults={handleShowLastQuizResults}
          hasLastQuizResults={hasLastQuizResults}
        />
      </div>

      <RoadmapModal isOpen={showRoadmap} onClose={() => setShowRoadmap(false)} topics={roadmapData} />
      <QuizReadyModal 
        isOpen={showQuizReadyModal} 
        totalQuestions={quizQuestions.length}
        onStart={handleStartQuiz}
      />
      <QuizResultsModal
        isOpen={showQuizResultsModal}
        trees={knowledgeTrees}
        quizResults={quizResults}
        onClose={() => setShowQuizResultsModal(false)}
      />
    </div>
  )
}