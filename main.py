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

# Gemini AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# MongoDB Setup
client = MongoClient(os.environ.get("MONGO_URI"))
db = client["zerowordai"]
users_collection = db["users"]

# Request Model
class RewriteRequest(BaseModel):
    text: str
    tone: str
    num_rewrites: int = 1
    mode: str = "rewrite"
    userId: str

@app.post("/api/rewrite")
async def rewrite_text(req: RewriteRequest):
    # 1. Check User in Database
    user = users_collection.find_one({"userId": req.userId})
    if not user:
        user = {"userId": req.userId, "credits": 5}
        users_collection.insert_one(user)
    
    # 2. Check Credits
    if user["credits"] <= 0:
        return {"error": "No credits left! Please upgrade your plan."}

    # 3. 🚀 THE MAGIC: Prompt Selection based on Mode
    if req.mode == "avoid_ai":
        # 🛡️ Humanizer Prompt (AI Detection Bypass)
        prompt = f"""You are an expert human writer and copywriter. Your task is to rewrite the following text so that it completely bypasses all AI detectors (like ZeroGPT, Turnitin, Originality.ai).
        
        Follow these strict rules to make it 100% human-like:
        1. Use high 'burstiness' (mix very short, punchy sentences with longer, flowing ones).
        2. Use high 'perplexity' (use natural, conversational vocabulary; avoid highly predictable word sequences).
        3. Do NOT use typical AI buzzwords (e.g., delve, testament, tapestry, crucial, transformative, landscape, realm, unlock, dive).
        4. Add a slight conversational tone and occasional natural human phrasing.
        
        Bypass Strength: {req.tone}.
        
        Please provide exactly {req.num_rewrites} different variations of the rewritten text.
        Separate each variation using EXACTLY this text: "|||VARIATION|||". Do not add numbers like "Variation 1".
        
        Original Text:
        {req.text}
        """
    else:
        # ✏️ Standard Rewrite Prompt
        prompt = f"""You are an expert SEO content rewriter. Rewrite the following text to be unique, engaging, and highly readable.
        Tone: {req.tone}.
        
        Please provide exactly {req.num_rewrites} different distinct variations.
        Separate each variation using EXACTLY this text: "|||VARIATION|||". Do not add numbers like "Variation 1".
        
        Original Text:
        {req.text}
        """

    # 4. Generate Content with Gemini
    try:
        response = model.generate_content(prompt)
        output = response.text
        
        # 5. Split Variations
        variations = [v.strip() for v in output.split("|||VARIATION|||") if v.strip()]
        
        if not variations:
            variations = [output.strip()]
            
        # 6. Deduct 1 Credit
        users_collection.update_one(
            {"userId": req.userId},
            {"$inc": {"credits": -1}}
        )
        
        # 7. Get Updated Credits
        updated_user = users_collection.find_one({"userId": req.userId})
        
        return {
            "rewrites": variations[:req.num_rewrites],
            "credits_left": updated_user["credits"]
        }
        
    except Exception as e:
        return {"error": f"Failed to generate text: {str(e)}"}