import os
import random
import string
from datetime import datetime
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

users_collection = db["users"] if db is not None else None
plans_collection = db["plans"] if db is not None else None
analytics_collection = db["analytics"] if db is not None else None
coupons_collection = db["coupons"] if db is not None else None 

@app.get("/")
def read_root(): 
    return {"message": "ZeroWordAi Ultimate Backend is running smoothly!"}

# ==========================================
# 📧 3. USER EMAIL SYNC ROUTE
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
                users_collection.update_one({"userId": req.userId}, {"$set": {"email": req.email}})
            else:
                users_collection.insert_one({
                    "userId": req.userId, 
                    "email": req.email, 
                    "seo_words": 50000, 
                    "bypass_words": 25000, 
                    "plan": "Starter", 
                    "banned": False,
                    "expiry_date": None
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
    duration_days: int = 30

@app.get("/api/plans")
async def get_plans():
    try:
        if plans_collection is not None:
            plans = list(plans_collection.find({}, {"_id": 0}))
            if not plans:
                default_plans = [
                    {"planId": "starter", "name": "Starter", "price": 17, "seo_words": 50000, "bypass_words": 25000, "features": ["Pass AI detection"], "sort_order": 1, "duration_days": 30},
                    {"planId": "power", "name": "Power", "price": 57, "seo_words": 3000000, "bypass_words": 250000, "features": ["API access"], "sort_order": 2, "duration_days": 30}
                ]
                plans_collection.insert_many(default_plans)
                plans = default_plans
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
# 🎁 6. COUPON MANAGEMENT (AppSumo)
# ==========================================
class GenerateCouponReq(BaseModel):
    plan_name: str
    count: int
    prefix: str = "SUMO"

@app.post("/api/admin/generate-coupons")
async def generate_coupons(req: GenerateCouponReq):
    try:
        if coupons_collection is not None and plans_collection is not None:
            plan = plans_collection.find_one({"name": req.plan_name})
            if not plan: 
                return {"error": "Plan not found!"}

            new_coupons = []
            for _ in range(req.count):
                random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                full_code = f"{req.prefix.upper()}-{random_code}"
                new_coupons.append({
                    "code": full_code, 
                    "plan_name": req.plan_name, 
                    "seo_words": plan.get("seo_words", 0), 
                    "bypass_words": plan.get("bypass_words", 0),
                    "duration_days": plan.get("duration_days", 30),
                    "is_used": False, 
                    "used_by": None, 
                    "created_at": datetime.now().isoformat()
                })
            
            coupons_collection.insert_many(new_coupons)
            return {"success": True, "generated": req.count}
        return {"error": "DB Error"}
    except Exception as e: 
        return {"error": str(e)}

@app.get("/api/admin/coupons")
async def get_coupons():
    if coupons_collection is not None:
        coupons = list(coupons_collection.find({}, {"_id": 0}).sort("created_at", -1))
        return {"coupons": coupons}
    return {"coupons": []}

# ==========================================
# 👥 7. USER MANAGEMENT ROUTES
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
                "banned": user.get("banned", False),
                "expiry_date": user.get("expiry_date")
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
# ✍️ 8. CORE AI REWRITE ROUTE
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
        input_word_count = len(req.text.split())
        if input_word_count == 0: 
            return {"error": "Text cannot be empty."}

        target_limit_field = "seo_words" if req.mode == "rewrite" else "bypass_words"
        limit_name = "SEO Rewrite" if req.mode == "rewrite" else "AI Bypass"

        if users_collection is not None and req.userId != "guest":
            user = users_collection.find_one({"userId": req.userId})
            if not user:
                user = {"userId": req.userId, "seo_words": 50000, "bypass_words": 25000, "plan": "Starter", "banned": False}
                users_collection.insert_one(user)
            
            if user.get("banned", False) == True: 
                return {"error": "Your account has been banned."}
            
            current_words_left = user.get(target_limit_field, 0)
            if current_words_left < input_word_count:
                return {"error": f"Limit Reached! You have {current_words_left} words left for {limit_name}, but your text has {input_word_count} words."}

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: 
            return {"error": "API Key is missing!"}
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-pro"))
        
        if req.mode == "avoid_ai":
            prompt = f'Expert AI Detection Bypass Specialist. Rewrite to score 100% human. Rules: High Burstiness. Text: "{req.text}". Bypass: {req.tone}. Return {req.num_rewrites} versions separated by |||VARIATION|||.' 
        else:
            prompt = f'Expert SEO Writer. Semantic SEO-optimized. Text: "{req.text}". Tone: {req.tone}. Return {req.num_rewrites} versions separated by |||VARIATION|||.'

        response = model.generate_content(prompt)
        output = response.text
        variations = [v.strip() for v in output.split("|||VARIATION|||") if v.strip()]
        if not variations: 
            variations = [output.strip()]
            
        words_left = "Unlimited"
        if users_collection is not None and req.userId != "guest":
            users_collection.update_one(
                {"userId": req.userId}, 
                {"$inc": {target_limit_field: -input_word_count}}
            )
            updated_user = users_collection.find_one({"userId": req.userId})
            words_left = updated_user.get(target_limit_field, 0)
        
        if analytics_collection is not None:
            analytics_collection.update_one(
                {"_id": "global_stats"}, 
                {"$inc": {"total_rewrites": 1, "total_words": input_word_count}}, 
                upsert=True
            )
        
        return {"rewrites": variations[:req.num_rewrites], "words_left": words_left}
    
    except Exception as e: 
        return {"error": f"Backend Error: {str(e)}"}