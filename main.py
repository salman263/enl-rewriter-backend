import os
import random
import string
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException
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
saved_articles_collection = db["saved_articles"] if db is not None else None 

@app.get("/")
def read_root(): 
    return {"message": "ZeroWordAi Backend (With Strict Prompting & Developer API)"}

# ==========================================
# 📧 3. USER EMAIL SYNC & API KEY GENERATION
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
                update_data = {"email": req.email}
                # 🚀 Generate API key if not exists
                if "api_key" not in user:
                    update_data["api_key"] = f"sk-live-{uuid.uuid4().hex}"
                users_collection.update_one({"userId": req.userId}, {"$set": update_data})
            else:
                users_collection.insert_one({
                    "userId": req.userId, 
                    "email": req.email, 
                    "seo_words": 5000, 
                    "bypass_words": 1000, 
                    "plan": "Free", 
                    "banned": False,
                    "expiry_date": None,
                    "api_key": f"sk-live-{uuid.uuid4().hex}" # 🚀 Initial API Key
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
# 🎁 6. COUPON GENERATE, REDEEM & DELETE
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
            if not plan: return {"error": "Plan not found!"}

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
                    "is_used": False, "used_by": None, 
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

@app.delete("/api/admin/coupons/{code}")
async def delete_coupon(code: str):
    if coupons_collection is not None:
        coupons_collection.delete_one({"code": code})
        return {"success": True}
    return {"error": "DB error"}

@app.delete("/api/admin/coupons-bulk")
async def bulk_delete_coupons():
    if coupons_collection is not None:
        coupons_collection.delete_many({})
        return {"success": True}
    return {"error": "DB error"}

class RedeemCouponReq(BaseModel):
    userId: str
    code: str

@app.post("/api/redeem-coupon")
async def redeem_coupon(req: RedeemCouponReq):
    try:
        if coupons_collection is not None and users_collection is not None:
            coupon = coupons_collection.find_one({"code": req.code, "is_used": False})
            if not coupon:
                return {"error": "Invalid or already used promo code!"}
            
            coupons_collection.update_one({"code": req.code}, {"$set": {"is_used": True, "used_by": req.userId}})
            
            duration = coupon.get("duration_days", 30)
            expiry_date = None
            if duration > 0:
                expiry_date = (datetime.now() + timedelta(days=duration)).isoformat()

            users_collection.update_one(
                {"userId": req.userId}, 
                {"$set": {
                    "plan": coupon["plan_name"],
                    "seo_words": coupon["seo_words"],
                    "bypass_words": coupon["bypass_words"],
                    "expiry_date": expiry_date
                }}
            )
            return {"success": True}
        return {"error": "Database error"}
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 💾 7. SAVED ARTICLES ROUTES
# ==========================================
class SaveArticleReq(BaseModel):
    userId: str
    original_text: str
    rewritten_text: str
    mode: str

@app.post("/api/saved-articles")
async def save_article(req: SaveArticleReq):
    try:
        if saved_articles_collection is not None:
            article = {
                "articleId": str(uuid.uuid4()),
                "userId": req.userId,
                "original_text": req.original_text,
                "rewritten_text": req.rewritten_text,
                "mode": req.mode,
                "created_at": datetime.now().isoformat()
            }
            saved_articles_collection.insert_one(article)
            return {"success": True}
        return {"error": "DB error"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/saved-articles/{user_id}")
async def get_saved_articles(user_id: str):
    if saved_articles_collection is not None:
        articles = list(saved_articles_collection.find({"userId": user_id}, {"_id": 0}).sort("created_at", -1))
        return {"articles": articles}
    return {"articles": []}

@app.delete("/api/saved-articles/{article_id}")
async def delete_saved_article(article_id: str):
    if saved_articles_collection is not None:
        saved_articles_collection.delete_one({"articleId": article_id})
        return {"success": True}
    return {"error": "DB error"}

# ==========================================
# 👥 8. USER MANAGEMENT & API KEY ROUTES
# ==========================================
@app.get("/api/user/{user_id}")
async def get_user_data(user_id: str):
    if users_collection is not None:
        user = users_collection.find_one({"userId": user_id})
        if user: 
            # 🚀 Ensure existing users get an API key if they check their profile
            if "api_key" not in user:
                new_key = f"sk-live-{uuid.uuid4().hex}"
                users_collection.update_one({"userId": user_id}, {"$set": {"api_key": new_key}})
                user["api_key"] = new_key

            return {
                "seo_words": user.get("seo_words", 5000), 
                "bypass_words": user.get("bypass_words", 1000), 
                "plan": user.get("plan", "Free"), 
                "banned": user.get("banned", False),
                "api_key": user.get("api_key", ""), # 🚀 Return API Key to frontend
                "expiry_date": user.get("expiry_date")
            }
    return {"seo_words": 5000, "bypass_words": 1000, "plan": "Free", "banned": False, "api_key": ""}

# 🚀 NEW: Route to regenerate API Key from dashboard
@app.post("/api/user/{user_id}/regenerate-key")
async def regenerate_api_key(user_id: str):
    if users_collection is not None:
        new_key = f"sk-live-{uuid.uuid4().hex}"
        result = users_collection.update_one({"userId": user_id}, {"$set": {"api_key": new_key}})
        if result.modified_count > 0:
            return {"success": True, "api_key": new_key}
    return {"error": "User not found or DB error"}

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
# ✍️ 9. CORE AI REWRITE ROUTE (Internal Dashboard)
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
                user = {"userId": req.userId, "seo_words": 5000, "bypass_words": 1000, "plan": "Free", "banned": False}
                users_collection.insert_one(user)
            
            if user.get("banned", False) == True: 
                return {"error": "Your account has been banned."}
            
            current_words_left = user.get(target_limit_field, 0)
            if current_words_left < input_word_count:
                return {"error": f"Limit Reached! You have {current_words_left} words left for {limit_name}."}

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: 
            return {"error": "API Key is missing!"}
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-pro"))
        
        if req.mode == "avoid_ai":
            prompt = f'Act as an expert human writer. Rewrite the text to bypass AI detection (100% human score). Rules: 1. Maintain the exact same paragraph structure as the original text. 2. DO NOT use any markdown formatting (no #, no *, no **). Output plain text only. Text: "{req.text}". Tone: {req.tone}. Return exactly {req.num_rewrites} versions separated by |||VARIATION|||.' 
        else:
            prompt = f'Act as an expert SEO writer. Rewrite the text for semantic SEO. Rules: 1. Maintain the exact same paragraph structure as the original text. 2. DO NOT use any markdown formatting (no #, no *, no **). Output plain text only. Text: "{req.text}". Tone: {req.tone}. Return exactly {req.num_rewrites} versions separated by |||VARIATION|||.'

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

# ==========================================
# 🌐 10. EXTERNAL DEVELOPER API ROUTE (/api/v1/rewrite)
# ==========================================
class ExternalApiRequest(BaseModel):
    text: str
    mode: str = "rewrite" # rewrite or avoid_ai
    tone: str = "Regular"

@app.post("/api/v1/rewrite")
async def external_api_rewrite(req: ExternalApiRequest, authorization: str = Header(None)):
    try:
        # 1. Validate API Key
        if not authorization or not authorization.startswith("Bearer "):
            return {"error": "Unauthorized. Missing or invalid Bearer token."}
            
        api_key_extracted = authorization.split("Bearer ")[1].strip()
        if not users_collection:
            return {"error": "Database connection error"}
            
        user = users_collection.find_one({"api_key": api_key_extracted})
        if not user:
            return {"error": "Invalid API Key. Please check your dashboard."}
            
        if user.get("banned", False):
            return {"error": "Account suspended. Please contact support."}

        # 2. Check Word Limits
        input_word_count = len(req.text.split())
        target_limit_field = "seo_words" if req.mode == "rewrite" else "bypass_words"
        limit_name = "SEO Rewrite" if req.mode == "rewrite" else "AI Bypass"
        
        current_words_left = user.get(target_limit_field, 0)
        if current_words_left < input_word_count:
            return {"error": f"Insufficient balance. You have {current_words_left} words left for {limit_name}."}

        # 3. Process AI Generation
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-pro"))
        
        if req.mode == "avoid_ai":
            prompt = f'Act as an expert human writer. Rewrite the text to bypass AI detection (100% human score). Rules: 1. Maintain the exact same paragraph structure. 2. Output plain text only (no markdown). Text: "{req.text}". Tone: {req.tone}.' 
        else:
            prompt = f'Act as an expert SEO writer. Rewrite the text for semantic SEO. Rules: 1. Maintain the exact same paragraph structure. 2. Output plain text only (no markdown). Text: "{req.text}". Tone: {req.tone}.'

        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # 4. Deduct Words & Update Stats
        users_collection.update_one({"userId": user["userId"]}, {"$inc": {target_limit_field: -input_word_count}})
        analytics_collection.update_one({"_id": "global_stats"}, {"$inc": {"total_rewrites": 1, "total_words": input_word_count}}, upsert=True)

        return {
            "success": True,
            "original_words": input_word_count,
            "rewritten_text": result_text,
            "words_remaining": current_words_left - input_word_count
        }

    except Exception as e:
        return {"error": f"API Error: {str(e)}"}