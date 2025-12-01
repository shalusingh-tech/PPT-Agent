from langchain_core.tools import tool
import aiofiles
from logger import logging

@tool
async def save_outline(outline: str) -> str:
    '''Helps to save the outline to a file
    Args:
        outline: Content to be saved in file'''
    try:
        logging.info("Creating outline using the save_outline tool")
        async with aiofiles.open("files/outline.txt", 'w', encoding="utf-8") as f:
            await f.write(str(outline))

        logging.info("Successfully created the outline")
        return "Outline has been successfully saved into file."
    except Exception as e:
        logging.info(f"Error while creating outline using the save_outline tool and error is {str(e)}")
        return f"An error while saving the outline error is {e}"