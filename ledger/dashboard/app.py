from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="."), create_index=False)

@app.get("/", response_class=HTMLResponse)
def leaderboard():
    data = [
        {"model": "Llama-3.1-405B", "params": 405000000000, "lethality": 12.7, "worst": "DAN Jailbreak", "date": "2025-11-21"},
        {"model": "Qwen2-72B", "params": 72000000000, "lethality": 8.4, "worst": "Data Exfil", "date": "2025-11-21"}
    ]
    html = """
    <html><body>
    <h1>Red Queen Leaderboard</h1>
    <table border="1">
    <tr><th>Model</th><th>Params</th><th>Lethality %</th><th>Worst Attack</th><th>Date</th></tr>
    """
    for row in data:
        color = "red" if row["lethality"] > 5 else "yellow" if row["lethality"] > 1 else "green"
        html += f'<tr><td>{row["model"]}</td><td>{row["params"]:,}</td><td style="color:{color}">{row["lethality"]}</td><td>{row["worst"]}</td><td>{row["date"]}</td></tr>'
    html += "</table></body></html>"
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
