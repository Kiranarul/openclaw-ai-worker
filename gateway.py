from fastapi import FastAPI, Request
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = FastAPI()

SUPABASE_URL = "https://rswmaifnuvsctckedvjf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzd21haWZudXZzY3Rja2VkdmpmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mjc4MzI2MCwiZXhwIjoyMDg4MzU5MjYwfQ.KxJaPlLbj8jE6qE47-gHqW0T7HMS-s0B-3CA0fpAB-U"

# Create session with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def create_task(prompt):

    print(f"Creating task with prompt type: {type(prompt)}")
    print(f"Prompt value: {prompt}")

    r = session.post(
        f"{SUPABASE_URL}/rest/v1/tasks",
        headers=HEADERS,
        json={"prompt": prompt},
        timeout=30
    )

    if r.status_code not in [200,201]:
        raise Exception(r.text)

    return r.json()[0]["id"]


def wait_for_result(task_id):

    while True:

        try:
            r = session.get(
                f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}",
                headers=HEADERS,
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            time.sleep(2)
            continue

        data = r.json()

        if not data:
            time.sleep(1)
            continue

        task = data[0]

        if task["status"] == "done":
            return task["result"]

        time.sleep(1)


def build_prompt(messages):

    prompt = ""

    # Check if messages is a list of message objects
    if isinstance(messages, list):
        for m in messages:
            if isinstance(m, dict):
                # Check if it's OpenClaw format: {'type': 'text', 'text': '...'}
                if 'type' in m and 'text' in m:
                    prompt += f"{m['text']}\n"
                # Check if it's standard chat format: {'role': 'user', 'content': '...'}
                elif 'role' in m and 'content' in m:
                    role = m.get("role","user")
                    content = m.get("content","")
                    prompt += f"{role.upper()}: {content}\n"
                else:
                    # Unknown dict format, convert to string
                    prompt += f"{str(m)}\n"
            else:
                # If message is already a string
                prompt += f"{str(m)}\n"
    else:
        # If messages is not a list, use it directly
        prompt = str(messages)

    return prompt


@app.post("/v1/chat/completions")
async def chat(req: Request):

    data = await req.json()

    messages = data.get("messages", [])

    print(f"Received messages type: {type(messages)}")
    print(f"Messages: {messages}")

    prompt = build_prompt(messages)

    print(f"Built prompt type: {type(prompt)}")
    print(f"Prompt: {prompt[:100]}...")

    task_id = create_task(prompt)

    result = wait_for_result(task_id)

    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result
                },
                "finish_reason": "stop"
            }
        ]
    }