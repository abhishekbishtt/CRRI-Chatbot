# main.py
"""
FastAPI backend for the CRRI RAG Chatbot.

This script initializes the Pinecone vector store retriever using Hugging Face embeddings,
the Google Gemini Flash LLM, creates the RAG chain, and defines the API endpoints.
Includes CORS configuration and handles conversation history with improved prompt formatting.
"""

import os
import logging
import json
from pathlib import Path
# --- Add CORS Middleware Import ---
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# Import Pydantic models for request/response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
# Langchain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
import pinecone
# Add these lines to load the .env file
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not PINECONE_API_KEY or not GOOGLE_API_KEY:
    raise ValueError("PINECONE_API_KEY and GOOGLE_API_KEY environment variables must be set in .env file.")

PINECONE_INDEX_NAME = "crri-kb-index-hf" # The name of your *existing* Pinecone index
GEMINI_MODEL_NAME = "gemini-2.5-flash" # Or "gemini-1.5-flash" if preferred

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/api.log"), # Log to a file
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Constants ---
VALID_DIVISIONS = [
    "Accounts Section",
    "Administration AO Office",
    "Administration COA Office",
    "Bridge Engineering and Structures",
    "CSIR-Central Road Research Institute",
    "Canteen",
    "Computer Center & Networking",
    "Director Office",
    "Engineering Service Division",
    "Establishment Section- I",
    "Establishment Section-ll",
    "Flexible Pavements",
    "General & Works Section",
    "Geotechnical Engineering",
    "Guest House wing-1",
    "Horticulture",
    "Information, Liaison & Training",
    "Knowledge Resource Centre",
    "Maharani Bagh Staff Quarter Maintenance",
    "Main Store",
    "Mechanical and Transport",
    "Pavement Evaluation",
    "Personnel Cell",
    "Planning, Monitoring & Evaluation",
    "Purchase Section",
    "Rajbhasha",
    "Right to Information Cell",
    "Rigid Pavements",
    "Traffic Engineering and Safety",
    "Transport Planning and Environment",
    "Vigilance"
]

# --- Pydantic Models for API ---
class Message(BaseModel):
    role: str # "user" or "assistant"
    content: str

class QueryRequest(BaseModel):
    # Send the full conversation history
    conversation_history: List[Message]

class QueryResponse(BaseModel):
    answer: str

# --- Global Variables for RAG Chain ---
# We'll initialize these once when the app starts up.
# This avoids re-initializing on every request, which is inefficient.
vector_store = None # Store vector_store globally to allow dynamic retrieval
chat_model = None # Store the LLM instance globally

# --- FastAPI App Instance ---
app = FastAPI(
    title="CRRI RAG Chatbot API",
    description="API for querying the CRRI knowledge base using Retrieval Augmented Generation with conversation history.",
    version="1.0.0"
)

# --- Add CORS Middleware Configuration ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",  # Backend port (for testing)
    "http://127.0.0.1:8080",
    "https://huggingface.co",  # Hugging Face main domain
    "https://*.hf.space",  # Hugging Face Spaces domain pattern
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Event Handler for App Startup ---
@app.on_event("startup")
async def startup_event():
    """
    Initialize the RAG chain components when the FastAPI application starts.
    """
    global vector_store, chat_model # Declare globals

    logger.info("Starting up FastAPI application...")
    logger.info("Initializing RAG system components...")

    # 1. Initialize Pinecone Client and Vector Store
    logger.info("Connecting to Pinecone index...")
    try:
        # Initialize the Pinecone client instance
        pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)

        # Check if index exists
        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
             logger.error(f"Index '{PINECONE_INDEX_NAME}' does not exist.")
             return # Exit startup if index not found
        logger.info(f"Index '{PINECONE_INDEX_NAME}' found.")

        # Initialize the Hugging Face Embedding model
        logger.info("Initializing Hugging Face embedding model for Pinecone connection...")
        hf_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )
        logger.info("Hugging Face embedding model initialized for Pinecone connection.")

        # Create the vector store instance connected to the index
        vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=hf_embeddings,
            pinecone_api_key=PINECONE_API_KEY
        )
        logger.info("Pinecone vector store initialized successfully.")

    except Exception as e:
        logger.error(f"Error initializing Pinecone vector store during startup: {e}")
        return # Exit startup if error occurs

    # 2. Initialize Google Gemini LLM
    logger.info(f"Initializing Google LLM: {GEMINI_MODEL_NAME}")
    try:
        chat_model = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0, # Low temperature for factual consistency
        )
        logger.info("Google LLM initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Google LLM during startup: {e}")
        return # Exit startup if error occurs

    logger.info("RAG components initialized. Ready for chat requests with history.")
    logger.info("FastAPI application startup complete.")


# --- Helper Function for Query Analysis ---
async def analyze_query(query: str, chat_model: ChatGoogleGenerativeAI) -> Dict[str, Any]:
    """
    Analyzes the user's query to extract:
    - target_division: Specific division mentioned
    - query_type: Type of query (list_contacts, list_staff, equipment_detail, etc.)
    - requires_exhaustive: Whether query needs ALL matching documents
    """
    system_prompt = (
        "You are an expert query analyzer for the CRRI (Central Road Research Institute) chatbot. "
        "Analyze the query and return a JSON object with these fields:\n\n"
        
        "1. **target_division**: If query mentions a division, return EXACT name from this list:\n"
        f"{json.dumps(VALID_DIVISIONS, indent=2)}\n"
        "Common abbreviations: 'CCN' -> 'Computer Center & Networking', 'ESD' -> 'Engineering Service Division', "
        "'GWS' -> 'General & Works Section', 'BES' -> 'Bridge Engineering and Structures'.\n"
        "Return null if no division mentioned.\n\n"
        
        "2. **query_type**: Classify the query as one of:\n"
        "   - 'list_contacts': User wants phone numbers, emails, or contact info for multiple people\n"
        "   - 'list_staff': User wants list of staff/employees/members\n"
        "   - 'list_equipment': User wants list of equipment/facilities\n"
        "   - 'count_query': User asks 'how many' of something\n"
        "   - 'detail_query': User wants details about a specific item/person\n"
        "   - 'general': Other general questions\n\n"
        
        "3. **requires_exhaustive**: Set to true if query implies needing ALL items "
        "(e.g., 'list all', 'everyone', 'all contacts', 'how many'). Otherwise false.\n\n"
        
        "Return ONLY valid JSON."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{query}")
    ])
    
    chain = prompt | chat_model | JsonOutputParser()
    
    try:
        result = await chain.ainvoke({"query": query})
        # Ensure all expected fields exist
        result.setdefault("target_division", None)
        result.setdefault("query_type", "general")
        result.setdefault("requires_exhaustive", False)
        return result
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return {"target_division": None, "query_type": "general", "requires_exhaustive": False}


# --- API Endpoints ---

@app.post("/chat", response_model=QueryResponse)
async def chat_endpoint(query_request: QueryRequest):
    """
    Endpoint to handle chat queries using the RAG system, considering conversation history.
    Implements dynamic filtering based on query analysis.
    """
    global vector_store, chat_model

    if not vector_store or not chat_model:
        logger.error("RAG system components (vector_store or LLM) not initialized.")
        raise HTTPException(status_code=500, detail="RAG system is not ready.")

    # Extract the latest user question and conversation history
    if not query_request.conversation_history or query_request.conversation_history[-1].role != "user":
        logger.error("Invalid conversation history format or last message is not from user.")
        raise HTTPException(status_code=400, detail="Invalid conversation history format.")

    conversation_history = query_request.conversation_history
    latest_user_message = conversation_history[-1]
    latest_question = latest_user_message.content

    logger.info(f"Received query (with history): '{latest_question}'")

    try:
        # --- 1. Query Analysis ---
        analysis_result = await analyze_query(latest_question, chat_model)
        target_division = analysis_result.get("target_division")
        query_type = analysis_result.get("query_type", "general")
        requires_exhaustive = analysis_result.get("requires_exhaustive", False)
        logger.info(f"Query Analysis Result: {analysis_result}")

        # --- 2. Smart Dynamic k Selection ---
        # Base k values by query type
        k_by_type = {
            "list_contacts": 200,
            "list_staff": 300,
            "list_equipment": 100,
            "count_query": 200,
            "detail_query": 20,
            "general": 15
        }
        k = k_by_type.get(query_type, 15)
        
        # Increase k for exhaustive queries or division-specific lookups
        if requires_exhaustive:
            k = max(k, 300)
        if target_division and query_type in ["list_contacts", "list_staff"]:
            k = 500  # Get all docs for that division
            
        logger.info(f"Query type: {query_type}, requires_exhaustive: {requires_exhaustive}, k={k}")

        # --- 3. Retrieval ---
        # Modify search query for better staff/contact retrieval
        search_query = latest_question
        if target_division and query_type in ["list_contacts", "list_staff"]:
            search_query = f"staff members employees scientists technicians officers working in {target_division} division their names designations positions contacts phone email"
            logger.info(f"Modified search query for better staff retrieval: '{search_query}'")
        
        docs = vector_store.similarity_search(
            search_query,
            k=k
        )
        logger.info(f"Retrieved {len(docs)} documents from Pinecone.")
        
        # Debug: Show sample metadata
        if docs and target_division:
            sample_meta = docs[0].metadata if docs else {}
            logger.info(f"Sample metadata keys: {list(sample_meta.keys())}")
            logger.info(f"Sample primary_division: {sample_meta.get('primary_division', 'NOT FOUND')}")
        
        # Post-filter by division if needed
        if target_division and query_type in ["list_contacts", "list_staff"]:
            filtered_docs = []
            for doc in docs:
                metadata = doc.metadata
                # Check if this document belongs to the target division
                primary_div = metadata.get('primary_division', '')
                divisions_list = metadata.get('divisions', [])
                
                if (primary_div == target_division or 
                    target_division in divisions_list or
                    (isinstance(divisions_list, str) and target_division in divisions_list)):
                    filtered_docs.append(doc)
            
            docs = filtered_docs
            logger.info(f"After filtering by division '{target_division}': {len(docs)} documents")
        
        # Extract unique staff names from retrieved docs for debugging
        if target_division and query_type in ["list_contacts", "list_staff"]:
            staff_names = set()
            for doc in docs:
                metadata = doc.metadata
                if metadata.get('page_type') == 'staff_profile':
                    name = metadata.get('name', '')
                    if name:
                        staff_names.add(name)
            logger.info(f"Unique staff names in filtered docs: {len(staff_names)} - {sorted(staff_names)}")

        # --- 3. Prepare Context ---
        escaped_context_parts = []
        for doc in docs:
            # Escape literal braces in the page content to prevent formatting errors
            escaped_content = doc.page_content.replace('{', '{{').replace('}', '}}')
            escaped_context_parts.append(escaped_content)
        context = "\n\n---\n\n".join(escaped_context_parts)

        # --- 4. Construct Prompt ---
        system_prompt = (
            "You're a helpful colleague at CRRI Delhi who loves sharing information about the institute. "
            "Talk like you're having a friendly conversation.\n\n"
            
            "**Your Personality:**\n"
            "- Speak naturally, warm and approachable.\n"
            "- Avoid robotic phrases like 'Certainly!' or 'Of course!'.\n\n"
            
            "**RESPONSE LENGTH - CRITICAL:**\n"
            "- **Be CONCISE by default.** Give brief, to-the-point answers.\n"
            "- Only provide detailed information if the user explicitly asks for details/more info.\n"
            "- For simple questions, a 2-3 sentence answer is often enough.\n"
            "- Don't overwhelm users with information they didn't ask for.\n\n"
            
            "**How to Answer:**\n"
            "- Draw from the `Context` and `Conversation History` provided below.\n"
            "- **CRITICAL**: If the user asks for a list of people/staff, you MUST list EVERY SINGLE PERSON mentioned in the context. Do not omit anyone.\n"
            "- If something's not in the information, say so honestly and direct them to contact the relevant division.\n"
            "- Rephrase and summarize - don't just copy text word-for-word.\n\n"
            
            "**COUNTING - STRICT RULE:**\n"
            "- **NEVER make up or guess a count.** If asked 'how many' of something, count the actual items in the Context.\n"
            "- If you cannot count precisely from the context, say 'I have information on several...' instead of giving a made-up number.\n"
            "- **DO NOT say a specific number unless you've actually counted the items in the Context.**\n\n"
            
            "**USAGE CHARGES & PRICING - STRICT RULE:**\n"
            "- **COMPLETELY IGNORE any pricing, charges, or 'no charges' information in the Context - do NOT include it in your response.**\n"
            "- **NEVER mention specific charges, fees, or pricing for any equipment, facility, or service.**\n"
            "- **NEVER say something is 'free', has 'no charges', or 'no usage charges' - even if the Context says so.**\n"
            "- If the user specifically asks about pricing/charges, respond ONLY with: 'For usage charges and pricing information, please contact the relevant division directly.'\n"
            "- If the user did NOT ask about charges, simply DO NOT mention pricing at all.\n\n"
            
            "**FORMATTING RULES (VERY IMPORTANT):**\n\n"
            
            "1. **For Tenders/Events with structured data** - ALWAYS wrap JSON in proper code blocks:\n"
            "   Write a brief 1-2 sentence intro, then include JSON:\n"
            "   ```json\n"
            "   {{\"tenders\": [{{\"title\": \"...\", \"deadline\": \"...\", \"description\": \"...\", \"status\": \"active/expiring/expired\", \"documents\": [{{\"title\": \"...\", \"url\": \"...\"}}]}}]}}\n"
            "   ```\n"
            "   **CRITICAL: JSON must ALWAYS be inside ```json ... ``` code blocks. NEVER output raw JSON in text.**\n"
            "   Set status to 'expiring' if deadline is within 7 days, 'expired' if past, otherwise 'active'.\n\n"
            
            "2. **For Staff/Person Info** - Use this clean format:\n"
            "   **Dr. Name Here** | Designation\n"
            "   📧 email@crri.res.in · 📞 Phone Number\n"
            "   Division: Division Name\n"
            "   (Add a blank line between each person)\n\n"
            
            "3. **For Contact/Location Info** - Use inline format:\n"
            "   📍 Address · 📞 Phone · 📧 Email · 🌐 Website\n\n"
            
            "4. **For Lists of Items (3+ items)** - Use a clean table:\n"
            "   | Name | Designation | Division |\n"
            "   |------|-------------|----------|\n"
            "   | Dr. X | Scientist | Geo |\n\n"
            
            "5. **For General Information** - Use paragraphs with **bold keywords**.\n"
            "   Only use bullet points when listing 2-4 distinct items.\n"
            "   AVOID excessive bullet points - prefer flowing text.\n\n"
            
            "6. **For Events** - Similar to tenders, include JSON in code blocks:\n"
            "   ```json\n"
            "   {{\"events\": [{{\"name\": \"...\", \"date\": \"...\", \"status\": \"...\", \"brochure_url\": \"...\"}}]}}\n"
            "   ```\n\n"
            
            "**AVOID:**\n"
            "- Walls of bullet points\n"
            "- Repeating the same information\n"
            "- Generic filler text\n"
            "- Overly long responses when a short answer suffices\n"
            "- Raw JSON in text (must be in code blocks)\n"
            "- Mentioning any specific charges, prices, or saying things are free\n"
        )

        messages_for_prompt = [("system", system_prompt)]

        # Add conversation history (exclude the latest user message)
        for msg in conversation_history[:-1]:
             if msg.role == "user" or msg.role == "assistant":
                 escaped_msg_content = msg.content.replace('{', '{{').replace('}', '}}')
                 if msg.role == "user":
                     messages_for_prompt.append(("human", escaped_msg_content))
                 elif msg.role == "assistant":
                     messages_for_prompt.append(("ai", escaped_msg_content))

        # Add the latest user question WITH the retrieved context
        escaped_latest_question = latest_question.replace('{', '{{').replace('}', '}}')
        final_user_prompt_with_context = (
            f"Here's my question: {escaped_latest_question}\n\n"
            f"Context from CRRI website:\n{context}\n\n"
            f"Please answer following the formatting rules. Keep it clean and professional."
        )
        messages_for_prompt.append(("human", final_user_prompt_with_context))

        # --- 5. Invoke LLM ---
        prompt_template = ChatPromptTemplate.from_messages(messages_for_prompt)
        from langchain_core.output_parsers import StrOutputParser
        chain = prompt_template | chat_model | StrOutputParser()
        answer = await chain.ainvoke({})

        logger.info(f"Generated answer: {answer}")
        return QueryResponse(answer=answer)

    except Exception as e:
        logger.error(f"Error processing query '{latest_question}': {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")



# --- Static File Serving for React Frontend ---
frontend_dist_path = Path(__file__).parent / "frontend" / "dist"
if frontend_dist_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist_path), html=True), name="frontend")
    logger.info(f"Frontend static files mounted from: {frontend_dist_path}")
else:
    logger.warning(f"Frontend dist folder not found at: {frontend_dist_path}")
    logger.warning("Running in API-only mode. Build the frontend with 'npm run build' to enable the UI.")

# --- Main execution block for running with uvicorn ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
