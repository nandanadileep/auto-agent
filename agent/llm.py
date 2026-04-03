import litellm
from rich.console import Console
from config import GROQ_API_KEY, OLLAMA_BASE_URL

litellm.api_base = OLLAMA_BASE_URL
console = Console()


async def ask_tick_model(prompt: str) -> str:
    try:
        response = await litellm.acompletion(
            model="ollama/gemma4:e2b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a silent background coding agent. Respond with exactly one line: either 'SLEEP' or 'ACTION: <what to do>'. Nothing else."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=50,
            temperature=0.1,
            api_base="http://localhost:11434",
        )
        console.print(f"[dim]raw litellm response: {response}[/dim]")
        text = response.choices[0].message.content
        return text.strip() if text else "SLEEP"
    except Exception as e:
        console.print(f"[red][kairos] tick model error:[/red] {e}")
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
        console.print(f"[red][kairos] dream model error:[/red] {e}")
        return ""
