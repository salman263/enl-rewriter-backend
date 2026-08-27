import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from pymongo import MongoClient

app = FastAPI()

# ==========================================
# 🛡️ 1. CORS SETUP
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🚀 2. MONGODB SETUP
# ==========================================
MONGO_URI = os.environ.get("MONGO_URI")
client_mongo = MongoClient(MONGO_URI) if MONGO_URI else None
db = client_mongo["zerowordai"] if client_mongo else None

# Collections
users_collection = db["users"] if db is not None else None
plans_collection = db["plans"] if db is not None else None
analytics_collection = db["analytics"] if db is not None else None

@app.get("/")
def read_root(): 
    return {"message": "ZeroWordAi Ultimate Backend is running smoothly!"}

# ==========================================
# 📧 3. USER EMAIL SYNC ROUTE (New)
# ==========================================
class SyncUserRequest(BaseModel):
    userId: str
    email: str

@app.post("/api/sync-user")
async def sync_user(req: SyncUserRequest):
    try:
        if users_collection is not None:
            user = users_collection.find_one({"userId": req.userId})
            if user:
                # ইউজার আগে থেকেই থাকলে শুধু ইমেইল আপডেট করবে (লিমিট নষ্ট করবে না)
                users_collection.update_one({"userId": req.userId}, {"$set": {"email": req.email}})
            else:
                # একদম নতুন ইউজার হলে Starter প্ল্যান দিয়ে সেভ করবে
                users_collection.insert_one({
                    "userId": req.userId, 
                    "email": req.email, 
                    "seo_words": 50000, 
                    "bypass_words": 25000, 
                    "plan": "Starter", 
                    "banned": False
                })
            return {"success": True}
        return {"error": "DB error"}
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 📊 4. ANALYTICS ROUTE
# ==========================================
@app.get("/api/admin/analytics")
async def get_analytics():
    try:
        total_users = users_collection.count_documents({}) if users_collection is not None else 0
        stats = analytics_collection.find_one({"_id": "global_stats"}) if analytics_collection is not None else None
        return {
            "total_users": total_users,
            "total_rewrites": stats.get("total_rewrites", 0) if stats else 0,
            "total_words_processed": stats.get("total_words", 0) if stats else 0,
            "active_database": "MongoDB Atlas"
        }
    except Exception as e: 
        return {"error": str(e)}

# ==========================================
# 💳 5. PLAN MANAGEMENT ROUTES
# ==========================================
class PlanModel(BaseModel):
    planId: str
    name: str
    price: int
    seo_words: int
    bypass_words: int
    features: list[str] = []
    sort_order: int = 99

@app.get("/api/plans")
async def get_plans():
    try:
        if plans_collection is not None:
            plans = list(plans_collection.find({}, {"_id": 0}))
            
            if not plans:
                default_plans = [
                    {"planId": "starter", "name": "Starter", "price": 17, "seo_words": 50000, "bypass_words": 25000, "features": ["Pass AI detection", "AI-powered rewriter", "Human quality content", "One click rewriting", "Sentence and phrase level rewriting"], "sort_order": 1},
                    {"planId": "power", "name": "Power", "price": 57, "seo_words": 3000000, "bypass_words": 250000, "features": ["Pass AI detection", "AI-powered rewriter", "Human quality content", "One click rewriting", "Bulk article rewriting", "API access"], "sort_order": 2},
                    {"planId": "enterprise", "name": "Enterprise", "price": 0, "seo_words": 9999999, "bypass_words": 9999999, "features": ["High volume usage", "Increased throughput", "White Labeled Integration", "Multiple user accounts", "Customized rewrites", "Account manager"], "sort_order": 3}
                ]
                plans_collection.insert_many(default_plans)
                plans = default_plans
            
            # 🚀 পজিশন অনুযায়ী সাজানো
            plans.sort(key=lambda x: x.get("sort_order", 99))
            return {"plans": plans}
        return {"plans": []}
    except Exception as e: 
        return {"error": str(e)}

@app.post("/api/admin/plans")
async def save_plan(req: PlanModel):
    if plans_collection is not None:
        plans_collection.update_one({"planId": req.planId}, {"$set": req.dict()}, upsert=True)
        return {"success": True}
    return {"error": "DB error"}

@app.delete("/api/admin/plans/{plan_id}")
async def delete_plan(plan_id: str):
    if plans_collection is not None:
        plans_collection.delete_one({"planId": plan_id})
        return {"success": True}
    return {"error": "DB error"}

# ==========================================
# 👥 6. USER MANAGEMENT ROUTES
# ==========================================
@app.get("/api/user/{user_id}")
async def get_user_data(user_id: str):
    if users_collection is not None:
        user = users_collection.find_one({"userId": user_id})
        if user: 
            return {
                "seo_words": user.get("seo_words", 50000), 
                "bypass_words": user.get("bypass_words", 25000), 
                "plan": user.get("plan", "Starter"), 
                "banned": user.get("banned", False)
            }
    return {"seo_words": 50000, "bypass_words": 25000, "plan": "Starter", "banned": False}

@app.get("/api/admin/users")
async def get_all_users():
    if users_collection is not None: 
        return {"users": list(users_collection.find({}, {"_id": 0}))}
    return {"users": []}

class AdminActionRequest(BaseModel):
    userId: str
    plan: str
    seo_words: int
    bypass_words: int
    banned: bool

@app.post("/api/admin/super-update")
async def super_update_user(req: AdminActionRequest):
    if users_collection is not None:
        users_collection.update_one(
            {"userId": req.userId}, 
            {"$set": {"plan": req.plan, "seo_words": req.seo_words, "bypass_words": req.bypass_words, "banned": req.banned}}
        )
        return {"success": True}
    return {"error": "DB Error"}

@app.delete("/api/admin/delete-user/{user_id}")
async def delete_user(user_id: str):
    if users_collection is not None:
        users_collection.delete_one({"userId": user_id})
        return {"success": True}
    return {"error": "DB error"}

# ==========================================
# ✍️ 7. CORE AI REWRITE ROUTE (With Word Limits)
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
        # 1. ইনপুট টেক্সটের শব্দ গণনা
        input_word_count = len(req.text.split())
        if input_word_count == 0: 
            return {"error": "Text cannot be empty."}

        target_limit_field = "seo_words" if req.mode == "rewrite" else "bypass_words"
        limit_name = "SEO Rewrite" if req.mode == "rewrite" else "AI Bypass"

        # 2. ইউজার ভেরিফিকেশন ও লিমিট চেক
        if users_collection is not None and req.userId != "guest":
            user = users_collection.find_one({"userId": req.userId})
            if not user:
                user = {"userId": req.userId, "seo_words": 50000, "bypass_words": 25000, "plan": "Starter", "banned": False}
                users_collection.insert_one(user)
            
            if user.get("banned", False) == True: 
                return {"error": "Your account has been banned by the administrator."}
            
            current_words_left = user.get(target_limit_field, 0)
            if current_words_left < input_word_count:
                return {"error": f"Limit Reached! You have {current_words_left} words left for {limit_name}, but your text has {input_word_count} words."}

        # 3. Gemini API Configuration
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: 
            return {"error": "API Key is missing!"}
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-pro"))
        
        # 4. প্রম্পট সিলেক্ট
        if req.mode == "avoid_ai":
            prompt = f'Expert AI Detection Bypass Specialist. Rewrite to score 100% human. Rules: High Burstiness. Text: "{req.text}". Bypass: {req.tone}. Return {req.num_rewrites} versions separated by |||VARIATION|||.' 
        else:
            prompt = f'Expert SEO Writer. Semantic SEO-optimized. Text: "{req.text}". Tone: {req.tone}. Return {req.num_rewrites} versions separated by |||VARIATION|||.'

        # 5. AI Generation
        response = model.generate_content(prompt)
        output = response.text
        variations = [v.strip() for v in output.split("|||VARIATION|||") if v.strip()]
        if not variations: 
            variations = [output.strip()]
            
        # 6. ডাটাবেস থেকে শব্দ কাটা
        words_left = "Unlimited"
        if users_collection is not None and req.userId != "guest":
            users_collection.update_one(
                {"userId": req.userId}, 
                {"$inc": {target_limit_field: -input_word_count}}
            )
            updated_user = users_collection.find_one({"userId": req.userId})
            words_left = updated_user.get(target_limit_field, 0)
        
        # 7. Analytics আপডেট
        if analytics_collection is not None:
            analytics_collection.update_one(
                {"_id": "global_stats"}, 
                {"$inc": {"total_rewrites": 1, "total_words": input_word_count}}, 
                upsert=True
            )
        
        return {"rewrites": variations[:req.num_rewrites], "words_left": words_left}
    
    except Exception as e: 
        return {"error": f"Backend Error: {str(e)}"}