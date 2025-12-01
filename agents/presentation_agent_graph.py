from langgraph.graph import StateGraph, MessagesState, START, END
from agents.understand_files import get_files_agent
from agents.outline_creation_agent import get_outline_agent
from agents.presentation_agent import get_ppt_agent
from agents.researcher_agent import get_web_researcher
from agent_tools.presentation_agent_tool import setup_slides_directory, convert_slides_to_pdf
import json
from logger import logging
import asyncio
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv()


class State(MessagesState):
    files_data: str
    web_content: str
    outline: str
    ppt_content: str


async def router(state: State):
    logging.info("Inside the router")
    msg = state['messages'][-1].content

    try:
        input_dict = json.loads(msg)
    except json.JSONDecodeError:
        import ast
        input_dict = ast.literal_eval(msg)

    if input_dict.get('files') and len(input_dict['files']) > 0:
        return 'files_agent'
    
    return 'researcher_agent'

@traceable
async def researcher(state: State):
    msg = state['messages'][-1].content

    try:
        input_dict = json.loads(msg)
    except json.JSONDecodeError:
        import ast
        input_dict = ast.literal_eval(msg)

    logging.info(f"Inside the researcher agent with the task: {input_dict.get('task')}")
    web_researcher = get_web_researcher()
    response = await web_researcher.ainvoke(
        {"messages": "Research on this topic" + input_dict.get('task')},
        config={"recursion_limit": 15}  # Limit to prevent infinite loops
    )

    return {"web_content": response["messages"][-1].content}

@traceable
async def file_understand_agent(state: State):
    logging.info("Inside Files Agent")

    msg = state['messages'][-1].content

    try:
        input_dict = json.loads(msg)
    except json.JSONDecodeError:
        import ast
        input_dict = ast.literal_eval(msg)

    files_agent = get_files_agent()
    response = await files_agent.ainvoke(
        {"messages": "Explore and provide the essence for the files mentioned in this query" + str(input_dict.get('files'))}
    )

    logging.info(f"Response from the files agent {response['messages'][-1].content}")

    return {"files_data": response["messages"][-1].content}

@traceable
async def outline_maker(state: State):
    logging.info("Inside the outline creation agent")
    
    msg = state['messages'][-1].content
    try:
        input_dict = json.loads(msg)
    except json.JSONDecodeError:
        import ast
        input_dict = ast.literal_eval(msg)

    user_query = input_dict.get('task')

    if len(input_dict.get('files')) == 0:
        logging.info("Creating outline using web content")
        outline_agent = get_outline_agent()
        response = await outline_agent.ainvoke(
            {"messages": "The user query is" + input_dict.get('task') + "create ppt outline using the content" + state["web_content"]}
        )

        return {"outline": response["messages"][-1].content}
    
    logging.info("creating outline with the files provided")
    logging.info(f"Files data state to create outline {state['files_data']}")

    outline_agent = get_outline_agent()
    response = await outline_agent.ainvoke(
        {"messages": "The user query is" + user_query + "Create the outline using the following content" + state["files_data"]}
    )
    return {"outline": response["messages"][-1].content}

@traceable
async def ppt(state: State):
    setup_slides_directory()
    logging.info("Starting slide generation")

    ppt_agent = get_ppt_agent()
    
    instruction = f"""Here is the presentation outline. You MUST call the create_slide tool for EACH slide listed below.
    
OUTLINE:
{state["outline"]}

Remember: Call create_slide(outline=<slide content>, slide_no=<number>) for EVERY slide starting from slide 1."""
    
    response = await ppt_agent.ainvoke(
        {"messages": instruction}
    )
    
    logging.info("Slide generation complete")
    
    # Convert all slides to PDF
    pdf_path = await convert_slides_to_pdf()
    if pdf_path:
        logging.info(f"Presentation PDF created at: {pdf_path}")
    else:
        logging.warning("Failed to create PDF from slides")
    
    return {"ppt_content": response["messages"][-1].content}

async def define_graph():
    builder = StateGraph(State)

    builder.add_node("files_agent", file_understand_agent)
    builder.add_node("outline_agent", outline_maker)
    builder.add_node("ppt_agent",  ppt)
    builder.add_node("researcher_agent", researcher)

    builder.add_conditional_edges(START, router, {"files_agent": "files_agent", "researcher_agent": "researcher_agent"})
    builder.add_edge("files_agent", "outline_agent")
    builder.add_edge("researcher_agent", "outline_agent")
    builder.add_edge("outline_agent", "ppt_agent")

    return builder.compile()

async def runner():
    graph = await define_graph()
    result = await graph.ainvoke(
        {"messages": '{"task": "create a 10 slide ppt on open weight model comparison", "files": []}'}
    )
    return result


if __name__ == "__main__":
    asyncio.run(runner())
