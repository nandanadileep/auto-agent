from agent.llm import ask_dream_model
from memory.daily_log import get_todays_log
from memory.memory_md import read_memory_md, write_memory_md


async def run_autodream():
    try:
        log = get_todays_log()
        if not log.strip():
            return

        memory = read_memory_md()

        prompt = f"""You are performing a dream — a reflective pass over your memory.

Current MEMORY.md:
{memory}

Today's observations:
{log}

Instructions:
- Merge today's observations into the existing memory
- Remove contradictions and outdated facts
- Convert vague notes into specific facts
- Keep the result under 200 lines
- Output only the updated MEMORY.md content, nothing else
- Do not include any preamble or explanation"""

        response = await ask_dream_model(prompt)
        if response:
            write_memory_md(response)
    except Exception as e:
        from actions import print_brief
        print_brief(f"Autodream failed: {e}")
