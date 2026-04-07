import logging
import litellm
from rich.console import Console
from config import GROQ_API_KEY, GOOGLE_AI_STUDIO_KEY

litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

console = Console()


async def ask_tick_model(prompt: str) -> str:
    try:
        response = await litellm.acompletion(
            model="gemini/gemma-3n-e2b-it",
            messages=[
                {
                    "role": "system",
                    "content": "You are a silent background coding agent. Respond with exactly one line: 'SLEEP', 'ACTION: <what to do>', or 'COMMENT: <pr_number>: <message>'. Nothing else."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=80,
            temperature=0.1,
            api_key=GOOGLE_AI_STUDIO_KEY,
        )
        text = response.choices[0].message.content
        return text.strip() if text else "SLEEP"
    except Exception as e:
        console.print(f"[red][auto-agent] tick model error:[/red] {e}")
        return "SLEEP"


async def ask_dream_model(prompt: str) -> str:
    try:
        response = await litellm.acompletion(
            model="groq/llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
            api_key=GROQ_API_KEY,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        console.print(f"[red][auto-agent] dream model error:[/red] {e}")
        return ""
