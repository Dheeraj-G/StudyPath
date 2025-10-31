/**
 * Knowledge Tree Service
 * Handles fetching knowledge trees from the API
 */

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

interface KnowledgeTreeNode {
  concept: string
  level: number
  question: Question | null
  children: KnowledgeTreeNode[]
}

interface KnowledgeTree {
  root_concept: string
  tree: KnowledgeTreeNode
}

interface KnowledgeTreeResponse {
  trees: KnowledgeTree[]
  content_length: number
  total_nodes: number
  tree_id?: string
}

class KnowledgeTreeService {
  private baseUrl: string
  private authToken: string | null = null

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.baseUrl = baseUrl
  }

  setAuthToken(token: string) {
    this.authToken = token
  }

  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  async getKnowledgeTrees(): Promise<KnowledgeTreeResponse> {
    const response = await this.makeRequest<any>('/api/knowledge-trees/')
    // Handle different response structures
    if (response.trees) {
      // Already has trees array
      return response
    } else if (response.message) {
      // No trees found message
      return { trees: [], content_length: 0, total_nodes: 0 }
    } else if (Array.isArray(response)) {
      return { trees: response, content_length: 0, total_nodes: 0 }
    } else {
      // If it's a single tree object with nested trees array
      if (response.trees && Array.isArray(response.trees)) {
        return response
      }
      // If it's just a single tree structure, wrap it
      return { trees: [response], content_length: 0, total_nodes: 0 }
    }
  }

  async getKnowledgeTree(treeId: string): Promise<KnowledgeTreeResponse> {
    const response = await this.makeRequest<any>(`/api/knowledge-trees/?tree_id=${treeId}`)
    // Handle response structure
    if (response.trees) {
      return response
    } else if (Array.isArray(response)) {
      return { trees: response, content_length: 0, total_nodes: 0 }
    } else {
      return { trees: [response], content_length: 0, total_nodes: 0 }
    }
  }

  async storeQuizResults(quizResults: any, trees: any[]): Promise<any> {
    const response = await this.makeRequest<any>('/api/knowledge-trees/quiz-results', {
      method: 'POST',
      body: JSON.stringify({
        quizResults,
        trees,
        timestamp: new Date().toISOString()
      })
    })
    return response
  }

  async getLastQuizResults(): Promise<any> {
    const response = await this.makeRequest<any>('/api/knowledge-trees/quiz-results/last')
    return response
  }

  /**
   * Flatten all questions from knowledge trees with their node information
   */
  flattenQuestions(trees: any[]): Array<{
    question: Question
    nodeInfo: {
      rootConcept: string
      concept: string
      level: number
    }
  }> {
    const questions: Array<{
      question: Question
      nodeInfo: {
        rootConcept: string
        concept: string
        level: number
      }
    }> = []

    const traverse = (node: any, rootConcept: string) => {
      // Handle different node structures
      if (!node) return
      
      const nodeQuestion = node.question || null
      const nodeConcept = node.concept || node.conceptName || 'Unknown'
      const nodeLevel = node.level !== undefined ? node.level : 0
      const nodeChildren = node.children || []
      
      if (nodeQuestion && typeof nodeQuestion === 'object') {
        // Validate question structure
        if (nodeQuestion.question && nodeQuestion.options && nodeQuestion.correct_answer) {
          questions.push({
            question: nodeQuestion as Question,
            nodeInfo: {
              rootConcept,
              concept: nodeConcept,
              level: nodeLevel,
            },
          })
        }
      }

      for (const child of nodeChildren) {
        traverse(child, rootConcept)
      }
    }

    for (const tree of trees) {
      if (!tree) continue
      
      // Handle different tree structures
      const rootConcept = tree.root_concept || tree.rootConcept || 'Unknown'
      let treeRoot = tree.tree || tree
      
      // If treeRoot has a trees array, iterate through it
      if (treeRoot.trees && Array.isArray(treeRoot.trees)) {
        for (const subTree of treeRoot.trees) {
          const subRootConcept = subTree.root_concept || subTree.rootConcept || rootConcept
          const subTreeRoot = subTree.tree || subTree
          traverse(subTreeRoot, subRootConcept)
        }
      } else {
        traverse(treeRoot, rootConcept)
      }
    }

    return questions
  }
}

export const knowledgeTreeService = new KnowledgeTreeService()
export type { Question, KnowledgeTreeNode, KnowledgeTree, KnowledgeTreeResponse }

