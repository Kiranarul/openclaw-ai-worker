import requests
import time
import os
import torch
from transformers import AutoProcessor, AutoModelForCausalLM

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

MODEL_ID = "Qwen/Qwen3.5-2B"

print("Loading model...")

HF_TOKEN = os.environ.get("HF_TOKEN")

processor = AutoProcessor.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

print("Model ready")


def get_task():
    try:

        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/claim_task",
            headers=HEADERS
        )

        print(f"Claim task response: {r.status_code}")
        data = r.json()
        print(f"Claim task data: {data}")

        if len(data) == 0:
            return None

        return data[0]

    except Exception as e:
        print("Error fetching task:", e)
        import traceback
        traceback.print_exc()
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

    print(f"Full task object: {task}")
    print(f"Task type: {type(task)}")

    # Safety check: ensure task is a dict
    if not isinstance(task, dict):
        print(f"ERROR: Task is not a dictionary! Got: {type(task)}")
        continue

    task_id = task["id"]
    prompt = task["prompt"]

    print(f"Task data type - id: {type(task_id)}, prompt: {type(prompt)}")
    print(f"Prompt value: {prompt}")
    
    # Safety check: ensure prompt is a string
    if not isinstance(prompt, str):
        print(f"WARNING: Prompt is not a string! Type: {type(prompt)}, Value: {prompt}")
        prompt = str(prompt)

    try:

        print(f"Generating response for prompt: {prompt[:100]}...")

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        )

        print(f"Input shape: {inputs['input_ids'].shape}")

        outputs = model.generate(**inputs, max_new_tokens=200)

        print(f"Output shape: {outputs.shape}")

        result = processor.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        )

        print(f"Generated result: {result[:200]}")

    except Exception as e:
        import traceback
        result = f"Execution error: {str(e)}"
        print("ERROR:", result)
        traceback.print_exc()

    submit_result(task_id, result)

    print("Task completed:", task_id)