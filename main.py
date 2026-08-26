import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from pymongo import MongoClient

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 SMART WORK: MongoDB Connection Setup with Environment Variable
MONGO_URI = os.environ.get("MONGO_URI")
client_mongo = MongoClient(MONGO_URI) if MONGO_URI else None
db = client_mongo["zerowordai"] if client_mongo else None
users_collection = db["users"] if db is not None else None

class RewriteRequest(BaseModel):
    text: str
    tone: str
    num_rewrites: int = 1
    mode: str = "rewrite"
    userId: str = "guest"

@app.get("/")
def read_root():
    return {"message": "AI Backend with MongoDB is running!"}

@app.post("/api/rewrite")
async def rewrite_text(req: RewriteRequest):
    try:
        # 1. 🛡️ AUTH & SECURITY: Credit চেক করা
        if users_collection is not None and req.userId != "guest":
            user = users_collection.find_one({"userId": req.userId})
            
            # নতুন ইউজার হলে অ্যাকাউন্ট খুলে ৫ ক্রেডিট দেওয়া হবে
            if not user:
                users_collection.insert_one({"userId": req.userId, "credits": 5})
                user = {"credits": 5}
            
            # ক্রেডিট ফুরিয়ে গেলে কাজ বন্ধ করে দেবে
            if user.get("credits", 0) <= 0:
                return {"error": "Limit Reached! You have run out of free credits. Please upgrade your plan."}

        # 2. 🚀 SMART WORK: API Key এবং Model Render-এর Environment থেকে নেওয়া হচ্ছে
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "API Key is missing!"}
            
        genai.configure(api_key=api_key)
        
        # আপনার আইডিয়া অনুযায়ী ডায়নামিক মডেল (Render থেকে আসবে)
        ai_model_name = os.environ.get("GEMINI_MODEL", "gemini-pro")
        model = genai.GenerativeModel(ai_model_name)

        # 3. 🧠 PROMPT LOGIC: Humanizer vs Standard Rewrite
        if req.mode == "avoid_ai":
            prompt = f"""You are an expert AI Detection Bypass Specialist. Rewrite the text to score 100% human.
            Original Text: "{req.text}"
            Rules: High Burstiness, High Perplexity. Do not use typical robotic AI words. Bypass Level: {req.tone}.
            Return EXACTLY {req.num_rewrites} variations separated by |||VARIATION|||. No extra text."""
        else:
            prompt = f"""You are an Expert SEO Content Writer. Rewrite the text to be Semantic SEO-optimized.
            Original Text: "{req.text}"
            Rules: Preserve entities, use LSI keywords naturally. Tone: {req.tone}.
            Return EXACTLY {req.num_rewrites} variations separated by |||VARIATION|||. No extra text."""

        # 4. Generate Content with Gemini
        response = model.generate_content(prompt)
        output = response.text
        
        # 5. Split Variations
        variations = [v.strip() for v in output.split("|||VARIATION|||") if v.strip()]
        if not variations:
            variations = [output.strip()]
            
        # 6. 💰 UPDATE CREDITS: সফলভাবে রিরাইট হওয়ার পর ক্রেডিট কেটে নেওয়া
        credits_left = "Unlimited"
        if users_collection is not None and req.userId != "guest":
            users_collection.update_one(
                {"userId": req.userId},
                {"$inc": {"credits": -1}}
            )
            updated_user = users_collection.find_one({"userId": req.userId})
            credits_left = updated_user.get("credits", 0)
        
        return {
            "rewrites": variations[:req.num_rewrites],
            "credits_left": credits_left
        }
        
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}