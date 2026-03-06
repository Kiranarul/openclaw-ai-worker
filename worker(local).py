import requests
import subprocess
import time
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def get_task():
    url = f"{SUPABASE_URL}/rest/v1/tasks?status=eq.pending&limit=1"
    r = requests.get(url, headers=headers)
    data = r.json()
    return data[0] if data else None

def mark_running(task_id):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}"
    requests.patch(url, headers=headers, json={"status":"running"})

def submit_result(task_id, result):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}"
    requests.patch(url, headers=headers, json={
        "status":"done",
        "result":result
    })

print("Worker started...")

while True:

    task = get_task()

    if not task:
        print("No task, sleeping...")
        time.sleep(5)
        continue

    task_id = task["id"]
    prompt = task["prompt"]

    print("Running task:", task_id)

    mark_running(task_id)

    result = subprocess.run(
        ["ollama","run","qwen2.5-coder:3b",prompt],
        capture_output=True,
        text=True
    )

    submit_result(task_id, result.stdout)

    print("Task completed:", task_id)