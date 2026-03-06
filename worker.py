import requests
import subprocess
import time
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

MODEL_PATH = "models/model.gguf"
LLAMA_PATH = "./llama.cpp/build/bin/llama-cli"


def get_task():
    try:
        url = f"{SUPABASE_URL}/rest/v1/tasks?status=eq.pending&limit=1"
        r = requests.get(url, headers=HEADERS)
        data = r.json()

        if len(data) == 0:
            return None

        return data[0]

    except Exception as e:
        print("Error fetching task:", e)
        return None


def mark_running(task_id):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}"
    requests.patch(url, headers=HEADERS, json={"status": "running"})


def submit_result(task_id, result):
    url = f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}"
    requests.patch(
        url,
        headers=HEADERS,
        json={
            "status": "done",
            "result": result
        }
    )


print("Worker started")

while True:

    task = get_task()

    if not task:
        print("No tasks, sleeping...")
        time.sleep(5)
        continue

    task_id = task["id"]
    prompt = task["prompt"]

    print("Processing task:", task_id)

    mark_running(task_id)

    try:
        result = subprocess.run(
            [
                LLAMA_PATH,
                "-m", MODEL_PATH,
                "-p", prompt,
                "-n", "512"
            ],
            capture_output=True,
            text=True
        )

        output = result.stdout

    except Exception as e:
        output = f"Execution error: {str(e)}"

    submit_result(task_id, output)

    print("Task completed:", task_id)