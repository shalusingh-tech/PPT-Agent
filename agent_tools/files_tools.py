from langchain_core.tools import tool
import os
import fitz
import asyncio
from agent_prompts.summarizer_prompts import summarizer_sys_prompt
from agent_prompts.img_description_prompt import img_desc_sys_prompt
from langchain_core.messages import SystemMessage, HumanMessage
from logger import logging
import sys
sys.path.append("..")
from config_loader import get_llm


# Lazy initialization (singleton pattern)
_summarizer = None
_img_describer = None

def get_summarizer():
    """Lazy initialization of summarizer LLM (singleton pattern)"""
    global _summarizer
    if _summarizer is None:
        _summarizer = get_llm(tool_name="summarizer")
    return _summarizer

def get_img_describer():
    """Lazy initialization of img_describer LLM (singleton pattern)"""
    global _img_describer
    if _img_describer is None:
        _img_describer = get_llm(tool_name="img_describer")
    return _img_describer

# def extract_images_from_pdf(pdf_path, output_folder="image_folder"):
    
#     os.makedirs(output_folder, exist_ok=True)

#     pdf_file = fitz.open(pdf_path)
#     img_count = 0

#     for page_index in range(len(pdf_file)):
#         page = pdf_file[page_index]
#         images = page.get_images(full=True)

#         for img_index, img in enumerate(images, start=1):
#             xref = img[0]
#             base_image = pdf_file.extract_image(xref)
#             image_bytes = base_image["image"]

#             img_count += 1
#             image_filename = os.path.join(output_folder, f"img_{img_count}.png")

#             with open(image_filename, "wb") as img_file:
#                 img_file.write(image_bytes)

#     pdf_file.close()
#     return f"Extracted {img_count} images to {output_folder}"


@tool
async def summarize_document(file_name: str) -> str:
    """Reads and understands and summarizes the content inside the document. Helps in summarizing pdf, docx files.
        Args:
            file_name: name of the file in string
    """
    try:
        logging.info(f"Summarizing document {file_name}")
        
        # Handle path - check if already includes user_files
        if file_name.startswith('user_files') or file_name.startswith('user_files\\') or file_name.startswith('user_files/'):
            file_path = file_name
        else:
            file_path = os.path.join('user_files', file_name)
        
        doc = fitz.open(file_path)

        glob_sum = ''

        for page_num in range(len(doc)):
            logging.info(f"processing page no {page_num}")
            page = doc[page_num]
            text = page.get_text()
            
            summarizer = get_summarizer()
            response = await summarizer.ainvoke(
                [SystemMessage(content=summarizer_sys_prompt.format(global_summary=glob_sum, current_content=text))]
            )
            glob_sum = response.content

        logging.info(f"Successfully summarized the document {file_name}")

        return f"The summary of the file {file_name} is: \n {glob_sum}"
    except Exception as e:
        logging.info(f"Error while summarizing document {file_name} error is {str(e)}")
        return f"Error while summarizing document {file_name} because of {str(e)}"

@tool
async def summarize_images(file_name: str) -> str:
    '''Helps to understand and summarize the '.png', '.jpg', '.jpeg', '.webp' extensions and provide its descriptions'''

    try:
        logging.info(f"Summarizing image {file_name}")
        
        # Handle path - check if already includes user_images
        if file_name.startswith('user_images') or file_name.startswith('user_images\\') or file_name.startswith('user_images/'):
            image_path = file_name
        else:
            image_path = os.path.join('user_images', file_name)
        
        # Read image and convert to base64
        import base64
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode("utf-8")
        
        # Determine image type
        ext = file_name.lower().split('.')[-1]
        mime_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"
        
        # Create multimodal message
        message = HumanMessage(
            content=[
                {"type": "text", "text": img_desc_sys_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_data}"}
                }
            ]
        )
        
        img_describer = get_img_describer()
        response = await img_describer.ainvoke([message])
        
        logging.info(f"Image summarization successful for {file_name}")

        return f"The image saved to {'user_images/' + file_name} has this information {response.content}"
    except Exception as e:
        logging.info(f"Error while summarizing image {file_name} and error is {str(e)}")
        return f"Error while summarizing image {file_name} and error is {str(e)}"



    

    




    
# if __name__ == '__main__':
#     result = asyncio.run(summarize_document('somatosensory.pdf'))
#     print(result)





