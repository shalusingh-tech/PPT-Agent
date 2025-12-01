from langgraph.prebuilt import create_react_agent
from agent_tools.researcher_tool import web_search, visual_search
from agent_prompts.researcher_prompt import researcher_sys_prompt
import sys
sys.path.append("..")
from config_loader import get_llm


# Agent - Lazy initialization (singleton pattern)
_web_researcher = None

def get_web_researcher():
    """Lazy initialization of web_researcher agent (singleton pattern)"""
    global _web_researcher
    if _web_researcher is None:
        _web_researcher = create_react_agent(
            model=get_llm(agent_name="researcher"),
            tools=[web_search, visual_search],
            prompt=researcher_sys_prompt,
            name="researcher_agent",
        )
    return _web_researcher

# For backward compatibility
web_researcher = None  # Will be initialized on first use via get_web_researcher()


# async def main():
#     result = await web_researcher.ainvoke(
#         {"messages": "Create ppt on comparison of memory for ai agents langmem, mem0"}
#     )
#     print(result)

#     for i in result["messages"]:
#         i.pretty_print()

# if __name__ == "__main__":
#     asyncio.run(main())


