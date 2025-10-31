"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ChevronRight, ChevronLeft } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import Tree from "react-d3-tree"

interface KnowledgeTreeNode {
  concept: string
  level: number
  question: any | null
  children: KnowledgeTreeNode[]
}

interface KnowledgeTree {
  root_concept: string
  tree: KnowledgeTreeNode
}

interface QuizResult {
  nodeInfo: {
    rootConcept: string
    concept: string
    level: number
  }
  correct: boolean
  userAnswer: string
  correctAnswer: string
}

interface QuizResultsModalProps {
  isOpen: boolean
  trees: KnowledgeTree[]
  quizResults: QuizResult[]
  onClose: () => void
}

// Helper to create a map of concept -> result
function createResultMap(results: QuizResult[]): Map<string, boolean> {
  const map = new Map<string, boolean>()
  results.forEach(result => {
    const key = `${result.nodeInfo.rootConcept}:${result.nodeInfo.concept}:${result.nodeInfo.level}`
    map.set(key, result.correct)
  })
  return map
}

// Helper to check if a node has a result
function getNodeResult(node: KnowledgeTreeNode, rootConcept: string, resultMap: Map<string, boolean>): boolean | null {
  const key = `${rootConcept}:${node.concept}:${node.level}`
  return resultMap.get(key) ?? null
}

// Helper to get all incorrect nodes in top-down order with descriptions
function getIncorrectNodesInOrder(trees: KnowledgeTree[], resultMap: Map<string, boolean>): Array<{ concept: string; level: number; rootConcept: string; description: string }> {
  const incorrectNodes: Array<{ concept: string; level: number; rootConcept: string; description: string }> = []
  
  const traverse = (node: KnowledgeTreeNode, rootConcept: string) => {
    const result = getNodeResult(node, rootConcept, resultMap)
    
    // If this node has a result and it's incorrect, add it
    if (result === false) {
      // Extract description from question explanation or generate one
      let description = `Study the fundamentals and key concepts of ${node.concept}.`
      if (node.question && typeof node.question === 'object' && node.question.explanation) {
        // Use the explanation from the question, but keep it to one sentence
        const explanation = node.question.explanation as string
        // Take first sentence or truncate to reasonable length
        const firstSentence = explanation.split('.')[0].trim()
        if (firstSentence && firstSentence.length > 10 && firstSentence.length < 200) {
          description = firstSentence.endsWith('.') ? firstSentence : firstSentence + '.'
        } else if (explanation.length > 10 && explanation.length < 200) {
          // If no period found, truncate at 150 chars and add ellipsis
          description = explanation.length > 150 ? explanation.substring(0, 150) + '...' : explanation
        }
      }
      
      incorrectNodes.push({
        concept: node.concept,
        level: node.level,
        rootConcept,
        description
      })
    }
    
    // Recursively process children in order (top-down)
    node.children.forEach(child => {
      traverse(child, rootConcept)
    })
  }
  
  trees.forEach(tree => {
    traverse(tree.tree, tree.root_concept)
  })
  
  // Reverse the order so it goes from bottom-up (deepest to shallowest)
  return incorrectNodes.reverse()
}

// Helper to find index of a node in recommended order
function findRecommendedIndex(
  node: KnowledgeTreeNode,
  rootConcept: string,
  incorrectNodes: Array<{ concept: string; level: number; rootConcept: string; description: string }>
): number | undefined {
  const index = incorrectNodes.findIndex(
    n => n.concept === node.concept && 
         n.level === node.level && 
         n.rootConcept === rootConcept
  )
  return index >= 0 ? index : undefined
}

// Component to render a single node
function TreeNode({ 
  node, 
  rootConcept, 
  resultMap, 
  depth = 0,
  showRecommendedOrder = false,
  incorrectNodes = []
}: { 
  node: KnowledgeTreeNode
  rootConcept: string
  resultMap: Map<string, boolean>
  depth?: number
  showRecommendedOrder?: boolean
  incorrectNodes?: Array<{ concept: string; level: number; rootConcept: string; description: string }>
}) {
  const result = getNodeResult(node, rootConcept, resultMap)
  const recommendedIndex = showRecommendedOrder 
    ? findRecommendedIndex(node, rootConcept, incorrectNodes)
    : undefined
  
  // Determine node color - pastel colors
  let nodeColor = 'bg-gray-100 text-gray-700' // Default (no question/result)
  if (result === true) {
    nodeColor = 'bg-green-200 text-green-800' // Correct - pastel green
  } else if (result === false) {
    nodeColor = 'bg-red-200 text-red-800' // Incorrect - pastel red
  }
  
  // If showing recommended order and this is in the list, highlight it
  if (showRecommendedOrder && recommendedIndex !== undefined) {
    nodeColor = 'bg-red-200 text-red-800' // Recommended study - pastel red
  }
  
  return (
    <div className="flex flex-col items-center">
      <div className={`rounded-md px-2 py-1.5 mb-2 min-w-[100px] max-w-[120px] text-center text-xs font-medium ${nodeColor}`}>
        <div className="truncate">{node.concept}</div>
        {showRecommendedOrder && recommendedIndex !== undefined && (
          <span className="ml-1 text-[10px] font-bold">#{recommendedIndex + 1}</span>
        )}
      </div>
      {node.children.length > 0 && (
        <div className="flex items-center gap-2 mt-1 relative">
          {/* Vertical line connecting parent to children */}
          <div className="absolute left-1/2 top-[-8px] w-0.5 h-2 bg-gray-400 -translate-x-1/2"></div>
          {/* Horizontal line above children */}
          {node.children.length > 1 && (
            <div className="absolute left-1/2 top-[-8px] w-full h-0.5 bg-gray-400 -translate-x-1/2" style={{ width: `${(node.children.length - 1) * 100}%` }}></div>
          )}
          {node.children.map((child, idx) => (
            <div key={`${child.concept}-${child.level}-${idx}`} className="relative flex flex-col items-center">
              {/* Vertical line from horizontal line to node */}
              <div className="absolute left-1/2 top-[-8px] w-0.5 h-2 bg-gray-400 -translate-x-1/2"></div>
              <TreeNode
                node={child}
                rootConcept={rootConcept}
                resultMap={resultMap}
                depth={depth + 1}
                showRecommendedOrder={showRecommendedOrder}
                incorrectNodes={incorrectNodes}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Convert knowledge tree node to d3 tree format
function convertToD3Node(node: KnowledgeTreeNode, rootConcept: string, resultMap: Map<string, boolean>, incorrectNodes: Array<{ concept: string; level: number; rootConcept: string; description: string }>): any {
  const result = getNodeResult(node, rootConcept, resultMap)
  const recommendedIndex = findRecommendedIndex(node, rootConcept, incorrectNodes)
  
  // Determine node color
  let nodeColor = '#e5e7eb' // Default gray
  let textColor = '#374151' // Default text color
  if (result === true) {
    nodeColor = '#bbf7d0' // Pastel green
    textColor = '#166534'
  } else if (result === false) {
    nodeColor = '#fecaca' // Pastel red
    textColor = '#991b1b'
  }
  
  if (recommendedIndex !== undefined) {
    nodeColor = '#fecaca' // Pastel red
    textColor = '#991b1b'
  }
  
  const d3Node: any = {
    name: node.concept,
    attributes: {
      level: node.level,
      result: result === null ? 'none' : result ? 'correct' : 'incorrect',
      recommendedIndex: recommendedIndex !== undefined ? recommendedIndex + 1 : null
    },
    nodeSvgShape: {
      shape: 'rect',
      shapeProps: {
        width: 120,
        height: 40,
        x: -60,
        y: -20,
        fill: nodeColor,
        stroke: '#9ca3af',
        strokeWidth: 1,
        rx: 4,
      }
    },
    style: {
      fill: textColor,
    }
  }
  
  if (node.children.length > 0) {
    d3Node.children = node.children.map(child => 
      convertToD3Node(child, rootConcept, resultMap, incorrectNodes)
    )
  }
  
  return d3Node
}

// Custom node component for d3 tree
function renderCustomNode({ nodeDatum, toggleNode }: any) {
  const isCorrect = nodeDatum.attributes?.result === 'correct'
  const isIncorrect = nodeDatum.attributes?.result === 'incorrect'
  const isRecommended = nodeDatum.attributes?.recommendedIndex !== null
  
  let bgColor = '#e5e7eb'
  let textColor = '#374151'
  
  if (isCorrect) {
    bgColor = '#bbf7d0'
    textColor = '#166534'
  } else if (isIncorrect) {
    bgColor = '#fecaca'
    textColor = '#991b1b'
  }
  
  if (isRecommended) {
    bgColor = '#fecaca'
    textColor = '#991b1b'
  }
  
  return (
    <g>
      <rect
        width={120}
        height={40}
        x={-60}
        y={-20}
        fill={bgColor}
        stroke="#9ca3af"
        strokeWidth={1}
        rx={4}
        onClick={toggleNode}
        style={{ cursor: 'pointer' }}
      />
      <text
        fill={textColor}
        strokeWidth={1}
        x={0}
        y={5}
        textAnchor="middle"
        fontSize={12}
        fontWeight="medium"
        style={{ pointerEvents: 'none' }}
      >
        {nodeDatum.name.length > 15 ? nodeDatum.name.substring(0, 12) + '...' : nodeDatum.name}
      </text>
      {isRecommended && (
        <text
          fill={textColor}
          strokeWidth={1}
          x={0}
          y={-25}
          textAnchor="middle"
          fontSize={10}
          fontWeight="bold"
          style={{ pointerEvents: 'none' }}
        >
          #{nodeDatum.attributes.recommendedIndex}
        </text>
      )}
    </g>
  )
}

// Component to render a tree
function TreeView({ 
  tree, 
  resultMap, 
  showRecommendedOrder = false, 
  incorrectNodes = [],
  containerWidth = 800 
}: { 
  tree: KnowledgeTree
  resultMap: Map<string, boolean>
  showRecommendedOrder?: boolean
  incorrectNodes?: Array<{ concept: string; level: number; rootConcept: string; description: string }>
  containerWidth?: number
}) {
  const d3Data = convertToD3Node(tree.tree, tree.root_concept, resultMap, incorrectNodes)
  
  return (
    <div className="mb-6 w-full">
      <h3 className="text-lg font-semibold mb-4 text-center">{tree.root_concept}</h3>
      <div className="flex justify-center w-full bg-white rounded-lg border" style={{ height: '500px', overflow: 'auto', width: '80%', margin: '0 auto' }}>
        <Tree
          data={d3Data}
          orientation="vertical"
          translate={{ x: (containerWidth * 0.8) / 2, y: 50 }}
          nodeSize={{ x: 200, y: 120 }}
          renderCustomNodeElement={renderCustomNode}
          pathClassFunc={() => 'tree-link'}
          styles={{
            links: {
              stroke: '#9ca3af',
              strokeWidth: 2,
              fill: 'none',
            },
          }}
          zoomable={true}
          draggable={true}
          scaleExtent={{ min: 0.3, max: 1.5 }}
        />
      </div>
    </div>
  )
}

export function QuizResultsModal({ isOpen, trees, quizResults, onClose }: QuizResultsModalProps) {
  const [currentView, setCurrentView] = useState<'results' | 'recommended'>('results')
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const treeContainerRef = useRef<HTMLDivElement>(null)
  const resultMap = createResultMap(quizResults)
  const incorrectNodes = getIncorrectNodesInOrder(trees, resultMap)
  
  // Update dimensions on mount and window resize
  useEffect(() => {
    const updateDimensions = () => {
      if (treeContainerRef.current) {
        // Calculate 80% of the modal width (modal is 80vw, so tree should be 80% of that = 64vw)
        const modalWidth = window.innerWidth * 0.8
        const treeWidth = modalWidth * 0.8
        setDimensions({
          width: treeWidth,
          height: 500
        })
      }
    }
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])
  
  const handleNext = () => {
    setCurrentView('recommended')
  }
  
  const handlePrevious = () => {
    setCurrentView('results')
  }
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="!w-[80vw] !h-[80vh] !max-w-[80vw] sm:!max-w-[80vw] !max-h-[80vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4">
          <DialogTitle>
            {currentView === 'results' ? 'Quiz Results' : 'Recommended Study Order'}
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden relative px-6 pb-6">
          {/* Results View */}
          <div 
            className={`absolute inset-0 transition-transform duration-300 ease-in-out ${
              currentView === 'results' ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0 pointer-events-none'
            }`}
            style={{ width: '100%', height: '100%' }}
          >
            <div className="h-full overflow-y-auto px-8 py-4">
              <div className="mb-6 flex justify-center gap-6">
                <p className="text-sm text-muted-foreground">
                  <span className="inline-block w-4 h-4 bg-green-200 rounded mr-2"></span>
                  Green = Correct Answer
                </p>
                <p className="text-sm text-muted-foreground">
                  <span className="inline-block w-4 h-4 bg-red-200 rounded mr-2"></span>
                  Red = Incorrect Answer
                </p>
              </div>
              
              <div ref={treeContainerRef} className="flex flex-col items-center gap-4 w-full">
                {trees.map((tree, idx) => (
                  <TreeView 
                    key={`tree-${idx}`} 
                    tree={tree} 
                    resultMap={resultMap}
                    incorrectNodes={incorrectNodes}
                    containerWidth={dimensions.width}
                  />
                ))}
              </div>
            </div>
          </div>
          
          {/* Recommended Study Order View */}
          <div 
            className={`absolute inset-0 transition-transform duration-300 ease-in-out ${
              currentView === 'recommended' ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none'
            }`}
            style={{ width: '100%', height: '100%' }}
          >
            <div className="h-full overflow-y-auto px-8 py-4">
              <div className="mb-6 text-center">
                <p className="text-sm text-muted-foreground">
                  Study these topics in order (top-down from each tree, only incorrectly answered questions):
                </p>
              </div>
              
              <div className="flex flex-col gap-4 max-w-2xl mx-auto">
                {incorrectNodes.map((node, idx) => (
                  <div key={`rec-${idx}`} className="flex items-center gap-4 p-4 border rounded-lg">
                    <div className="flex-shrink-0 w-8 h-8 bg-red-200 text-red-800 rounded-full flex items-center justify-center font-bold">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium">{node.concept}</div>
                      <div className="text-sm text-muted-foreground mt-1">{node.description}</div>
                      <div className="text-xs text-muted-foreground mt-1">{node.rootConcept} • Level {node.level}</div>
                    </div>
                  </div>
                ))}
                
                {incorrectNodes.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>Great job! You answered all questions correctly.</p>
                    <p className="text-sm mt-2">No recommended study order needed.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        
        {/* Navigation */}
        <div className="flex justify-between items-center px-6 pt-4 pb-6 border-t">
          <Button
            variant="outline"
            onClick={currentView === 'results' ? onClose : handlePrevious}
          >
            {currentView === 'results' ? 'Close' : (
              <>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Back to Results
              </>
            )}
          </Button>
          
          {currentView === 'results' && (
            <Button onClick={handleNext}>
              Recommended Study Order
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          )}
          
          {currentView === 'recommended' && (
            <Button onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

