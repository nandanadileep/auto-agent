import re

from agent.llm import ask_dream_model
from memory.daily_log import get_todays_log
from memory.memory_md import list_topics, read_all_topics, read_topic, write_memory_md, write_topic


async def run_autodream():
    try:
        log = get_todays_log()
        if not log.strip():
            return

        existing_topics = read_all_topics()
        topics_text = "\n\n".join(
            f"## {t}\n{c}" for t, c in existing_topics.items()
        ) if existing_topics else "(none yet)"

        prompt = f"""You are performing a dream — a reflective pass over your memory.

Existing topic files:
{topics_text}

Today's observations:
{log}

Instructions:
- Merge today's observations into the relevant topics
- Create new topics if observations don't fit existing ones
- Remove contradictions and outdated facts within each topic
- Convert vague notes into specific facts
- Keep each topic under 100 lines
- Output ONLY topic sections in this exact format, nothing else:

## topic_name
<content>

## another_topic
<content>

Use short lowercase snake_case topic names (e.g. auth, open_prs, testing, dependencies, architecture)."""

        response = await ask_dream_model(prompt)
        if not response:
            return

        # parse ## topic_name sections
        sections = re.split(r'\n## ', '\n' + response.strip())
        parsed = {}
        for section in sections:
            if not section.strip():
                continue
            lines = section.strip().splitlines()
            topic = lines[0].strip().lower().replace(" ", "_")
            content = "\n".join(lines[1:]).strip()
            if topic and content:
                parsed[topic] = content

        if not parsed:
            return

        # write each topic file
        for topic, content in parsed.items():
            write_topic(topic, content)

        # update MEMORY.md index
        index_lines = ["# Memory Index", ""]
        for topic in sorted(list_topics()):
            index_lines.append(f"- [{topic}](topics/{topic}.md)")
        write_memory_md("\n".join(index_lines))

    except Exception as e:
        from actions import print_brief
        print_brief(f"Autodream failed: {e}")
