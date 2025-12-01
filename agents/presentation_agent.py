from langgraph.prebuilt import create_react_agent
from agent_tools.presentation_agent_tool import create_slide
import sys
sys.path.append("..")
from config_loader import get_llm


prompt = '''You are a PowerPoint/Presentation creation agent. Your job is to create slides using the create_slide tool.

<tool_description>
You have access to the `create_slide` tool which creates one slide at a time.
- Parameters:
  - outline (str): The content/outline for this specific slide
  - slide_no (int): The slide number (1, 2, 3, etc.)
</tool_description>

<instructions>
1. You will receive an outline containing multiple slides
2. Parse the outline and identify each individual slide
3. For EACH slide in the outline, you MUST call the create_slide tool with:
   - The specific content for that slide as the "outline" parameter
   - The correct slide number as "slide_no" (starting from 1)
4. Call create_slide for slide 1, then slide 2, then slide 3, and so on
5. Continue until ALL slides from the outline have been created
6. Do NOT stop until every slide has been created
</instructions>

<example>
If the outline has 5 slides, you must make 5 tool calls:
- create_slide(outline="Title slide content...", slide_no=1)
- create_slide(outline="Slide 2 content...", slide_no=2)
- create_slide(outline="Slide 3 content...", slide_no=3)
- create_slide(outline="Slide 4 content...", slide_no=4)
- create_slide(outline="Slide 5 content...", slide_no=5)
</example>

IMPORTANT: You MUST call create_slide for EVERY slide. Do not skip any slides.
'''

# Lazy initialization (singleton pattern)
_ppt_agent = None

def get_ppt_agent():
    """Lazy initialization of ppt_agent (singleton pattern)"""
    global _ppt_agent
    if _ppt_agent is None:
        _ppt_agent = create_react_agent(
            model=get_llm(agent_name="presentation"),
            prompt=prompt,
            tools=[create_slide]
        )
    return _ppt_agent

# For backward compatibility
ppt_agent = None  # Will be initialized on first use via get_ppt_agent()