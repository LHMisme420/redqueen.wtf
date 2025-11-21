from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import json
import os
from typing import Dict

app = FastAPI()

class SwarmRequest(BaseModel):
    target_model: str
    budget_flops: float = 1e23

@app.post("/run")
async def run_swarm(request: SwarmRequest):
    # Call the swarm_runner as subprocess (or integrate directly)
    cmd = [
        "python", "swarm_runner.py",
        "--target", request.target_model,
        "--budget-flops", str(request.budget_flops)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/app")
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)
        
        # Parse report.json
        with open("report.json", "r") as f:
            report = json.load(f)
        
        return {
            "status": "success",
            "lethality_score": report.get("lethality"),
            "model": report.get("model"),
            "total_attacks": report.get("total_attacks"),
            "report": report  # Full deets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
