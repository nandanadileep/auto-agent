import litellm
from config import GROQ_API_KEY, OLLAMA_BASE_URL

litellm.api_base = OLLAMA_BASE_URL


async def ask_tick_model(prompt: str) -> str:
    try:
        response = await litellm.acompletion(
            model="ollama/gemma4:e2b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
            api_base=OLLAMA_BASE_URL,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        from rich.console import Console
        Console().print(f"[red][kairos] tick model error:[/red] {e}")
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
        from rich.console import Console
        Console().print(f"[red][kairos] dream model error:[/red] {e}")
        return ""
