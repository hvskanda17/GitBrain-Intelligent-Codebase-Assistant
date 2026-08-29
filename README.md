# GitBrain - Intelligent Codebase Assistant

GitBrain is an intelligent AI-powered codebase assistant designed to help you understand, navigate, and analyze your repositories. It consists of a modern web frontend and a powerful Python backend that parses code, builds dependency graphs, and uses Large Language Models (LLMs) to provide deep insights into your codebase.

## 🚀 Features

- **Codebase Analysis:** Automatically parses and analyzes codebases.
- **Dependency & Call Graphs:** Resolves circular dependencies and builds call graphs for better navigation.
- **AI Chat Interface:** Ask questions about your code and get intelligent, context-aware answers.
- **Repository Management:** Easily add and manage different projects and repositories.
- **Dead Code Detection:** Identifies unused code to help maintain a clean codebase.

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLAlchemy & Alembic (PostgreSQL/SQLite)
- **AI Integration:** LLM client and embedding generation
- **Code Analysis:** Custom AST parsers, knowledge graph builder

### Frontend
- **Framework:** Next.js & React (TypeScript)
- **Styling:** Tailwind CSS (implied via standard Next.js setup) & modern UI components
- **State & Data Fetching:** React Query / Custom API hooks

## 📦 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- PostgreSQL (or SQLite for local development)

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   Copy `.env.example` to `.env` and fill in the necessary API keys and database URLs.
5. Run database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License.
