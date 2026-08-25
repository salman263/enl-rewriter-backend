from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RewriteRequest(BaseModel):
    text: str
    tone: str
    num_rewrites: int = 1

@app.get("/")
def read_root():
    return {"message": "Semantic SEO Advanced Backend is running!"}

@app.post("/api/rewrite")
async def rewrite(request: RewriteRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "API Key is missing!"}
            
        client = genai.Client(api_key=api_key)
        AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

        # 🚀 Advanced Semantic SEO & NLP Prompt Engineering
        prompt = f"""You are an Expert SEO Content Writer and NLP (Natural Language Processing) Specialist.
Your task is to rewrite the text to be perfectly Semantic SEO-optimized and highly human-like to bypass AI detectors.

Original Text: "{request.text}"

Semantic SEO & Writing Rules:
1. Entities & Intent: Preserve all core entities (names, locations, brands, specific data). Maintain the original search intent.
2. LSI & Context: Use natural Latent Semantic Indexing (LSI) phrasing. Enhance the topical depth without keyword stuffing.
3. EEAT & Readability: Write in a highly engaging, authoritative, and concise manner. Avoid fluff, filler words, and passive voice. 
4. AI Bypass: Ensure the text flows naturally like a Native English speaker. Vary sentence length and structure to avoid robotic patterns.
5. Tone Constraint: {request.tone}.
   - If "Fluent" (Conservative): Keep structure similar, improve flow, fix grammar, retain meaning entirely.
   - If "Regular": Rephrase for better SEO and engagement, modernize vocabulary.
   - If "Creative" (Adventurous): Highly dynamic sentence restructuring, vivid vocabulary, deeply engaging while keeping core intent.

Output Formatting Instructions:
Return EXACTLY {request.num_rewrites} distinct rewritten version(s).
Separate each version using this exact string: |||
Do not include any intro, outro, HTML, markdown, or extra text. Just the rewritten text versions separated by |||.
"""
        
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt,
        )
        
        raw_text = response.text
        # আলাদা আলাদা অপশনগুলো বের করা
        rewrites = [text.strip() for text in raw_text.split("|||") if text.strip()]
        
        if not rewrites:
            return {"error": "AI could not generate the rewrites. Please try again."}
            
        return {"rewrites": rewrites}
        
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}