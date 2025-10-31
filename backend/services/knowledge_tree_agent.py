"""
Knowledge Tree Agent
Creates hierarchical knowledge trees from parsed content and generates questions
"""

from typing import Dict, List, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
import json
import re

from config.settings import get_settings


class KnowledgeTreeNode:
    """Represents a node in the knowledge tree"""
    def __init__(self, concept: str, level: int = 0):
        self.concept = concept
        self.level = level
        self.children: List['KnowledgeTreeNode'] = []
        self.question: Optional[Dict[str, Any]] = None
        self.parent: Optional['KnowledgeTreeNode'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary"""
        return {
            "concept": self.concept,
            "level": self.level,
            "question": self.question,
            "children": [child.to_dict() for child in self.children]
        }


class KnowledgeTreeAgent:
    """Agent that creates knowledge trees and generates questions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGroq(
            api_key=self.settings.GROQ_API_KEY,
            model=self.settings.GROQ_KNOWLEDGE_TREE_MODEL,  # Use llama instant for knowledge tree
            temperature=0.3,  # Lower temperature for more consistent structure
        )
        self.max_levels = 5
        
        # Prompt for creating knowledge trees
        self.tree_prompt = ChatPromptTemplate.from_template(
            """You are an expert educator creating a hierarchical knowledge tree from learning materials.

Given the following parsed content from a learning session, create a knowledge tree structure.
- Start with broad, high-level concepts
- Split each concept into more specific subconcepts
- Maximum depth: {max_levels} levels
- Each node should represent a distinct learning topic or concept
- You may create multiple root-level trees if the content covers different domains

Parsed Content:
{content}

Instructions:
1. Identify the main broad concepts (level 0)
2. For each concept, create logical subdivisions (max {max_levels} levels deep)
3. Return a JSON array of trees, where each tree has this structure:
   {{
     "root_concept": "Main topic name",
     "tree": {{
       "concept": "Concept name",
       "level": 0,
       "children": [
         {{
           "concept": "Subconcept name",
           "level": 1,
           "children": [
             {{
               "concept": "Sub-subconcept name",
               "level": 2,
               "children": []
             }}
           ]
         }}
       ]
     }}
   }}

Important:
- Keep concept names concise and clear (10-30 characters)
- Ensure hierarchical relationships are logical
- Maximum depth is {max_levels} levels
- Include "level" field in each node
- Include "children" array even if empty
- You may create 1-5 root trees depending on content diversity
- Return ONLY valid JSON array, no markdown, no code blocks, no additional text

Example structure:
[
  {{
    "root_concept": "Mathematics",
    "tree": {{
      "concept": "Algebra",
      "level": 0,
      "children": [
        {{
          "concept": "Linear Equations",
          "level": 1,
          "children": []
        }}
      ]
    }}
  }}
]

Return the JSON array now:"""
        )
        
        # Prompt for generating multiple choice questions
        self.question_prompt = ChatPromptTemplate.from_template(
            """You are an expert educator creating multiple choice questions for assessment.

Given the following concept and its context from the learning materials, create a high-quality multiple choice question.

Concept: {concept}
Context: {context}
Level: {level}

Instructions:
1. Create a clear, unambiguous multiple choice question that tests understanding of this concept
2. Provide 4 answer options (A, B, C, D)
3. Exactly one answer should be correct
4. The incorrect answers (distractors) should be plausible but clearly wrong
5. Make questions appropriate for the concept level (level {level})
6. Return ONLY valid JSON in this exact format:
   {{
     "question": "The question text here?",
     "options": {{
       "A": "First option",
       "B": "Second option",
       "C": "Third option",
       "D": "Fourth option"
     }},
     "correct_answer": "A",
     "explanation": "Brief explanation of why the correct answer is correct"
   }}

Return the JSON structure now:"""
        )
    
    def _extract_content_from_parsed_data(self, parsed_data: Dict[str, Any]) -> str:
        """Extract and combine text content from parsed data"""
        content_parts = []
        
        print(f"🔍 Extracting content from parsed data...")
        print(f"🔍 Parsed data keys: {list(parsed_data.keys())}")
        
        # Extract from PDF results
        pdf_data = parsed_data.get("pdf", {})
        print(f"🔍 PDF data: {bool(pdf_data)}, type: {type(pdf_data)}")
        if pdf_data:
            pdf_results = pdf_data.get("results", [])
            print(f"🔍 PDF results count: {len(pdf_results)}")
            for idx, result in enumerate(pdf_results):
                llm_outputs = result.get("llm_outputs", [])
                print(f"🔍 PDF result {idx} - llm_outputs count: {len(llm_outputs)}")
                for output in llm_outputs:
                    # Try to parse JSON from LLM output
                    if isinstance(output, str):
                        # Try to extract JSON from the string
                        try:
                            # Look for JSON in the output
                            json_match = re.search(r'\{.*\}', output, re.DOTALL)
                            if json_match:
                                parsed = json.loads(json_match.group())
                                summary = parsed.get("summary", "")
                                topics = parsed.get("topics", [])
                                key_points = parsed.get("key_points", [])
                                if summary:
                                    content_parts.append(summary)
                                if topics:
                                    content_parts.append("Topics: " + ", ".join(topics))
                                if key_points:
                                    content_parts.append("\n".join(key_points))
                        except Exception as e:
                            # If parsing fails, use the raw output
                            print(f"⚠️ Failed to parse JSON from output, using raw: {str(e)[:100]}")
                            content_parts.append(output)
        
        # Extract from image results
        image_data = parsed_data.get("image", {})
        print(f"🔍 Image data: {bool(image_data)}, type: {type(image_data)}")
        if image_data:
            image_results = image_data.get("results", [])
            print(f"🔍 Image results count: {len(image_results)}")
            for idx, result in enumerate(image_results):
                llm_output = result.get("llm_output", "")
                if llm_output:
                    print(f"🔍 Image result {idx} - found llm_output")
                    content_parts.append(llm_output)
        
        # Extract from audio results
        audio_data = parsed_data.get("audio", {})
        print(f"🔍 Audio data: {bool(audio_data)}, type: {type(audio_data)}")
        if audio_data:
            audio_results = audio_data.get("results", [])
            print(f"🔍 Audio results count: {len(audio_results)}")
            for idx, result in enumerate(audio_results):
                transcription = result.get("transcription", "")
                if transcription:
                    print(f"🔍 Audio result {idx} - found transcription")
                    content_parts.append(transcription)
        
        extracted_content = "\n\n".join(content_parts)
        print(f"🔍 Extracted content length: {len(extracted_content)} characters")
        if len(extracted_content) > 0:
            print(f"🔍 First 200 chars: {extracted_content[:200]}")
        else:
            print("⚠️ WARNING: No content extracted from parsed data!")
        
        return extracted_content
    
    async def create_knowledge_trees(self, parsed_content: str) -> List[Dict[str, Any]]:
        """Create knowledge trees from parsed content"""
        print(f"🌳 Creating knowledge trees from content (length: {len(parsed_content)})...")
        print(f"🌳 Making Groq API request for tree generation...")
        
        chain = self.tree_prompt | self.llm
        response = await chain.ainvoke({
            "content": parsed_content,
            "max_levels": self.max_levels
        })
        
        print(f"✅ Groq API response received (length: {len(response.content)} chars)")
        
        # Parse the JSON response
        content = response.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Find JSON array in the response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                trees_data = json.loads(json_match.group())
            else:
                # Try parsing the entire content
                trees_data = json.loads(content)
            
            return trees_data
        except json.JSONDecodeError as e:
            print(f"Error parsing knowledge tree JSON: {e}")
            print(f"Response content: {content[:500]}")
            # Return a default tree structure
            return [{
                "root_concept": "General Topics",
                "tree": {
                    "concept": "General Topics",
                    "level": 0,
                    "children": []
                }
            }]
    
    async def generate_question_for_node(
        self, 
        concept: str, 
        context: str, 
        level: int
    ) -> Dict[str, Any]:
        """Generate a multiple choice question for a node"""
        print(f"❓ Making Groq API request to generate question for: {concept} (Level {level})...")
        
        chain = self.question_prompt | self.llm
        response = await chain.ainvoke({
            "concept": concept,
            "context": context,
            "level": level
        })
        
        print(f"✅ Groq API response received for question (length: {len(response.content)} chars)")
        
        # Parse the JSON response
        content = response.content.strip()
        
        try:
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to parse JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                question_data = json.loads(json_match.group())
            else:
                question_data = json.loads(content)
            
            return question_data
        except json.JSONDecodeError as e:
            print(f"Error parsing question JSON: {e}")
            print(f"Response content: {content[:200]}")
            # Return a default question structure
            return {
                "question": f"What is {concept}?",
                "options": {
                    "A": "Option A",
                    "B": "Option B",
                    "C": "Option C",
                    "D": "Option D"
                },
                "correct_answer": "A",
                "explanation": "Default explanation"
            }
    
    async def build_tree_with_questions(
        self, 
        tree_structure: Dict[str, Any], 
        context: str,
        node: Optional[KnowledgeTreeNode] = None,
        level: int = 0
    ) -> KnowledgeTreeNode:
        """Recursively build tree nodes and generate questions"""
        if node is None:
            # Root node
            concept = tree_structure.get("concept", "Unknown")
            node = KnowledgeTreeNode(concept, level)
        else:
            concept = tree_structure.get("concept", "Unknown")
            child_node = KnowledgeTreeNode(concept, level)
            child_node.parent = node
            node.children.append(child_node)
            node = child_node
        
        # Generate question for this node
        try:
            question = await self.generate_question_for_node(
                concept=node.concept,
                context=context,
                level=node.level
            )
            node.question = question
            
            # Print the question to console
            print("\n" + "="*80)
            print(f"📝 Question Generated for Concept: {node.concept} (Level {node.level})")
            print("="*80)
            print(f"Question: {question.get('question', 'N/A')}")
            print("\nOptions:")
            options = question.get('options', {})
            for option_key in ['A', 'B', 'C', 'D']:
                if option_key in options:
                    marker = "✓" if option_key == question.get('correct_answer') else " "
                    print(f"  {marker} {option_key}. {options[option_key]}")
            print(f"\nCorrect Answer: {question.get('correct_answer', 'N/A')}")
            print(f"Explanation: {question.get('explanation', 'N/A')}")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"Error generating question for {node.concept}: {e}")
        
        # Recursively process children
        children = tree_structure.get("children", [])
        for child_structure in children:
            await self.build_tree_with_questions(
                child_structure,
                context,
                node,
                level + 1
            )
        
        return node
    
    async def process_parsed_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process parsed data to create knowledge trees with questions"""
        print("🚀 Starting process_parsed_data...")
        print(f"🚀 Input parsed_data keys: {list(parsed_data.keys())}")
        
        # Extract content from parsed data
        content = self._extract_content_from_parsed_data(parsed_data)
        
        if not content.strip():
            print("⚠️ ERROR: No content extracted from parsed data!")
            print(f"⚠️ Parsed data structure: {parsed_data}")
            return {
                "trees": [],
                "error": "No content found in parsed data"
            }
        
        print(f"✅ Content extracted successfully: {len(content)} characters")
        print(f"✅ Content preview (first 500 chars): {content[:500]}")
        
        # Create knowledge trees
        print("🔄 Calling create_knowledge_trees...")
        trees_data = await self.create_knowledge_trees(content)
        print(f"✅ Knowledge trees created: {len(trees_data)} trees")
        
        # Build trees with questions
        knowledge_trees = []
        for tree_data in trees_data:
            root_concept = tree_data.get("root_concept", "Unknown")
            tree_structure = tree_data.get("tree", {})
            
            print(f"\n🌳 Building Knowledge Tree: {root_concept}")
            print("-"*80)
            
            # Build the tree recursively
            root_node = await self.build_tree_with_questions(
                tree_structure,
                content,
                None,
                0
            )
            
            # Convert to dict
            tree_dict = {
                "root_concept": root_concept,
                "tree": root_node.to_dict()
            }
            knowledge_trees.append(tree_dict)
            
            total_nodes = self._count_nodes(root_node.to_dict())
            print(f"\n✅ Completed tree '{root_concept}' with {total_nodes} nodes")
            print("-"*80)
        
        total_questions = sum(
            self._count_nodes(tree["tree"]) for tree in knowledge_trees
        )
        
        print(f"\n🎉 Knowledge Tree Generation Complete!")
        print(f"   Total Trees: {len(knowledge_trees)}")
        print(f"   Total Nodes/Questions: {total_questions}")
        print("="*80 + "\n")
        
        return {
            "trees": knowledge_trees,
            "content_length": len(content),
            "total_nodes": total_questions
        }
    
    def _count_nodes(self, node_dict: Dict[str, Any]) -> int:
        """Count total nodes in a tree"""
        count = 1  # Count this node
        for child in node_dict.get("children", []):
            count += self._count_nodes(child)
        return count

