from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os
from pymongo import MongoClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 MongoDB Connection Setup
MONGO_URI = os.environ.get("MONGO_URI")
client_mongo = MongoClient(MONGO_URI) if MONGO_URI else None
db = client_mongo["zerowordai"] if client_mongo else None
users_collection = db["users"] if db is not None else None

class RewriteRequest(BaseModel):
    text: str
    tone: str
    num_rewrites: int = 1
    mode: str = "rewrite"
    userId: str = "guest" # ইউজারের আইডি ফ্রন্টএন্ড থেকে আসবে

@app.get("/")
def read_root():
    return {"message": "AI Backend with MongoDB is running!"}

@app.post("/api/rewrite")
async def rewrite(request: RewriteRequest):
    try:
        # ১. Credit চেক করা (ইউজার ডেটাবেসে আছে কি না)
        if users_collection is not None and request.userId != "guest":
            user = users_collection.find_one({"userId": request.userId})
            
            # নতুন ইউজার হলে ডেটাবেসে অ্যাকাউন্ট খুলে ৫ ক্রেডিট দেওয়া হবে
            if not user:
                users_collection.insert_one({"userId": request.userId, "credits": 5})
                user = {"credits": 5}
            
            # ক্রেডিট ফুরিয়ে গেলে কাজ বন্ধ করে দেবে
            if user.get("credits", 0) <= 0:
                return {"error": "Limit Reached! You have run out of free credits. Please upgrade your plan."}

        # ২. AI Generation Logic (আগের মতোই)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "API Key is missing!"}
            
        client = genai.Client(api_key=api_key)
        AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

        if request.mode == "avoid_ai":
            prompt = f"""You are an expert AI Detection Bypass Specialist. Rewrite the text to score 100% human.
            Original Text: "{request.text}"
            Rules: High Burstiness, High Perplexity. Do not use robotic words. Bypass Level: {request.tone}.
            Return EXACTLY {request.num_rewrites} versions separated by |||. No extra text."""
        else:
            prompt = f"""You are an Expert SEO Content Writer. Rewrite the text to be Semantic SEO-optimized.
            Original Text: "{request.text}"
            Rules: Preserve entities, use LSI keywords naturally. Tone: {request.tone}.
            Return EXACTLY {request.num_rewrites} versions separated by |||. No extra text."""
        
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt,
        )
        
        raw_text = response.text
        rewrites = [text.strip() for text in raw_text.split("|||") if text.strip()]
        
        if not rewrites:
            return {"error": "AI could not generate the rewrites. Please try again."}
            
        # ৩. সফলভাবে রিরাইট হওয়ার পর ১টি ক্রেডিট কেটে নেওয়া
        credits_left = "Unlimited"
        if users_collection is not None and request.userId != "guest":
            users_collection.update_one(
                {"userId": request.userId},
                {"$inc": {"credits": -1}}
            )
            credits_left = user.get("credits", 5) - 1

        return {"rewrites": rewrites, "credits_left": credits_left}
        
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}