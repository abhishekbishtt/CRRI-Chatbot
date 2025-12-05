---
title: CRRI Chatbot
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
short_description: AI-powered chatbot for Central Road Research Institute Delhi
---

# 🤖 CRRI Chatbot

[![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Live%20Demo-blue)](https://huggingface.co/spaces/abhishekbisht/CRRI-Chatbot)

An intelligent chatbot for **Central Road Research Institute (CRRI) Delhi**, powered by **RAG (Retrieval Augmented Generation)**.

## ✨ Features

- 💬 **Natural Language Q&A** about CRRI Delhi
- 👥 **Staff Information** - Find details about researchers and divisions
- 🔬 **Equipment Database** - Browse available research equipment
- 📋 **Tender Information** - Access current and past tenders
- 🧠 **Powered by AI** - Google Gemini 2.5 Flash + Pinecone Vector Database
- 🎨 **Modern UI** - Beautiful, responsive React interface

## 🛠️ Local Installation

### 1. Clone the repository
```bash
git clone https://github.com/abhishekbishtt/CRRI-Chatbot.git
cd CRRI-Chatbot
```

### 2. Set up environment
```bash
# install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY and PINECONE_API_KEY
```

### 3. Run the application
```bash
# Start backend and frontend (if using separate terminals)
python main.py
cd frontend && npm run dev
```

## 🚀 Technology Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **LangChain** - RAG orchestration framework
- **Google Gemini 2.5 Flash** - Large Language Model
- **Pinecone** - Vector database for semantic search
- **Sentence Transformers** - Text embeddings

### Frontend
- **React 19** - Modern UI library
- **Vite** - Fast build tool
- **React Markdown** - Rich text rendering

## 🎯 How to Use

1. **Ask Questions** - Type your question about CRRI in the input box
2. **Use Suggestions** - Click on suggested questions to get started
3. **Follow Up** - The chatbot remembers conversation context
4. **Get Links** - Receive clickable links to official documents

### Example Questions:
- "Who is the director of CRRI?"
- "List all members of the CCN division"
- "What equipment is available for soil testing?"
- "Show me recent tenders"
- "Tell me about the Pavement Engineering division"

## 🔒 Privacy & Data

- All data is sourced from the official CRRI website
- No personal information is collected
- Conversations are not stored permanently
- API keys are securely managed via Hugging Face Secrets

## 🔄 Automated Data Pipeline

This project includes a production-grade automated pipeline that keeps the chatbot data fresh:

### Quick Start
```bash
# Run the complete pipeline
./scripts/run_full_pipeline.sh
```

### What it does:
1. Scrapes fresh data from CRRI website
2. Processes and cleans all data
3. Uploads to Pinecone vector database
4. Auto-cleans old files

### Documentation
- **[docs/PIPELINE_README.md](docs/PIPELINE_README.md)** - Complete pipeline documentation
- **[docs/CRON_SETUP.md](docs/CRON_SETUP.md)** - Set up automation (runs every 2 days)
- **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Quick commands

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **CRRI Delhi** - For the publicly available information
- **Google Gemini** - For the powerful LLM
- **Pinecone** - For vector database infrastructure
- **Hugging Face** - For hosting this demo

---

**Note:** This is a demonstration project. For official information, please visit the [CRRI website](https://www.crridom.gov.in/).
