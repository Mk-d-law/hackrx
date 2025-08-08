from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List
import os
from dotenv import load_dotenv
import logging

from services.document_processor import DocumentProcessor
from services.qa_service import QAService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HackRx Document QA API",
    description="API for processing documents and answering questions using RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# API Key from environment
API_KEY = os.getenv("API_KEY", "default_api_key")

# Pydantic models
class QuestionRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

class AnswerResponse(BaseModel):
    answers: List[str]

# Initialize services
document_processor = DocumentProcessor()
qa_service = QAService()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the bearer token"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "HackRx Document QA API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "hackrx-api"}

@app.post("/hackrx/run", response_model=AnswerResponse)
async def process_documents_and_questions(
    request: QuestionRequest,
    token: str = Depends(verify_token)
):
    """
    Process documents and answer questions using RAG
    
    Args:
        request: Request containing document URL and questions
        token: Bearer token for authentication
    
    Returns:
        AnswerResponse: Contains answers to all questions
    """
    try:
        logger.info(f"Processing request with {len(request.questions)} questions")
        logger.info(f"Document URL: {request.documents}")
        
        # Process the document
        logger.info("Processing document...")
        document_id = await document_processor.process_document(str(request.documents))
        
        # Generate answers for all questions
        logger.info("Generating answers...")
        answers = []
        for i, question in enumerate(request.questions):
            logger.info(f"Processing question {i+1}/{len(request.questions)}: {question[:100]}...")
            answer = await qa_service.answer_question(question, document_id)
            answers.append(answer)
        
        logger.info(f"Successfully generated {len(answers)} answers")
        return AnswerResponse(answers=answers)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )