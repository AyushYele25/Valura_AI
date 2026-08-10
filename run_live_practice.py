import urllib.request
import json
import sys
import time

SERVER_URL = "https://ai-arena.twocc.in"
API_KEY = "vlr_V7pE04PXx7FLI_yDGQZ66AKM3Jdvfwi9"
SERVICE_URL = "http://127.0.0.1:8080/answer"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def get_next_question():
    req = urllib.request.Request(f"{SERVER_URL}/v1/next", headers=headers)
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode())
    except Exception as e:
        print(f"Error fetching next question: {e}")
        return None

def answer_via_local_service(q_envelope):
    data = json.dumps(q_envelope).encode()
    req = urllib.request.Request(SERVICE_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode())
    except Exception as e:
        print(f"Error calling local service: {e}")
        return None

def submit_answer(answer_obj):
    data = json.dumps(answer_obj).encode()
    req = urllib.request.Request(f"{SERVER_URL}/v1/answer", data=data, headers=headers)
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode())
    except Exception as e:
        print(f"Error submitting answer: {e}")
        return None

def main():
    count = 0
    max_questions = 10  # Run a batch of 10 practice questions

    print(f"Starting practice evaluation against {SERVER_URL}...")
    while count < max_questions:
        q = get_next_question()
        if not q or "question_id" not in q:
            print("No more questions or error.")
            break

        count += 1
        print(f"\n--- Question {count} ({q['question_id']}) ---")
        print(f"Prompt: {q.get('prompt')}")
        print(f"Client ID: {q.get('client_id')}")

        start_t = time.time()
        ans = answer_via_local_service(q)
        elapsed = round(time.time() - start_t, 2)

        if not ans:
            print("Failed to get answer from local service!")
            continue

        print(f"Local Answer Value ({elapsed}s): {ans.get('answer_value')}")
        print(f"Local Answer Text: {str(ans.get('text'))[:120]}...")
        print(f"Agents Path: {ans.get('agents')}")
        print(f"Refusal Reason: {ans.get('reason')}")

        result = submit_answer(ans)
        print(f"Score / Feedback: {json.dumps(result, indent=2)}")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
