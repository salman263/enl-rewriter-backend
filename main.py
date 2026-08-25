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
    num_rewrites: int = 1  # নতুন ফিচার: কয়টি রেজাল্ট চাই

@app.get("/")
def read_root():
    return {"message": "WordAi Advanced Backend is running!"}

@app.post("/api/rewrite")
async def rewrite(request: RewriteRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "API Key is missing!"}
            
        client = genai.Client(api_key=api_key)
        AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

        # Advanced Prompt Engineering (AI Bypass & Multiple Rewrites)
        prompt = f"""You are an advanced, human-like AI text rewriter designed to bypass AI detection.
Original Text: "{request.text}"

Instructions:
1. Rewrite the text exactly {request.num_rewrites} times to provide different variations.
2. Tone/Strictness: {request.tone}. 
   - If "Fluent": Keep the meaning exactly the same, change only a few words (synonyms), keep the original sentence structure.
   - If "Regular": Rewrite for better flow, change phrasing, but keep the core meaning intact.
   - If "Creative": Be highly creative, change sentence structures entirely, use dynamic vocabulary, but retain the general idea.
3. Make the writing sound 100% natural and human. Do not use robotic phrasing.

Output Format:
Return EXACTLY {request.num_rewrites} distinct rewritten version(s).
Separate each version using this exact string: |||
Do not include any other text, intro, or markdown. Just the versions separated by |||.
"""
        
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt,
        )
        
        # এআইয়ের রেজাল্ট থেকে আলাদা আলাদা অপশনগুলো বের করা
        raw_text = response.text
        rewrites = [text.strip() for text in raw_text.split("|||") if text.strip()]
        
        return {"rewrites": rewrites}
        
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}