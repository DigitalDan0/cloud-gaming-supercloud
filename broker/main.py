from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn
import asyncio
from .settings import settings
from .lease_manager import LeaseManager, LeaseInfo
from .billing import BillingManager

app = FastAPI(title="Cloud Gaming Broker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

lease_manager = LeaseManager()
billing_manager = BillingManager()

class SessionRequest(BaseModel):
    hours: int = 1
    payment_method: str = "stripe"

class SessionResponse(BaseModel):
    session_id: str
    moonlight_host: str
    moonlight_port: int
    status: str
    expires_at: Optional[str] = None
    payment_info: Optional[Dict] = None

@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionRequest, background_tasks: BackgroundTasks):
    """Create a new cloud gaming session"""
    try:
        # Estimate cost
        cost_estimate = billing_manager.estimate_session_cost(request.hours)
        
        # Create payment intent
        payment_info = billing_manager.create_payment_intent(request.hours)
        
        # Create Akash lease
        lease_info = lease_manager.create_lease()
        
        # In production, would wait for payment confirmation
        # For now, simulate immediate success
        
        return SessionResponse(
            session_id=lease_info.lease_id,
            moonlight_host=lease_info.ip_address,
            moonlight_port=lease_info.port,
            status="provisioning",
            payment_info={
                "client_secret": payment_info["client_secret"],
                "estimated_cost": cost_estimate
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session status"""
    try:
        status = lease_manager.get_lease_status(session_id)
        if not status:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"session_id": session_id, "status": status}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """Close a gaming session"""
    try:
        success = lease_manager.close_lease(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session closed successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "cloud-gaming-broker"}

if __name__ == "__main__":
    try:
        settings.validate()
        uvicorn.run(
            "main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=True
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)