# GitBrain — Intelligent Codebase Assistant

GitBrain is an AI-powered codebase assistant that helps developers understand and interact with software repositories using natural-language conversations.

It indexes repository source code, retrieves relevant code context, and uses an LLM to generate repository-aware answers with source references.

## Features

- JWT Authentication — Secure user registration, login, access tokens, and protected API endpoints.
- Project & Repository Management — Create projects and associate repositories for analysis.
- Code Indexing & Retrieval — Index repository files, functions, and classes for code-aware search.
- AI Codebase Chat — Ask natural-language questions about an indexed repository.
- RAG Pipeline — Retrieve relevant code context before generating AI responses.
- SSE Streaming — Stream AI responses to the frontend in real time.
- Chat Sessions — Create, rename, pin, delete, and manage repository-specific conversations.
- Source References — Display the code sources used to generate responses.
- Mock AI Provider — Run and test the chat functionality locally without an external LLM API.
- PostgreSQL — Persistent storage for users, projects, repositories, indexed code, and chat history.
- Redis — Support for caching and background application workflows.
- Docker — Containerized development environment for the application services.

## Tech Stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- JWT Authentication

### AI & Search
- RAG (Retrieval-Augmented Generation)
- LLM integration
- Code indexing
- Full-text code search
- SSE (Server-Sent Events) streaming

### Development
- Docker
- Docker Compose
- Git

## Architecture

GitBrain follows a repository-aware RAG architecture:

User
  ↓
Next.js Frontend
  ↓
FastAPI Backend
  ↓
Chat Orchestrator
  ↓
Repository Retrieval
  ↓
Relevant Code Context
  ↓
LLM / Mock LLM
  ↓
SSE Stream
  ↓
Frontend Chat Interface

## How It Works

1. A user creates a project and adds a repository.
2. GitBrain indexes the repository and extracts useful code information such as files, functions, and classes.
3. The user opens the repository's Chat interface.
4. The user asks a natural-language question.
5. GitBrain searches the indexed repository for relevant code.
6. The retrieved context is provided to the LLM.
7. The generated response is streamed back to the frontend using Server-Sent Events (SSE).
8. The conversation and response sources are persisted in PostgreSQL.

## RAG

GitBrain uses Retrieval-Augmented Generation (RAG) to make AI responses aware of the repository being analyzed.

Instead of asking the LLM to answer only from its general knowledge, GitBrain first retrieves relevant code from the repository and provides that context to the model.

This allows users to ask questions such as:

- "How does authentication work?"
- "Where is the database connection configured?"
- "Explain this function."
- "How are repositories indexed?"
- "Where is JWT validation implemented?"

## SSE Streaming

GitBrain uses Server-Sent Events (SSE) to stream assistant responses from the backend to the frontend.

This allows the response to appear progressively instead of waiting for the entire AI response to finish.

## Redis

Redis is used as an infrastructure component for fast in-memory operations and application workflows. It can support caching and background processing as the project grows.

## Local Development

### Prerequisites

- Node.js
- Python
- Docker Desktop
- PostgreSQL
- Redis

### Start Backend

```bash
cd backend
docker compose up -d

Start Frontend
cd frontend
npm install
npm run dev

The frontend runs on:

http://localhost:3000

The backend runs on:

http://localhost:8000

Environment Configuration

Create the required environment configuration for the backend.

Example:
APP_NAME=GitBrain
ENVIRONMENT=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://gitbrain:gitbrain@localhost:5432/gitbrain
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256

CORS_ORIGINS=["http://localhost:3000"]

LLM_PROVIDER=mock
LLM_API_KEY=
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

For local development, LLM_PROVIDER=mock can be used to test the complete chat flow without consuming an external LLM API.

Project Structure
GitBrain/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── llm/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
└── docker-compose.yml
Authentication

GitBrain uses JWT-based authentication to protect API resources.

The authentication flow includes:

User registration
User login
Access tokens
Protected API endpoints
Current-user validation
Role-based access control
Chat

Each repository can have its own chat sessions.

Users can:

Create a new chat
Ask questions about the repository
View previous messages
Rename conversations
Pin conversations
Delete conversations
View retrieved source references
Testing

Backend tests:
 pytest

Frontend type checking:

npx tsc --noEmit

SSE parser tests:

npx tsx src/lib/sse-parser.test.ts
Future Improvements
Semantic/vector search for improved retrieval
File explorer
Code dependency graphs
Improved repository indexing
Multiple LLM provider support
Background indexing jobs
Production deployment
Advanced code navigation
Improved source citations
License

This project is currently intended for educational and development purposes.


**GitHub repository description:**

`AI-powered codebase assistant for understanding, searching, and chatting with GitHub repositories using R
