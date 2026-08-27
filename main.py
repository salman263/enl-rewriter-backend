import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from pymongo import MongoClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 MONGODB SETUP (WITH NEW COLLECTIONS)
MONGO_URI = os.environ.get("MONGO_URI")
client_mongo = MongoClient(MONGO_URI) if MONGO_URI else None
db = client_mongo["zerowordai"] if client_mongo else None
users_collection = db["users"] if db is not None else None
plans_collection = db["plans"] if db is not None else None # নতুন: প্ল্যানের জন্য
analytics_collection = db["analytics"] if db is not None else None # নতুন: অ্যানালিটিক্সের জন্য

@app.get("/")
def read_root():
    return {"message": "AI Backend with Dynamic Plans & Analytics is running!"}

# ==========================================
# 📊 1. ANALYTICS ROUTE
# ==========================================
@app.get("/api/admin/analytics")
async def get_analytics():
    try:
        total_users = users_collection.count_documents({}) if users_collection is not None else 0
        stats = analytics_collection.find_one({"_id": "global_stats"}) if analytics_collection is not None else None
        total_rewrites = stats.get("total_rewrites", 0) if stats else 0
        
        return {
            "total_users": total_users,
            "total_rewrites": total_rewrites,
            "active_database": "MongoDB Atlas",
            "ai_engine": os.environ.get("GEMINI_MODEL", "gemini-pro")
        }
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 💳 2. DYNAMIC PLAN MANAGEMENT ROUTES
# ==========================================
class PlanModel(BaseModel):
    planId: str
    name: str
    price: int
    credits: int
    features: list[str]

# পাবলিক রাউট: প্রাইসিং পেজে প্ল্যান দেখানোর জন্য
@app.get("/api/plans")
async def get_plans():
    try:
        if plans_collection is not None:
            plans = list(plans_collection.find({}, {"_id": 0}))
            # যদি ডেটাবেসে কোনো প্ল্যান না থাকে, তবে ডিফল্ট প্ল্যানগুলো তৈরি করে নেবে
            if not plans:
                default_plans = [
                    {"planId": "free", "name": "Free Plan", "price": 0, "credits": 5, "features": ["5 Free Credits", "Standard SEO Rewrite", "Basic Humanizer"]},
                    {"planId": "pro", "name": "Pro Plan", "price": 19, "credits": 100, "features": ["100 Credits / month", "Advanced AI Bypass", "Priority Speed"]},
                    {"planId": "enterprise", "name": "Enterprise", "price": 49, "credits": 9999, "features": ["Unlimited Credits", "Max Human Bypass", "24/7 VIP Support"]}
                ]
                plans_collection.insert_many(default_plans)
                plans = default_plans
            return {"plans": plans}
        return {"plans": []}
    except Exception as e:
        return {"error": str(e)}

# অ্যাডমিন রাউট: নতুন প্ল্যান তৈরি বা আপডেট করার জন্য
@app.post("/api/admin/plans")
async def save_plan(req: PlanModel):
    try:
        if plans_collection is not None:
            plans_collection.update_one(
                {"planId": req.planId},
                {"$set": req.dict()},
                upsert=True
            )
            return {"success": True, "message": "Plan saved successfully!"}
        return {"error": "DB not connected"}
    except Exception as e:
        return {"error": str(e)}

# অ্যাডমিন রাউট: প্ল্যান ডিলিট করার জন্য
@app.delete("/api/admin/plans/{plan_id}")
async def delete_plan(plan_id: str):
    try:
        if plans_collection is not None:
            plans_collection.delete_one({"planId": plan_id})
            return {"success": True, "message": "Plan deleted!"}
        return {"error": "DB error"}
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 👥 3. USER MANAGEMENT ROUTES (আগেরগুলোই)
# ==========================================
@app.get("/api/user/{user_id}")
async def get_user_data(user_id: str):
    if users_collection is not None:
        user = users_collection.find_one({"userId": user_id})
        if user: return {"credits": user.get("credits", 5), "plan": user.get("plan", "Free"), "banned": user.get("banned", False)}
    return {"credits": 5, "plan": "Free", "banned": False}

@app.get("/api/admin/users")
async def get_all_users():
    if users_collection is not None:
        return {"users": list(users_collection.find({}, {"_id": 0}))}
    return {"users": []}

class AdminActionRequest(BaseModel):
    userId: str
    plan: str
    credits: int
    banned: bool

@app.post("/api/admin/super-update")
async def super_update_user(req: AdminActionRequest):
    if users_collection is not None:
        users_collection.update_one({"userId": req.userId}, {"$set": {"plan": req.plan, "credits": req.credits, "banned": req.banned}})
        return {"success": True}
    return {"error": "DB Error"}

@app.delete("/api/admin/delete-user/{user_id}")
async def delete_user(user_id: str):
    if users_collection is not None:
        users_collection.delete_one({"userId": user_id})
        return {"success": True}
    return {"error": "DB error"}

# ==========================================
# ✍️ 4. REWRITE ROUTE (With Analytics Tracking)
# ==========================================
class RewriteRequest(BaseModel):
    text: str
    tone: str
    num_rewrites: int = 1
    mode: str = "rewrite"
    userId: str = "guest"

@app.post("/api/rewrite")
async def rewrite_text(req: RewriteRequest):
    try:
        if users_collection is not None and req.userId != "guest":
            user = users_collection.find_one({"userId": req.userId})
            if not user:
                user = {"userId": req.userId, "credits": 5, "plan": "Free", "banned": False}
                users_collection.insert_one(user)
            if user.get("banned", False) == True:
                return {"error": "Your account has been banned by the administrator."}
            if user.get("credits", 0) <= 0:
                return {"error": "Limit Reached! Please upgrade your plan."}

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: return {"error": "API Key is missing!"}
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-pro"))

        if req.mode == "avoid_ai":
            prompt = f'Expert AI Detection Bypass Specialist. Rewrite to score 100% human. Rules: High Burstiness. Text: "{req.text}". Bypass: {req.tone}. Return {req.num_rewrites} versions separated by |||VARIATION|||.'
        else:
            prompt = f'Expert SEO Writer. Semantic SEO-optimized. Text: "{req.text}". Tone: {req.tone}. Return {req.num_rewrites} versions separated by |||VARIATION|||.'

        response = model.generate_content(prompt)
        output = response.text
        variations = [v.strip() for v in output.split("|||VARIATION|||") if v.strip()]
        if not variations: variations = [output.strip()]
            
        credits_left = "Unlimited"
        if users_collection is not None and req.userId != "guest":
            users_collection.update_one({"userId": req.userId}, {"$inc": {"credits": -1}})
            credits_left = users_collection.find_one({"userId": req.userId}).get("credits", 0)
        
        # 🚀 NEW: ANALYTICS TRACKING - মোট জেনারেট সংখ্যা ১ করে বাড়িয়ে দেবে
        if analytics_collection is not None:
            analytics_collection.update_one(
                {"_id": "global_stats"},
                {"$inc": {"total_rewrites": 1}},
                upsert=True
            )
        
        return {"rewrites": variations[:req.num_rewrites], "credits_left": credits_left}
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}
