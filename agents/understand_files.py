import asyncio
from langgraph.prebuilt import create_react_agent
from agent_tools.files_tools import summarize_document, summarize_images
from agent_prompts.file_agent_prompt import files_agent_sys_prompt
import sys
sys.path.append("..")
from config_loader import get_llm


# Lazy initialization (singleton pattern)
_files_agent = None

def get_files_agent():
    """Lazy initialization of files_agent (singleton pattern)"""
    global _files_agent
    if _files_agent is None:
        _files_agent = create_react_agent(
            model=get_llm(agent_name="file_understanding"),
            prompt=files_agent_sys_prompt,
            tools=[summarize_document, summarize_images]
        )
    return _files_agent

# For backward compatibility
files_agent = None  # Will be initialized on first use via get_files_agent()


# async def runner():
#     response = await files_agent.ainvoke(
#         {"messages": "summarize the somatosensory.pdf file"}
#     )

#     for i in response["messages"]:
#         i.pretty_print()

# if __name__ == '__main__':
#     asyncio.run(runner())

