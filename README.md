# HackRx Document QA API

A FastAPI-based document processing and question-answering API using RAG (Retrieval Augmented Generation) with Google Gemini 2.0 Flash and Pinecone vector database.

## Features

- **Document Processing**: Download and process PDF documents from URLs
- **Text Chunking**: Intelligent text splitting for optimal embedding
- **Vector Search**: Store and retrieve document embeddings using Pinecone
- **RAG-based QA**: Answer questions using retrieved context and Google Gemini 2.0 Flash
- **Authentication**: Bearer token-based API security
- **Scalable**: Ready for deployment on multiple platforms

## API Endpoints

### POST `/hackrx/run`
Process documents and answer questions using RAG.

**Headers:**
```
Authorization: Bearer <api_key>
Content-Type: application/json
```

**Request Body:**
```json
{
    "documents": "https://example.com/document.pdf",
    "questions": [
        "What is the grace period for premium payment?",
        "What is the waiting period for pre-existing diseases?"
    ]
}
```

**Response:**
```json
{
    "answers": [
        "A grace period of thirty days is provided for premium payment...",
        "There is a waiting period of thirty-six (36) months..."
    ]
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
    "status": "healthy",
    "service": "hackrx-api"
}
```

## Setup Instructions

### Prerequisites

1. **Python 3.9+**
2. **Google AI API Key** - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **Pinecone Account** - Sign up at [Pinecone](https://www.pinecone.io/)

### Local Development

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd hackrx-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Set up Pinecone:**
   - Create a Pinecone account
   - Create a new index with dimension 384 and cosine metric
   - Note your API key and environment

4. **Run the application:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Environment Variables

Create a `.env` file with the following variables:

```env
# Google Gemini Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment_here
PINECONE_INDEX_NAME=hackrx-documents

# API Configuration
API_KEY=your_api_bearer_token_here
HOST=0.0.0.0
PORT=8000
```

## Deployment on Render

### Using Docker Build (Recommended)

1. **Create Render Account:** Sign up at [Render](https://render.com/)

2. **Create New Web Service:**
   - Connect your GitHub repository
   - Choose "Docker" as the environment
   - Set the following configuration:

3. **Render Configuration:**
   ```
   Name: hackrx-api
   Environment: Docker
   Build Command: (leave empty - Dockerfile handles this)
   Start Command: (leave empty - Dockerfile handles this)
   ```

4. **Environment Variables in Render:**
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   PINECONE_API_KEY=your_pinecone_api_key_here
   PINECONE_ENVIRONMENT=your_pinecone_environment
   PINECONE_INDEX_NAME=hackrx-documents
   API_KEY=your_bearer_token_here
   ```

5. **Deploy:**
   - Click "Create Web Service"
   - Render will automatically build and deploy your Docker container
   - Your API will be available at `https://your-service-name.onrender.com`

### Alternative Deployment Options

#### 1. Railway
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

#### 2. Heroku
1. Install Heroku CLI
2. Create Heroku app:
```bash
heroku create your-app-name
```
3. Set environment variables:
```bash
heroku config:set GOOGLE_API_KEY=your_key
heroku config:set PINECONE_API_KEY=your_key
# ... set other variables
```
4. Deploy:
```bash
git push heroku main
```

#### 3. Local Docker

1. **Build image:**
```bash
docker build -t hackrx-api .
```

2. **Run container:**
```bash
docker run -p 8000:8000 --env-file .env hackrx-api
```

3. **Using Docker Compose:**
```bash
docker-compose up -d
```

## Testing

Run the test script to validate functionality:

```bash
python test_api.py
```

This will test:
- Health endpoint
- Authentication
- Document processing and QA

## API Usage Example

```python
import httpx
import asyncio

async def test_api():
    url = "https://your-api-url.onrender.com/hackrx/run"
    headers = {
        "Authorization": "Bearer your_api_key",
        "Content-Type": "application/json"
    }
    
    data = {
        "documents": "https://example.com/policy.pdf",
        "questions": [
            "What is the grace period for premium payment?",
            "What are the waiting periods?"
        ]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        result = response.json()
        
        for i, answer in enumerate(result["answers"]):
            print(f"Q{i+1}: {data['questions'][i]}")
            print(f"A{i+1}: {answer}\n")

# Run the test
asyncio.run(test_api())
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │ Document        │    │   QA Service    │
│                 │    │ Processor       │    │                 │
│ /hackrx/run     │───▶│                 │───▶│                 │
│ Authentication  │    │ PDF Download    │    │ Vector Search   │
│ Request/Response│    │ Text Extraction │    │ Gemini 2.0 QA   │
└─────────────────┘    │ Chunking        │    │ Context Retrieval│
                       │ Embedding       │    └─────────────────┘
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Pinecone      │
                       │   Vector DB     │
                       │                 │
                       │ Store/Retrieve  │
                       │ Document        │
                       │ Embeddings      │
                       └─────────────────┘
```

## Technical Stack

- **Backend**: FastAPI
- **LLM**: Google Gemini 2.0 Flash
- **Vector Database**: Pinecone
- **PDF Processing**: PyPDF2
- **Text Processing**: LangChain
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Deployment**: Docker, Render, Railway, Heroku

## Performance Considerations

- **Caching**: Documents are processed once and stored in Pinecone
- **Chunking**: Optimized chunk size (1000 chars) with overlap (200 chars)
- **Retrieval**: Top-K similarity search with context expansion
- **Timeout**: 30-second response time limit
- **Concurrency**: Async/await for non-blocking operations
- **Embeddings**: Lightweight SentenceTransformers model for fast processing

## Security

- Bearer token authentication
- Input validation with Pydantic
- HTTPS required for production
- Environment-based configuration
- No sensitive data in logs

## Google Gemini API Setup

1. **Get API Key:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the key for your environment variables

2. **API Features Used:**
   - Model: `gemini-2.0-flash`
   - Temperature: 0.1 for consistent responses
   - Safety settings: Block harmful content
   - Max tokens: 1000

## Pinecone Setup

1. **Create Account:** Sign up at [Pinecone](https://www.pinecone.io/)
2. **Create Index:**
   - Name: `hackrx-documents`
   - Dimension: `384` (for all-MiniLM-L6-v2 embeddings)
   - Metric: `cosine`
3. **Get Credentials:**
   - API Key from Pinecone console
   - Environment (e.g., `us-west1-gcp`)

## Render Deployment Checklist

✅ **Before Deployment:**
- [ ] Dockerfile optimized for Render
- [ ] Environment variables configured
- [ ] Google API key obtained
- [ ] Pinecone index created (dimension: 384)
- [ ] Repository pushed to GitHub

✅ **Render Configuration:**
- [ ] Docker environment selected
- [ ] Auto-deploy enabled
- [ ] Environment variables set
- [ ] Custom domain (optional)

✅ **Post-Deployment:**
- [ ] Health check passes: `GET /health`
- [ ] API authentication works
- [ ] Test document processing
- [ ] Monitor logs for errors

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check API_KEY in environment variables
2. **Pinecone Connection Error**: Verify API key and environment
3. **Google API Rate Limits**: Check your API key quota
4. **PDF Download Timeout**: Check document URL accessibility
5. **Memory Issues**: Consider smaller chunk sizes for large documents
6. **Render Build Fails**: Check Dockerfile and requirements.txt

### Logs

Check application logs for detailed error information:
```bash
# Local development
python main.py

# Docker
docker logs container_name

# Render
Check logs in Render dashboard
```

### Render-Specific Issues

1. **Port Binding**: Render sets `PORT` environment variable automatically
2. **Build Time**: Initial builds may take 5-10 minutes
3. **Cold Starts**: First request after inactivity may be slower
4. **Memory Limits**: Free tier has 512MB RAM limit

## Cost Considerations

- **Google Gemini**: Pay per API call (very affordable)
- **Pinecone**: Free tier includes 1M vectors
- **Render**: Free tier with limitations, $7/month for production
- **SentenceTransformers**: Free, runs locally

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Ensure all environment variables are set correctly
4. Verify API keys and permissions
5. Check Render deployment logs