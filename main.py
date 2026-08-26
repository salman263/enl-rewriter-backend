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
    userId: str = "guest"

@app.get("/")
def read_root():
    return {"message": "AI Backend with Admin & Pricing System is running!"}

# 1. 🔍 ইউজারের ক্রেডিট ও প্ল্যান চেক করার রাউট
@app.get("/api/user/{user_id}")
async def get_user_data(user_id: str):
    try:
        if users_collection is not None:
            user = users_collection.find_one({"userId": user_id})
            if user:
                return {
                    "credits": user.get("credits", 5),
                    "plan": user.get("plan", "Free")
                }
        return {"credits": 5, "plan": "Free"}
    except Exception as e:
        return {"error": str(e)}

# 2. 👑 অ্যাডমিন রাউট: সব ইউজারের লিস্ট দেখার জন্য (Future scalable)
@app.get("/api/admin/users")
async def get_all_users():
    try:
        if users_collection is not None:
            all_users = list(users_collection.find({}, {"_id": 0}))
            return {"users": all_users}
        return {"users": []}
    except Exception as e:
        return {"error": str(e)}

# 3. 💳 প্রাইসিং প্ল্যান আপডেট করার রাউট (Stripe বা Manual Upgrade এর জন্য)
class PlanUpgradeRequest(BaseModel):
    userId: str
    plan: str
    credits: int

@app.post("/api/admin/upgrade-plan")
async def upgrade_plan(req: PlanUpgradeRequest):
    try:
        if users_collection is not None:
            users_collection.update_one(
                {"userId": req.userId},
                {"$set": {"plan": req.plan, "credits": req.credits}}
            )
            return {"success": True, "message": f"User upgraded to {req.plan} successfully!"}
        return {"error": "Database not connected"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/rewrite")
async def rewrite_text(req: RewriteRequest):
    try:
        # 1. 🛡️ AUTH & CREDIT CHECK
        if users_collection is not None and req.userId != "guest":
            user = users_collection.find_one({"userId": req.userId})
            
            if not user:
                # নতুন ইউজার হলে Free প্ল্যানে ৫ ক্রেডিট দিয়ে সেভ হবে
                user = {"userId": req.userId, "credits": 5, "plan": "Free"}
                users_collection.insert_one(user)
            
            # ক্রেডিট শেষ কি না চেক
            if user.get("credits", 0) <= 0:
                return {"error": "Limit Reached! Please upgrade your plan to get more credits."}

        # 2. 🚀 GEMINI AI SETUP
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "API Key is missing in environment!"}
            
        genai.configure(api_key=api_key)
        ai_model_name = os.environ.get("GEMINI_MODEL", "gemini-pro")
        model = genai.GenerativeModel(ai_model_name)

        # 3. 🧠 PROMPTS
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

        response = model.generate_content(prompt)
        output = response.text
        
        variations = [v.strip() for v in output.split("|||VARIATION|||") if v.strip()]
        if not variations:
            variations = [output.strip()]
            
        # 4. 💰 DEDUCT CREDIT
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