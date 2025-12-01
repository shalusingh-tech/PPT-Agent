from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
import aiofiles
from logger import logging
load_dotenv()

@tool
async def web_search(query: str) -> str:
    '''This tool helps to research the web
    Args:
        query: The query to search for in the web in string'''
    
    try:
        logging.info(f"Searching the web with the query {query}")
        
        research = TavilySearch(
            max_results = 2
        )

        result = await research.ainvoke(query)
        response = result["results"]

        async with aiofiles.open("files/web.txt", 'w', encoding="utf-8") as f:
            await f.write(str(response))

        logging.info(f"Successfully researched on the query: {query}")
        return f"The web search has been successfully completed for the query {query} and results are {response}"
    except Exception as e:
        logging.info(f"An error occured while searching your query error is {e}")
        return f"An error occured while searching your query error is {e}"
    
@tool
async def visual_search(query: str) -> str:
    '''Helps to search for images from web
    Args:
        query: Images to search for topic'''
    
    try:
        logging.info(f"Searching for images for the query {query}")
        visual = TavilySearch(
            max_results=5,
            include_images = True,
            inlcude_image_descriptions=True
        )

        result = visual.invoke(query)
        imgs = result["images"]
        titles = []
        for i in result["results"]:
            titles.append(i["title"])

        visuals = {}
        for i in range(5):
            visuals[titles[i]] = imgs[i]

        return f"Retrieved visual images with their short description are {visuals}"
    except Exception as e:
        logging.info(f"Error while doing the visual search inside visual_search tool and error is {str(e)}")
        return f"Error while doing the visual search and error is {str(e)}"


    


