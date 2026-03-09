import requests
import time
import os
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

MODEL_ID = "Qwen/Qwen3.5-2B"

print("Loading model...")

processor = AutoProcessor.from_pretrained(MODEL_ID)

model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    device_map="cpu"
)

print("Model ready")


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

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        )

        outputs = model.generate(**inputs, max_new_tokens=200)

        result = processor.decode(
            outputs[0][inputs["input_ids"].shape[-1]:]
        )

    except Exception as e:
        result = f"Execution error: {str(e)}"

    submit_result(task_id, result)

    print("Task completed:", task_id)