import requests
import json
import os

ARWEAVE_GATEWAY = "https://arweave.net/tx"

def upload_to_arweave(data: dict, wallet_path: str = None):
    if not wallet_path:
        wallet_path = os.getenv("ARWEAVE_WALLET")
    with open(wallet_path) as f:
        wallet = json.load(f)
    
    payload = json.dumps(data)
    tx = {"data": payload.encode(), "wallet": wallet}
    resp = requests.post(ARWEAVE_GATEWAY, json=tx)
    if resp.status_code == 200:
        tx_id = resp.json().get("id")
        print(f"Uploaded: https://arweave.net/{tx_id}")
        return tx_id
    else:
        raise ValueError(f"Upload failed: {resp.text}")

if __name__ == "__main__":
    sample = {"test": "Red Queen lives"}
    upload_to_arweave(sample)
