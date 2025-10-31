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
- Be AS CONCISE AS POSSIBLE with the number of levels - only create levels when absolutely necessary
- CONSOLIDATE into ONE tree unless the core concepts are fundamentally different domains (e.g., completely unrelated topics like "Medicine" vs "Mathematics")
- If concepts are related or can be unified, consolidate them into a single tree
- Maximum number of trees: {max_trees} (based on number of documents uploaded)
- Start with broad, high-level concepts
- Split each concept into more specific subconcepts ONLY when it truly adds educational value
- Maximum depth: {max_levels} levels (but you do NOT need to use all {max_levels} levels)
- Prefer fewer levels over more levels - create only as many levels as necessary
- Trees can be 1, 2, 3, 4, or {max_levels} levels deep - choose the MINIMUM depth needed
- Each node should represent a distinct learning topic or concept

Parsed Content:
{content}

Instructions:
1. CONSOLIDATE: Unless concepts are fundamentally different domains, create ONE unified tree
2. Identify the main broad concepts (level 0) - consolidate related concepts under a single root
3. For each concept, create logical subdivisions ONLY when it makes significant educational sense
4. Be concise - do NOT force additional levels just to reach {max_levels} levels - use the minimum needed
5. Prefer shallow trees (1-2 levels) over deep trees unless depth is truly necessary
6. Maximum {max_trees} trees - only create separate trees if concepts are fundamentally unrelated
7. Return a JSON array of trees (1 to {max_trees} trees), where each tree has this structure:
   {{
     "root_concept": "Main topic name",
     "tree": {{
       "concept": "Concept name",
       "level": 0,
       "children": [
         {{
           "concept": "Subconcept name",
           "level": 1,
           "children": []
         }}
       ]
     }}
   }}

Important:
- Be CONCISE: Keep concept names concise and clear (10-30 characters)
- Be CONCISE: Use the MINIMUM number of levels needed - prefer shallow structures
- Ensure hierarchical relationships are logical
- Maximum depth is {max_levels} levels, but you can and SHOULD use fewer levels (aim for 1-3 levels when possible)
- DO NOT SKIP LEVELS: Levels must be sequential (0, 1, 2, 3...) - if a parent is level 0, children MUST be level 1, not level 2
- Each child must be exactly 1 level deeper than its parent (child level = parent level + 1)
- Include "level" field in each node - MUST match the actual depth in the tree
- Include "children" array even if empty
- CONSOLIDATION: Prefer 1 tree unless concepts are fundamentally different - maximum {max_trees} trees
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
Existing Questions (for uniqueness check): {existing_questions}

CRITICAL INSTRUCTIONS:
- BE CONCISE: Keep questions short and to the point while still being clear and insightful
- BE UNIQUE: The question MUST be completely different from all existing questions listed above
- BE INSIGHTFUL: Create questions that test deep understanding, not just surface knowledge
- ONLY use information from the provided Context above. Do NOT use any external knowledge.
- If the context does not contain sufficient information to create a question about the concept, indicate this clearly.
- All questions, answers, and explanations MUST be derived solely from the provided context.
- Do not add information that is not present in the context.
- Do not create a question that is similar or rephrased from the existing questions.

Instructions:
1. Create a CONCISE, clear, unambiguous multiple choice question that tests understanding of this concept based ONLY on the context provided
2. The question MUST be completely different from any questions in the existing questions list
3. Keep questions SHORT but INSIGHTFUL - aim for brevity without sacrificing clarity
4. Provide 4 answer options (A, B, C, D) that are all derived from the context - keep options concise too
5. Exactly one answer should be correct based on the context
6. The incorrect answers (distractors) should be plausible but clearly wrong based on the context
7. Make questions appropriate for the concept level (level {level})
8. Return ONLY valid JSON in this exact format:
   {{
     "question": "The question text here?",
     "options": {{
       "A": "First option",
       "B": "Second option",
       "C": "Third option",
       "D": "Fourth option"
     }},
     "correct_answer": "A",
     "explanation": "Brief explanation of why the correct answer is correct (based only on the context)"
   }}

IMPORTANT: If the context does not contain enough information to create a valid question, return:
{{
  "question": null,
  "options": {{}},
  "correct_answer": "",
  "explanation": "Insufficient information in context to generate question"
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
            # Handle two possible structures:
            # 1. New structure with "results" array (like PDF)
            image_results = image_data.get("results", [])
            print(f"🔍 Image results count: {len(image_results)}")
            
            if image_results:
                # Structure: {"results": [{"llm_output": "..."}, ...]}
                for idx, result in enumerate(image_results):
                    llm_output = result.get("llm_output", "")
                    if llm_output:
                        print(f"🔍 Image result {idx} - found llm_output")
                        content_parts.append(llm_output)
            else:
                # 2. Old structure with "raw" field directly
                raw_content = image_data.get("raw", "")
                if raw_content:
                    print(f"🔍 Image data - found raw content (length: {len(raw_content)})")
                    # Try to parse JSON if it's JSON, otherwise use as-is
                    try:
                        parsed_json = json.loads(raw_content)
                        # Extract useful fields from JSON response
                        if isinstance(parsed_json, dict):
                            description = parsed_json.get("description", "")
                            concepts = parsed_json.get("concepts", [])
                            text_snippets = parsed_json.get("text_snippets", [])
                            
                            if description:
                                content_parts.append(f"Image description: {description}")
                            if concepts:
                                content_parts.append(f"Concepts found: {', '.join(concepts) if isinstance(concepts, list) else str(concepts)}")
                            if text_snippets:
                                content_parts.append(f"Text found in image: {', '.join(text_snippets) if isinstance(text_snippets, list) else str(text_snippets)}")
                        else:
                            content_parts.append(str(parsed_json))
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, use as plain text
                        content_parts.append(raw_content)
                
                # Also check if there's a "urls" field for logging
                urls = image_data.get("urls", [])
                if urls:
                    print(f"🔍 Image data - found {len(urls)} image URL(s)")
        
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
    
    def _validate_and_fix_tree_levels(self, tree_structure: Dict[str, Any], expected_level: int = 0) -> Dict[str, Any]:
        """Validate and fix tree levels to ensure they are sequential without gaps"""
        concept = tree_structure.get("concept", "Unknown")
        current_level = tree_structure.get("level", expected_level)
        
        # Fix level if it doesn't match expected level
        if current_level != expected_level:
            print(f"⚠️ Fixing level mismatch for '{concept}': found {current_level}, expected {expected_level}")
            current_level = expected_level
        
        # Validate level doesn't exceed max
        if current_level >= self.max_levels:
            print(f"⚠️ Skipping '{concept}' - level {current_level} exceeds max_levels ({self.max_levels})")
            return {
                "concept": concept,
                "level": current_level,
                "children": []
            }
        
        fixed_tree = {
            "concept": concept,
            "level": current_level,
            "children": []
        }
        
        # Recursively validate and fix children
        children = tree_structure.get("children", [])
        for child in children:
            # Each child must be exactly 1 level deeper than parent
            fixed_child = self._validate_and_fix_tree_levels(child, current_level + 1)
            fixed_tree["children"].append(fixed_child)
        
        return fixed_tree
    
    async def create_knowledge_trees(self, parsed_content: str, max_trees: int = 1) -> List[Dict[str, Any]]:
        """Create knowledge trees from parsed content"""
        print(f"🌳 Creating knowledge trees from content (length: {len(parsed_content)})...")
        print(f"🌳 Maximum trees allowed: {max_trees}")
        print(f"🌳 Making Groq API request for tree generation...")
        
        chain = self.tree_prompt | self.llm
        response = await chain.ainvoke({
            "content": parsed_content,
            "max_levels": self.max_levels,
            "max_trees": max_trees
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
            
            # Validate and fix tree levels to ensure no gaps
            validated_trees = []
            for tree_data in trees_data:
                root_concept = tree_data.get("root_concept", "Unknown")
                tree_structure = tree_data.get("tree", {})
                
                print(f"🔍 Validating tree structure for '{root_concept}'...")
                fixed_tree = self._validate_and_fix_tree_levels(tree_structure, expected_level=0)
                
                validated_trees.append({
                    "root_concept": root_concept,
                    "tree": fixed_tree
                })
                print(f"✅ Tree '{root_concept}' validated and fixed if needed")
            
            # Limit number of trees based on max_trees (if provided)
            if len(validated_trees) > max_trees:
                print(f"⚠️ Generated {len(validated_trees)} trees, limiting to {max_trees}")
                validated_trees = validated_trees[:max_trees]
            
            return validated_trees
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
        level: int,
        existing_questions: str = "None"
    ) -> Dict[str, Any]:
        """Generate a multiple choice question for a node"""
        print(f"❓ Making Groq API request to generate question for: {concept} (Level {level})...")
        
        chain = self.question_prompt | self.llm
        response = await chain.ainvoke({
            "concept": concept,
            "context": context,
            "level": level,
            "existing_questions": existing_questions
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
        level: int = 0,
        existing_questions: Optional[List[str]] = None
    ) -> KnowledgeTreeNode:
        """Recursively build tree nodes and generate questions"""
        if existing_questions is None:
            existing_questions = []
        
        # Validate level doesn't exceed max_levels
        if level >= self.max_levels:
            print(f"⚠️ Skipping node at level {level} - exceeds max_levels ({self.max_levels})")
            return node if node else KnowledgeTreeNode("Skipped", level)
        
        # Validate that the tree structure's level matches expected level (no skipping)
        structure_level = tree_structure.get("level", level)
        if structure_level != level:
            print(f"⚠️ Level mismatch for '{tree_structure.get('concept', 'Unknown')}': structure has {structure_level}, expected {level}")
            print(f"⚠️ Fixing to expected level {level}")
            structure_level = level
        
        if node is None:
            # Root node
            concept = tree_structure.get("concept", "Unknown")
            node = KnowledgeTreeNode(concept, structure_level)
        else:
            concept = tree_structure.get("concept", "Unknown")
            # Ensure child level is exactly parent level + 1 (no skipping)
            expected_child_level = node.level + 1
            if structure_level != expected_child_level:
                print(f"⚠️ Level gap detected for '{concept}': found {structure_level}, expected {expected_child_level}")
                print(f"⚠️ Fixing to expected level {expected_child_level}")
                structure_level = expected_child_level
            
            child_node = KnowledgeTreeNode(concept, structure_level)
            child_node.parent = node
            node.children.append(child_node)
            node = child_node
        
        # Generate question for this node with uniqueness check (single attempt)
        question = None
        try:
            # Format existing questions for the prompt
            existing_questions_str = "\n".join([f"- {q}" for q in existing_questions]) if existing_questions else "None"
            
            question = await self.generate_question_for_node(
                concept=node.concept,
                context=context,
                level=node.level,
                existing_questions=existing_questions_str
            )
            
            # Check if question is valid and unique
            question_text = question.get("question", "")
            if not question_text:
                print(f"⚠️ Skipping '{node.concept}' - no question generated")
                question = None
            elif question_text.lower() in [q.lower() for q in existing_questions]:
                print(f"⚠️ Skipping '{node.concept}' - question is not unique")
                question = None
            else:
                # Question is valid and unique - add to list and assign to node
                existing_questions.append(question_text)
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
            print(f"⚠️ Error generating question for '{node.concept}': {e}")
            print(f"⚠️ Skipping question for '{node.concept}'")
            question = None
        
        # Recursively process children (only if level < max_levels - 1)
        if level < self.max_levels - 1:
            children = tree_structure.get("children", [])
            for child_structure in children:
                await self.build_tree_with_questions(
                    child_structure,
                    context,
                    node,
                    level + 1,
                    existing_questions
                )
        else:
            print(f"⚠️ Skipping children of level {level} node - would exceed max_levels")
        
        return node
    
    async def process_parsed_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process parsed data to create knowledge trees with questions"""
        print("🚀 Starting process_parsed_data...")
        print(f"🚀 Input parsed_data keys: {list(parsed_data.keys())}")
        
        # Count number of unique documents uploaded
        file_paths = parsed_data.get("file_paths", [])
        num_documents = len(set(file_paths)) if file_paths else 1
        max_trees = max(1, num_documents)  # At least 1 tree, at most num_documents
        print(f"📄 Found {num_documents} unique document(s), maximum trees allowed: {max_trees}")
        
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
        trees_data = await self.create_knowledge_trees(content, max_trees=max_trees)
        print(f"✅ Knowledge trees created: {len(trees_data)} trees (max allowed: {max_trees})")
        
        # Build trees with questions
        knowledge_trees = []
        all_questions = []  # Track all questions across all trees for uniqueness
        
        for tree_data in trees_data:
            root_concept = tree_data.get("root_concept", "Unknown")
            tree_structure = tree_data.get("tree", {})
            
            print(f"\n🌳 Building Knowledge Tree: {root_concept}")
            print("-"*80)
            
            # Build the tree recursively, passing the accumulated questions list
            root_node = await self.build_tree_with_questions(
                tree_structure,
                content,
                None,
                0,
                all_questions
            )
            
            # Collect questions from this tree
            def collect_questions(node_dict: Dict[str, Any], questions_list: List[str]):
                question = node_dict.get("question")
                if question and isinstance(question, dict):
                    q_text = question.get("question", "")
                    if q_text:
                        questions_list.append(q_text)
                for child in node_dict.get("children", []):
                    collect_questions(child, questions_list)
            
            tree_questions = []
            collect_questions(root_node.to_dict(), tree_questions)
            print(f"✅ Collected {len(tree_questions)} questions from tree '{root_concept}'")
            
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

