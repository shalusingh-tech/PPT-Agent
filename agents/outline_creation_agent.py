from langgraph.prebuilt import create_react_agent
from agent_prompts.outline_agent_prompt import outline_sys_prompt
from agent_tools.outline_agent_tool import save_outline
import sys
sys.path.append("..")
from config_loader import get_llm


# Lazy initialization (singleton pattern)
_outline_agent = None

def get_outline_agent():
    """Lazy initialization of outline_agent (singleton pattern)"""
    global _outline_agent
    if _outline_agent is None:
        _outline_agent = create_react_agent(
            model=get_llm(agent_name="outline_creation"),
            prompt=outline_sys_prompt,
            tools=[save_outline],
            name="outline_creation"
        )
    return _outline_agent

# For backward compatibility
outline_agent = None  # Will be initialized on first use via get_outline_agent()

 