# main.py
"""
FastAPI backend for the CRRI RAG Chatbot.

Initializes the Pinecone vector store retriever using Hugging Face embeddings,
the Google Gemini Flash LLM, creates the RAG chain, and defines the API endpoints.
"""

import os
import logging
import json
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
import pinecone
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not PINECONE_API_KEY or not GOOGLE_API_KEY:
    raise ValueError("PINECONE_API_KEY and GOOGLE_API_KEY environment variables must be set in .env file.")

PINECONE_INDEX_NAME = "crri-kb-index-hf"
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/api.log"),
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

# --- Pydantic Models ---
class Message(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    conversation_history: List[Message]

class QueryResponse(BaseModel):
    answer: str

# --- Global Variables ---
vector_store = None
chat_model = None

# --- FastAPI App ---
app = FastAPI(
    title="CRRI RAG Chatbot API",
    description="API for querying the CRRI knowledge base using Retrieval Augmented Generation.",
    version="1.0.0"
)

# --- CORS Configuration ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://huggingface.co",
    "https://*.hf.space",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize RAG components on startup."""
    global vector_store, chat_model

    logger.info("Starting up FastAPI application...")
    
    try:
        # Initialize Pinecone
        pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)

        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
             logger.error(f"Index '{PINECONE_INDEX_NAME}' does not exist.")
             return
        
        hf_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )

        vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=hf_embeddings,
            pinecone_api_key=PINECONE_API_KEY
        )
        logger.info("Pinecone vector store initialized.")

    except Exception as e:
        logger.error(f"Error initializing Pinecone: {e}")
        return

    try:
        # Initialize Gemini
        chat_model = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
        )
        logger.info("Google LLM initialized.")
    except Exception as e:
        logger.error(f"Error initializing Google LLM: {e}")
        return

    logger.info("RAG components ready.")


async def analyze_query(query: str, chat_model: ChatGoogleGenerativeAI) -> Dict[str, Any]:
    """
    Analyzes the user's query to extract target division, query type, and exhaustiveness.
    """
    system_prompt = (
        "You are an expert query analyzer for the CRRI chatbot. "
        "Analyze the query and return a JSON object with these fields:\n\n"
        
        "1. **target_division**: If query mentions a division, return EXACT name from this list:\n"
        f"{json.dumps(VALID_DIVISIONS, indent=2)}\n"
        "Common abbreviations: 'CCN' -> 'Computer Center & Networking', 'ESD' -> 'Engineering Service Division', "
        "'GWS' -> 'General & Works Section', 'BES' -> 'Bridge Engineering and Structures'.\n"
        "**CRITICAL MAPPINGS**:\n"
        "- 'guest house', 'accommodation', 'stay', 'living' -> 'Guest House wing-1'\n"
        "Return null if no division mentioned.\n\n"
        
        "2. **query_type**: Classify as:\n"
        "   - 'list_contacts': Contact info for multiple people\n"
        "   - 'list_staff': List of staff/employees\n"
        "   - 'list_equipment': List of equipment\n"
        "   - 'count_query': 'How many'\n"
        "   - 'detail_query': Details about specific item/person\n"
        "   - 'general': Other questions\n\n"
        "**CRITICAL CLASSIFICATION RULES**:\n"
        "- If query mentions 'accommodation', 'guest house', 'quarters', classify as 'list_contacts'.\n"
        
        "3. **requires_exhaustive**: true if query implies needing ALL items. Otherwise false.\n\n"
        
        "Return ONLY valid JSON."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{query}")
    ])
    
    chain = prompt | chat_model | JsonOutputParser()
    
    try:
        result = await chain.ainvoke({"query": query})
        result.setdefault("target_division", None)
        result.setdefault("query_type", "general")
        result.setdefault("requires_exhaustive", False)
        return result
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return {"target_division": None, "query_type": "general", "requires_exhaustive": False}


@app.post("/chat", response_model=QueryResponse)
async def chat_endpoint(query_request: QueryRequest):
    """
    Endpoint to handle chat queries using the RAG system.
    """
    global vector_store, chat_model

    if not vector_store or not chat_model:
        raise HTTPException(status_code=500, detail="RAG system is not ready.")

    if not query_request.conversation_history or query_request.conversation_history[-1].role != "user":
        raise HTTPException(status_code=400, detail="Invalid conversation history.")

    conversation_history = query_request.conversation_history
    latest_user_message = conversation_history[-1]
    latest_question = latest_user_message.content

    logger.info(f"Received query: '{latest_question}'")

    try:
        # --- 1. Query Analysis ---
        lower_query = latest_question.lower()
        
        # Fast track for Accommodation/Guest House
        if any(kw in lower_query for kw in ["accommodation", "accomodation", "guest house", "guest house", "quarters", "living"]):
            analysis_result = {
                "target_division": "Guest House wing-1",
                "query_type": "list_contacts",
                "requires_exhaustive": False
            }
        # Fast track for Tenders
        elif "tender" in lower_query:
             analysis_result = {
                "target_division": None,
                "query_type": "general",
                "requires_exhaustive": False
            }
        else:
            analysis_result = await analyze_query(latest_question, chat_model)
            
        target_division = analysis_result.get("target_division")
        query_type = analysis_result.get("query_type", "general")
        requires_exhaustive = analysis_result.get("requires_exhaustive", False)

        # --- 2. Dynamic k Selection ---
        k_by_type = {
            "list_contacts": 200,
            "list_staff": 300,
            "list_equipment": 100,
            "count_query": 200,
            "detail_query": 20,
            "general": 15
        }
        k = k_by_type.get(query_type, 15)
        
        if requires_exhaustive:
            k = max(k, 300)
        
        if target_division and query_type in ["list_contacts", "list_staff"]:
            k = 100

        # --- 3. Retrieval ---
        search_query = latest_question
        if target_division and query_type in ["list_contacts", "list_staff"]:
            search_query = f"staff members employees scientists technicians officers working in {target_division} division"
        
        search_kwargs = {}
        if target_division and query_type in ["list_contacts", "list_staff"]:
            search_kwargs["filter"] = {"divisions": target_division}

        docs = vector_store.similarity_search(
            search_query,
            k=k,
            **search_kwargs
        )
        
        # Post-filter by division if needed
        if target_division and query_type in ["list_contacts", "list_staff"]:
            filtered_staff_docs = []
            found_staff_names = []
            
            for doc in docs:
                metadata = doc.metadata
                if metadata.get('page_type') == 'staff_profile':
                     filtered_staff_docs.append(doc)
                     if metadata.get('name'):
                        found_staff_names.append(metadata.get('name'))
            
            # Retrieve contacts for these staff members
            if found_staff_names:
                names_to_search = found_staff_names[:30] 
                contact_query = f"contact details email phone mobile for {' '.join(names_to_search)}"
                
                contact_docs = vector_store.similarity_search(
                    contact_query,
                    k=max(500, len(names_to_search) * 10) 
                )
                
                relevant_contact_docs = []
                for c_doc in contact_docs:
                    c_meta = c_doc.metadata
                    c_name = c_meta.get('name', '')
                    if c_name:
                        def normalize_name(n):
                            n = n.lower().replace('.', ' ')
                            for prefix in ['mr ', 'dr ', 'ms ', 'mrs ', 'sh ']:
                                if n.startswith(prefix):
                                    n = n[len(prefix):]
                            return n.strip()

                        c_name_norm = normalize_name(c_name)
                        
                        is_match = False
                        for staff_name in found_staff_names:
                            s_name_norm = normalize_name(staff_name)
                            
                            if s_name_norm in c_name_norm or c_name_norm in s_name_norm:
                                is_match = True
                                break
                            
                            s_tokens = set(s_name_norm.split())
                            c_tokens = set(c_name_norm.split())
                            common = s_tokens.intersection(c_tokens)
                            if len(common) >= 2 or (len(s_tokens) == 1 and len(common) == 1):
                                is_match = True
                                break
                        
                        if is_match:
                            relevant_contact_docs.append(c_doc)
                
                seen_content = set()
                final_docs = []
                for d in filtered_staff_docs + relevant_contact_docs:
                    if d.page_content not in seen_content:
                        final_docs.append(d)
                        seen_content.add(d.page_content)
                
                docs = final_docs
            else:
                if filtered_staff_docs:
                    docs = filtered_staff_docs
        
        # --- 4. Prepare Context ---
        escaped_context_parts = []
        for doc in docs:
            escaped_content = doc.page_content.replace('{', '{{').replace('}', '}}')
            escaped_context_parts.append(escaped_content)
        context = "\n\n---\n\n".join(escaped_context_parts)

        # --- 5. Construct Prompt ---
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

        for msg in conversation_history[:-1]:
             if msg.role == "user" or msg.role == "assistant":
                 escaped_msg_content = msg.content.replace('{', '{{').replace('}', '}}')
                 if msg.role == "user":
                     messages_for_prompt.append(("human", escaped_msg_content))
                 elif msg.role == "assistant":
                     messages_for_prompt.append(("ai", escaped_msg_content))

        escaped_latest_question = latest_question.replace('{', '{{').replace('}', '}}')
        final_user_prompt_with_context = (
            f"Here's my question: {escaped_latest_question}\n\n"
            f"Context from CRRI website:\n{context}\n\n"
            f"Please answer following the formatting rules. Keep it clean and professional."
        )
        messages_for_prompt.append(("human", final_user_prompt_with_context))

        prompt_template = ChatPromptTemplate.from_messages(messages_for_prompt)
        from langchain_core.output_parsers import StrOutputParser
        chain = prompt_template | chat_model | StrOutputParser()
        answer = await chain.ainvoke({})

        logger.info(f"Generated answer: {answer}")
        return QueryResponse(answer=answer)

    except Exception as e:
        logger.error(f"Error processing query '{latest_question}': {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


# --- Static File Serving ---
frontend_dist_path = Path(__file__).parent / "frontend" / "dist"
if frontend_dist_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist_path), html=True), name="frontend")
else:
    logger.warning("Running in API-only mode. Build the frontend with 'npm run build' to enable the UI.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
