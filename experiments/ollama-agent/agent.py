import sys
from datetime import date

from ollama import chat

sys.stdin.reconfigure(errors="replace")
MODEL = "qwen3:1.7b"


def current_date() -> str:
    """Return today's date and weekday from the computer's clock."""
    today = date.today()
    return f"{today.isoformat()} ({today.strftime('%A')})"


TOOLS = {"current_date": current_date}

messages = [
    {"role": "system", "content": "You don't know today's date. Always use the tool, never guess."}
]

while True:
    try:
        user = input("you> ").strip()
    except EOFError:
        break
    if user.lower() == "exit":
        break
    messages.append({"role": "user", "content": user})
    while True:
        response = chat(model=MODEL, messages=messages, tools=list(TOOLS.values()), think=False)
        messages.append(response.message)
        if not response.message.tool_calls:
            print("agent>", response.message.content)
            break
        for call in response.message.tool_calls:
            fn = TOOLS.get(call.function.name)
            result = fn(**call.function.arguments) if fn else f"unknown tool {call.function.name}"
            print(f"[tool] {call.function.name} -> {result}")
            messages.append({"role": "tool", "tool_name": call.function.name, "content": str(result)})
