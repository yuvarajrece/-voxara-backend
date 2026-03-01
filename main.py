from fastapi import FastAPI, HTTPException, Header, Depends
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
import certifi
import os

load_dotenv()

app = FastAPI(title="Voxara NBFC Backend")

# Fixed MongoDB Atlas Connection with SSL
client = MongoClient(
    os.getenv("MONGO_URI"),
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["nbfc_updates"]
collection = db["daily_updates"]
missed_collection = db["missed_calls"]

API_KEY = os.getenv("API_KEY")


# Auth Check
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# Schema
class DailyUpdate(BaseModel):
    employee_name: str
    visits_count: int
    visit_summary: str
    has_query: str
    employee_query: Optional[str] = None
    tomorrow_goal: str


class MissedCall(BaseModel):
    phone_number: str
    reason: Optional[str] = "Employee unavailable"


# Save completed call
@app.post("/api/save-update")
def save_update(data: DailyUpdate, auth=Depends(verify_api_key)):
    record = {
        "employee_name": data.employee_name,
        "visits_count": data.visits_count,
        "visit_summary": data.visit_summary,
        "has_query": data.has_query,
        "employee_query": data.employee_query if data.has_query == "Yes" else None,
        "tomorrow_goal": data.tomorrow_goal,
        "call_status": "completed",
        "call_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "created_at": datetime.utcnow()
    }
    result = collection.insert_one(record)
    return {
        "success": True,
        "message": "Saved to MongoDB Atlas",
        "id": str(result.inserted_id)
    }


# Save missed call
@app.post("/api/missed-call")
def missed_call(data: MissedCall, auth=Depends(verify_api_key)):
    record = {
        "phone_number": data.phone_number,
        "reason": data.reason,
        "call_status": "missed",
        "call_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "created_at": datetime.utcnow()
    }
    missed_collection.insert_one(record)
    return {"success": True, "message": "Missed call logged"}


# Get all updates
@app.get("/api/updates")
def get_all_updates(auth=Depends(verify_api_key)):
    updates = list(collection.find({}, {"_id": 0}))
    return {"success": True, "total": len(updates), "data": updates}


# Get flagged queries
@app.get("/api/queries")
def get_flagged_queries(auth=Depends(verify_api_key)):
    queries = list(collection.find(
        {"has_query": "Yes"},
        {"_id": 0, "employee_name": 1, "employee_query": 1, "call_date": 1}
    ))
    return {"success": True, "total": len(queries), "data": queries}


# Get missed calls
@app.get("/api/missed-calls")
def get_missed_calls(auth=Depends(verify_api_key)):
    missed = list(missed_collection.find({}, {"_id": 0}))
    return {"success": True, "total": len(missed), "data": missed}
class CallSummary(BaseModel):
    summary: str

@app.post("/api/save-summary")
def save_summary(data: CallSummary, auth=Depends(verify_api_key)):
    record = {
        "summary": data.summary,
        "created_at": datetime.utcnow()
    }
    db["call_summaries"].insert_one(record)
    return {
        "success": True,
        "message": "Summary saved"
    }

# Health check
@app.get("/")
def root():
    return {"status": "Voxara NBFC Backend Running"}

