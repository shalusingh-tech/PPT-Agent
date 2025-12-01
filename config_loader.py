import yaml
from pathlib import Path
from langchain_community.chat_models import ChatLiteLLM
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.yaml"

_config_cache = None

def load_config():
    """Load configuration from YAML file with caching."""
    global _config_cache
    if _config_cache is None:
        with open(CONFIG_PATH, "r") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def get_llm(agent_name: str = None, tool_name: str = None):
    """
    Get LLM instance based on agent or tool name.
    
    Args:
        agent_name: Name of the agent (researcher, file_understanding, outline_creation, presentation)
        tool_name: Name of the tool (summarizer, ppt_creator, img_describer)
    
    Returns:
        ChatLiteLLM instance configured according to config.yaml
    """
    config = load_config()
    
    # Determine which config to use
    if agent_name:
        llm_config = config["agents"].get(agent_name, config["default"])
    elif tool_name:
        llm_config = config["tools"].get(tool_name, config["default"])
    else:
        llm_config = config["default"]
    
    # Build kwargs for ChatLiteLLM
    kwargs = {
        "model": llm_config.get("model"),
        "temperature": llm_config.get("temperature", 0.7),
    }
    
    # Add api_key if provided and not empty
    api_key = llm_config.get("api_key")
    if api_key:
        kwargs["api_key"] = api_key
    
    # Add api_base if provided (for Ollama, Azure, etc.)
    api_base = llm_config.get("api_base")
    if api_base:
        kwargs["api_base"] = api_base
    
    return ChatLiteLLM(**kwargs)
