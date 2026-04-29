"""Spike: verify Anthropic SDK connection."""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "Reply with exactly: ContentLoop spike OK"}
    ],
)

print(msg.content[0].text)
print(f"\nmodel={msg.model}  input_tokens={msg.usage.input_tokens}  output_tokens={msg.usage.output_tokens}")
