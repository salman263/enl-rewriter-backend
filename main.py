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

MONGO_URI = os.environ.get("MONGO_URI")
client_mongo = MongoClient(MONGO_URI) if MONGO_URI else None
db = client_mongo["zerowordai"] if client_mongo else None
users_collection = db["users"] if db is not None else None

@app.get("/")
def read_root():
    return {"message": "AI Backend with Ultimate Admin Control is running!"}

# 1. 🔍 Get User Data
@app.get("/api/user/{user_id}")
async def get_user_data(user_id: str):
    try:
        if users_collection is not None:
            user = users_collection.find_one({"userId": user_id})
            if user:
                return {
                    "credits": user.get("credits", 5),
                    "plan": user.get("plan", "Free"),
                    "banned": user.get("banned", False)
                }
        return {"credits": 5, "plan": "Free", "banned": False}
    except Exception as e:
        return {"error": str(e)}

# 2. 👑 Get All Users
@app.get("/api/admin/users")
async def get_all_users():
    try:
        if users_collection is not None:
            all_users = list(users_collection.find({}, {"_id": 0}))
            return {"users": all_users}
        return {"users": []}
    except Exception as e:
        return {"error": str(e)}

# 3. 💳 Update Plan from Pricing Page
class PlanUpgradeRequest(BaseModel):
    userId: str
    plan: str
    credits: int

@app.post("/api/admin/upgrade-plan")
async def upgrade_plan(req: PlanUpgradeRequest):
    if users_collection is not None:
        users_collection.update_one({"userId": req.userId}, {"$set": {"plan": req.plan, "credits": req.credits}})
        return {"success": True}
    return {"error": "DB not connected"}

# 4. 🚀 ULTIMATE ADMIN ACTION ROUTE (Set Credits, Ban, Unban)
class AdminActionRequest(BaseModel):
    userId: str
    plan: str
    credits: int
    banned: bool

@app.post("/api/admin/super-update")
async def super_update_user(req: AdminActionRequest):
    try:
        if users_collection is not None:
            users_collection.update_one(
                {"userId": req.userId},
                {"$set": {"plan": req.plan, "credits": req.credits, "banned": req.banned}}
            )
            return {"success": True, "message": "User updated successfully!"}
        return {"error": "Database not connected"}
    except Exception as e:
        return {"error": str(e)}

# 5. 🗑️ DELETE USER ROUTE
@app.delete("/api/admin/delete-user/{user_id}")
async def delete_user(user_id: str):
    try:
        if users_collection is not None:
            users_collection.delete_one({"userId": user_id})
            return {"success": True, "message": "User deleted!"}
        return {"error": "DB error"}
    except Exception as e:
        return {"error": str(e)}

# 6. ✍️ REWRITE ROUTE (With Ban Protection)
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
            
            # 🚨 BAN CHECK
            if user.get("banned", False) == True:
                return {"error": "Your account has been banned by the administrator. Contact support."}

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
        
        return {"rewrites": variations[:req.num_rewrites], "credits_left": credits_left}
    except Exception as e:
        return {"error": f"Backend Error: {str(e)}"}