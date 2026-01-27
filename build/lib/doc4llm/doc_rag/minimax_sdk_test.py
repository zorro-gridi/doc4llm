import os
import dotenv
dotenv.load_dotenv()

import anthropic

client = anthropic.Anthropic()

system_prompt = """

"""

message = client.messages.create(
    model="MiniMax-M2.1",
    max_tokens=20000,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "如何创建 ray cluster 和 opencode skills? "
                }
            ]
        }
    ]
)

for block in message.content:
    if block.type == "thinking":
        print(f"Thinking:\n{block.thinking}\n")
    elif block.type == "text":
        print(f"Text:\n{block.text}\n")