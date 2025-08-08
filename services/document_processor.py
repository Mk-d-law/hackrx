import httpx
import hashlib
import tempfile
import os
from typing import List, Dict
import logging
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import pinecone
import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        """Initialize the document processor with Pinecone and SentenceTransformers"""
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_host = os.getenv("PINECONE_HOST")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "hackrx-documents")
        
        # Initialize sentence transformer for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize Pinecone
        self._init_pinecone()
    
    def _init_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            # Initialize Pinecone with modern client
            from pinecone import Pinecone
            pc = Pinecone(api_key=self.pinecone_api_key)
            
            # Connect to existing index using host
            self.index = pc.Index(host=self.pinecone_host)
            logger.info("Pinecone initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {str(e)}")
            # Fallback to legacy initialization if available
            try:
                pinecone.init(api_key=self.pinecone_api_key)
                self.index = pinecone.Index(self.pinecone_index_name)
                logger.info("Pinecone initialized with legacy client")
            except Exception as e2:
                logger.error(f"Legacy Pinecone initialization also failed: {str(e2)}")
                raise
    
    async def download_pdf(self, url: str) -> str:
        """Download PDF from URL and return the file path"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Downloading PDF from: {url}")
                response = await client.get(url)
                response.raise_for_status()
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                
                logger.info(f"PDF downloaded successfully to: {temp_file_path}")
                return temp_file_path
                
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            text = ""
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
        finally:
            # Clean up temporary file
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding"""
        try:
            logger.info("Chunking text for embedding")
            chunks = self.text_splitter.split_text(text)
            logger.info(f"Created {len(chunks)} text chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise
    
    def create_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """Create embeddings for chunks using SentenceTransformers"""
        try:
            logger.info(f"Creating embeddings for {len(chunks)} chunks")
            embeddings = self.embedding_model.encode(chunks)
            logger.info(f"Created {len(embeddings)} embeddings")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise
    
    async def store_embeddings(self, chunks: List[str], embeddings: List[List[float]], document_id: str):
        """Store embeddings in Pinecone"""
        try:
            logger.info(f"Storing {len(embeddings)} embeddings in Pinecone")
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{document_id}_chunk_{i}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk[:1000]  # Store first 1000 chars in metadata
                    }
                })
            
            # Store in Pinecone (batch upsert)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Successfully stored {len(vectors)} vectors in Pinecone")
            
        except Exception as e:
            logger.error(f"Error storing embeddings: {str(e)}")
            raise
    
    def generate_document_id(self, url: str) -> str:
        """Generate a unique document ID based on URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    async def document_exists(self, document_id: str) -> bool:
        """Check if document already exists in Pinecone"""
        try:
            # Query for any vector with this document_id
            results = self.index.query(
                vector=[0.0] * self.embedding_dimension,  # Dummy vector
                filter={"document_id": document_id},
                top_k=1,
                include_metadata=True
            )
            return len(results['matches']) > 0
            
        except Exception as e:
            logger.error(f"Error checking document existence: {str(e)}")
            return False
    
    async def process_document(self, url: str) -> str:
        """Main method to process a document from URL"""
        try:
            # Generate document ID
            document_id = self.generate_document_id(url)
            logger.info(f"Processing document with ID: {document_id}")
            
            # Check if document already exists
            if await self.document_exists(document_id):
                logger.info(f"Document {document_id} already exists, skipping processing")
                return document_id
            
            # Download PDF
            pdf_path = await self.download_pdf(url)
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            
            # Chunk text
            chunks = self.chunk_text(text)
            
            # Create embeddings
            embeddings = self.create_embeddings(chunks)
            
            # Store embeddings
            await self.store_embeddings(chunks, embeddings, document_id)
            
            logger.info(f"Document {document_id} processed successfully")
            return document_id
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise