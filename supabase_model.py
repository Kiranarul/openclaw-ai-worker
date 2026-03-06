import requests
import time

SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SERVICE_ROLE_KEY"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def generate(prompt):

    # 1 insert task
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/tasks",
        headers=headers,
        json={"prompt": prompt}
    )

    task_id = r.json()[0]["id"]

    # 2 wait for result
    while True:

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}",
            headers=headers
        )

        data = res.json()[0]

        if data["status"] == "done":
            return data["result"]

        time.sleep(2)