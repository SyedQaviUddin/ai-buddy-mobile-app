import requests

API_KEY = "sk-95762b21ef0342dc9fe40c19f671ab69"
API_URL = "https://api.deepseek.com/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def ask_deepseek(prompt):
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(API_URL, headers=HEADERS, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
