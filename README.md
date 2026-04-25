# FastKwan

A FastAPI-based service for Traditional Chinese Medicine (TCM) syndrome differentiation, lifestyle recommendations, and prescription suggestions using AI and vector search.

## Overview

**FastKwan** is a Python-based API service that combines AI models with vector search to assist with Traditional Chinese Medicine diagnostics. It provides endpoints for:

- **Syndrome Differentiation**: Analyzes patient symptoms to identify TCM syndromes
- **Lifestyle Recommendations**: Retrieves prevention and lifestyle advice for diseases
- **Prescription Suggestions**: Suggests relevant prescriptions based on symptoms

## Features

- **AI-Powered NER**: Uses GPT-3.5-turbo to extract symptoms from patient descriptions
- **Vector Search**: Leverages Pinecone for semantic similarity search across TCM knowledge bases
- **Intelligent Reranking**: Uses Cohere reranking to improve result relevance
- **MongoDB Integration**: Stores and retrieves disease information and lifestyle recommendations
- **Interactive Documentation**: Auto-generated API docs via Swagger UI and ReDoc

## Technology Stack

- **Framework**: FastAPI 0.115+
- **AI/ML**: OpenAI GPT-3.5, Cohere Rerank, LangChain
- **Vector Database**: Pinecone
- **Database**: MongoDB Atlas
- **Server**: Uvicorn

## Prerequisites

- Python 3.10 or higher
- pip package manager
- API keys for: OpenAI, Pinecone, Cohere, MongoDB Atlas

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/kneeraazon404/fastkwan.git
   cd fastkwan
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
COHERE_API_KEY=your_cohere_api_key
MONGODB_URI=your_mongodb_connection_string
PINECONE_INDEX_NAME=evidgpt  # optional, defaults to "evidgpt"
```

## Usage

1. Start the FastAPI application:

   ```bash
   uvicorn main:app --reload
   ```

2. Access the API documentation:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

3. Test endpoints:

   **Health Check:**

   ```bash
   curl http://localhost:8000/health
   ```

   **Syndrome Differentiation:**

   ```bash
   curl -X POST "http://localhost:8000/syndrome" \
     -H "Content-Type: application/json" \
     -d '{"query": "患者咳嗽，喉咙痛，有痰，鼻塞"}'
   ```

   **Lifestyle Recommendations:**

   ```bash
   curl -X POST "http://localhost:8000/lifestyle" \
     -H "Content-Type: application/json" \
     -d '{"query": "感冒"}'
   ```

   **Prescription Suggestions:**

   ```bash
   curl -X POST "http://localhost:8000/prescription" \
     -H "Content-Type: application/json" \
     -d '{"query": "患者咳嗽，喉咙痛，有痰"}'
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info and health check |
| `/health` | GET | Health check endpoint |
| `/syndrome` | POST | Perform TCM syndrome differentiation |
| `/lifestyle` | POST | Get lifestyle/prevention recommendations |
| `/prescription` | POST | Get prescription suggestions |

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature-name"`
4. Push to your fork: `git push origin feature-name`
5. Open a pull request
