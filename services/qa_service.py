import os
import logging
from typing import List, Dict
import pinecone
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class QAService:
    def __init__(self):
        """Initialize the QA service with Google Gemini and Pinecone"""
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "hackrx-documents")
        
        # Initialize embeddings model (same as document processor)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384
        
        # Configure Google Gemini
        genai.configure(api_key=self.google_api_key)
        
        # Initialize Pinecone
        self._init_pinecone()
        
        # Create system prompt
        self.system_prompt = """You are an expert assistant that answers questions based on the provided context from insurance policy documents.

Instructions:
1. Use ONLY the information provided in the context to answer questions
2. If the answer is not found in the context, respond with "The information is not available in the provided document"
3. Be precise and specific in your answers
4. Include relevant details like numbers, percentages, time periods, and conditions
5. If there are multiple parts to a question, address each part
6. Maintain a professional and clear tone
7. Do not make assumptions or add information not present in the context"""
    
    def _init_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            pinecone.init(
                api_key=self.pinecone_api_key,
                environment=self.pinecone_environment
            )
            
            self.index = pinecone.Index(self.pinecone_index_name)
            logger.info("Pinecone initialized successfully for QA service")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone in QA service: {str(e)}")
            raise
    
    def create_question_embedding(self, question: str) -> List[float]:
        """Create embedding for the question"""
        try:
            embedding = self.embedding_model.encode([question])
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error creating question embedding: {str(e)}")
            raise
    
    async def retrieve_relevant_chunks(self, question: str, document_id: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant document chunks for the question"""
        try:
            logger.info(f"Retrieving relevant chunks for question: {question[:100]}...")
            
            # Create embedding for the question
            question_embedding = self.create_question_embedding(question)
            
            # Query Pinecone for similar chunks
            results = self.index.query(
                vector=question_embedding,
                filter={"document_id": document_id},
                top_k=top_k,
                include_metadata=True,
                include_values=False
            )
            
            relevant_chunks = []
            for match in results['matches']:
                relevant_chunks.append({
                    'text': match['metadata']['text'],
                    'score': match['score'],
                    'chunk_index': match['metadata']['chunk_index']
                })
            
            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {str(e)}")
            raise
    
    def expand_context(self, relevant_chunks: List[Dict], document_id: str) -> str:
        """Expand context by combining relevant chunks"""
        try:
            # Sort chunks by relevance score (highest first)
            sorted_chunks = sorted(relevant_chunks, key=lambda x: x['score'], reverse=True)
            
            # Build context from chunks
            context_parts = []
            for chunk in sorted_chunks:
                context_parts.append(chunk['text'])
            
            # Combine and return
            context = "\n\n".join(context_parts)
            return context
            
        except Exception as e:
            logger.error(f"Error expanding context: {str(e)}")
            # Fallback to basic context
            return "\n\n".join([chunk['text'] for chunk in relevant_chunks])
    
    async def call_gemini_api(self, prompt: str) -> str:
        """Call Google Gemini API directly using httpx"""
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.google_api_key
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 1000,
                    "stopSequences": []
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        return candidate['content']['parts'][0]['text'].strip()
                
                logger.error(f"Unexpected Gemini API response format: {result}")
                return "Error: Unable to generate response from Gemini API"
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return f"Error processing question: {str(e)}"
    
    async def answer_question(self, question: str, document_id: str) -> str:
        """Answer a question using RAG with Gemini"""
        try:
            logger.info(f"Answering question for document {document_id}")
            
            # Retrieve relevant chunks
            relevant_chunks = await self.retrieve_relevant_chunks(question, document_id, top_k=8)
            
            if not relevant_chunks:
                return "The information is not available in the provided document."
            
            # Expand context with relevant chunks
            context = self.expand_context(relevant_chunks, document_id)
            
            # Create the complete prompt
            full_prompt = f"""{self.system_prompt}

Context from the document:
{context}

Question: {question}

Answer:"""
            
            # Generate answer using Gemini
            logger.info("Generating answer with Gemini 2.0 Flash")
            answer = await self.call_gemini_api(full_prompt)
            
            logger.info(f"Generated answer: {answer[:100]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return f"Error processing question: {str(e)}"
    
    async def answer_multiple_questions(self, questions: List[str], document_id: str) -> List[str]:
        """Answer multiple questions for a document"""
        try:
            logger.info(f"Answering {len(questions)} questions for document {document_id}")
            
            answers = []
            for i, question in enumerate(questions):
                logger.info(f"Processing question {i+1}/{len(questions)}")
                answer = await self.answer_question(question, document_id)
                answers.append(answer)
            
            return answers
            
        except Exception as e:
            logger.error(f"Error answering multiple questions: {str(e)}")
            raise