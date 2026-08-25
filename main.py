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
    mode: str = "rewrite" # নতুন ফিচার: মোড সিলেকশন

@app.get("/")
def read_root():
    return {"message": "AI Bypass & SEO Backend is running!"}

@app.post("/api/rewrite")
async def rewrite(request: RewriteRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "API Key is missing!"}
            
        client = genai.Client(api_key=api_key)
        AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

        # 🚀 Mode Selection (Rewrite vs Avoid AI Detection)
        if request.mode == "avoid_ai":
            prompt = f"""You are an expert AI Detection Bypass Specialist and a highly skilled human writer.
            Your ultimate goal is to rewrite the provided text so that it scores 100% human on all AI detectors (like Originality.ai, GPTZero, and Turnitin) while maintaining the exact original meaning.

            Original Text: "{request.text}"

            Crucial Humanization Rules:
            1. High Burstiness: Drastically vary sentence lengths. Mix very short, punchy sentences (2-5 words) with longer, complex ones. 
            2. High Perplexity: Avoid predictable word choices and common AI transition words (e.g., "Furthermore", "In conclusion", "It is important to note", "Delve into"). Use natural, slightly unconventional vocabulary.
            3. Imperfections & Nuance: Write like a native English speaking human. Use active voice, idiomatic expressions, and natural phrasing. Do not sound robotic or perfectly symmetrical.
            4. Bypass Level: {request.tone} (1=Basic, 2=Advanced, 3=Maximum Humanization). 
               - If Maximum, completely restructure the paragraphs, change perspectives slightly if needed, and use highly idiomatic language to guarantee a 100% human score.

            Output Formatting Instructions:
            Return EXACTLY {request.num_rewrites} distinct rewritten version(s).
            Separate each version using this exact string: |||
            Do not include any intro, outro, HTML, markdown, or extra text.
            """
        else:
            prompt = f"""You are an Expert SEO Content Writer and NLP Specialist.
            Your task is to rewrite the text to be perfectly Semantic SEO-optimized and highly human-like.

            Original Text: "{request.text}"

            Semantic SEO Rules:
            1. Entities & Intent: Preserve all core entities. Maintain the original search intent.
            2. LSI & Context: Use natural Latent Semantic Indexing (LSI) phrasing. 
            3. EEAT & Readability: Write in a highly engaging, authoritative manner.
            4. Tone Constraint: {request.tone}.

            Output Formatting Instructions:
            Return EXACTLY {request.num_rewrites} distinct rewritten version(s).
            Separate each version using this exact string: |||
            Do not include any extra text.
            """
        
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt,
        )
        
        raw_text = response.text
        rewrites = [text.strip() for text in raw_text.split("|||") if text.strip()]
        
        if not rewrites:
            return {"error": "AI could not generate the rewrites. Please try again."}
            
        return {"rewrites": rewrites}
        
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}