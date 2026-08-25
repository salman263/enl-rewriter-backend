from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os

app = FastAPI()

# CORS ফিক্স করা হলো (allow_credentials=False করে দেওয়া হয়েছে)
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

@app.get("/")
def read_root():
    return {"message": "API is running safely!"}

@app.post("/api/rewrite")
async def rewrite(request: RewriteRequest):
    try:
        # API Key চেক করা
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"rewritten_text": "Error: GEMINI_API_KEY is missing in Render settings!"}
            
        client = genai.Client(api_key=api_key)
        
        # আমরা ডিফল্ট হিসেবে সবচেয়ে স্ট্যাবল মডেলটি ব্যবহার করছি
        AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

        prompt = f"Rewrite the following text in a {request.tone} tone. Return ONLY the rewritten text and absolutely nothing else. No intro, no options, no formatting:\n\n{request.text}"
        
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt,
        )
        
        return {"rewritten_text": response.text}
        
    except Exception as e:
        # যদি কোনো কারণে ফেইল করে, সার্ভার ক্র্যাশ না করে এরর মেসেজটি ওয়েবসাইটের স্ক্রিনে পাঠিয়ে দেবে
        return {"rewritten_text": f"Backend Error: {str(e)}"}