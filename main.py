from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os

app = FastAPI()

# CORS পারমিশন যোগ করা হলো
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # যেকোনো ওয়েবসাইট থেকে রিকোয়েস্ট অ্যালাউ করবে
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class RewriteRequest(BaseModel):
    text: str
    tone: str

@app.get("/")
def read_root():
    return {"message": "API is running!"}

@app.post("/api/rewrite")
async def rewrite(request: RewriteRequest):
    prompt = f"Rewrite the following text in a {request.tone} tone:\n\n{request.text}"
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
    )
    
    return {"rewritten_text": response.text}