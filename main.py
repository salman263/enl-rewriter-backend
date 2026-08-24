from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os

# আপনার API Key এখানে দিন
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

app = FastAPI(title="ENL Semantic Rewriter API")

# フロントএন্ড (Frontend) থেকে যেন API কল করা যায়, সেজন্য CORS যুক্ত করা
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=API_KEY)

# ইউজার থেকে কী ধরনের ডেটা আসবে তার একটি মডেল
class RewriteRequest(BaseModel):
    text: str
    tone: str = "professional"

# আমাদের মূল API রুট (Endpoint)
@app.post("/api/rewrite")
async def rewrite_api(request: RewriteRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
        
    prompt = f"""
    You are an expert ENL (Emulated Natural Language) Semantic Rewriter. Your job is to rewrite the following text completely while keeping the exact original meaning, facts, and intent intact. 
    
    Follow these strict rules:
    1. Do not just replace synonyms. Restructure the sentences completely (e.g., change active to passive, combine or split sentences).
    2. The output must flow naturally and read like it was written by a human expert.
    3. Ensure 100% uniqueness to bypass AI detectors and plagiarism checkers.
    4. Keep the tone: {request.tone}.
    5. Output ONLY the rewritten text, nothing else.

    Original Text to Rewrite:
    "{request.text}"
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return {"original": request.text, "rewritten": response.text, "tone": request.tone}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating text: {e}")

# ব্রাউজারে API ঠিকমতো চলছে কি না চেক করার জন্য
@app.get("/")
def read_root():
    return {"message": "Welcome to ENL Semantic Rewriter API. The server is running!"}