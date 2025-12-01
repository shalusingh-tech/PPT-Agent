from langchain_core.tools import tool
import aiofiles
from langgraph.prebuilt import create_react_agent
from agent_prompts.presentation_agent_prompt import sys_presentation_prompt
from langgraph.checkpoint.memory import InMemorySaver
import os
import shutil
import datetime
from logger import logging
import sys
import asyncio
import concurrent.futures
import re
sys.path.append("..")
from config_loader import get_llm
from PIL import Image
import io

# Remove PIL decompression bomb limit for large images (16K support)
Image.MAX_IMAGE_PIXELS = None


thread_id = '25'
_ppt_creator = None

def get_ppt_creator():
    """Lazy initialization of ppt_creator agent (singleton pattern)"""
    global _ppt_creator
    if _ppt_creator is None:
        _ppt_creator = create_react_agent(
            model=get_llm(tool_name="ppt_creator"),
            prompt=sys_presentation_prompt.format(date=datetime.datetime.today()),
            tools=[],
            checkpointer=InMemorySaver(),
            name="ppt_creation"
        )
    return _ppt_creator


def setup_slides_directory():
    """
    Setup slides directory before creating slides.
    If exists, empty it. If not, create it.
    """
    slides_dir = "slides"
    
    if os.path.exists(slides_dir):
        # Empty the directory
        shutil.rmtree(slides_dir)
        logging.info(f"Emptied existing slides directory: {slides_dir}")
    
    # Create fresh directory
    os.makedirs(slides_dir)
    logging.info(f"Created fresh slides directory: {slides_dir}")


def _convert_slides_to_pdf_sync():
    """
    Synchronous PDF conversion using Playwright sync API.
    Runs in a separate thread to avoid Windows asyncio issues.
    """
    try:
        from playwright.sync_api import sync_playwright
        import requests
        
        slides_dir = "slides"
        
        # Get all HTML files sorted by number
        html_files = []
        for f in os.listdir(slides_dir):
            if f.endswith('.html'):
                try:
                    num = int(f.replace('.html', ''))
                    html_files.append((num, f))
                except ValueError:
                    continue
        
        html_files.sort(key=lambda x: x[0])
        
        if not html_files:
            logging.warning("No HTML slides found to convert to PDF")
            return None
        
        logging.info(f"Found {len(html_files)} slides to convert to PDF")
        
        # Function to check if image URL is accessible
        def check_image_url(url: str) -> bool:
            try:
                response = requests.head(url, timeout=5)
                return response.status_code == 200
            except Exception:
                return False
        
        # Function to process HTML and handle broken images
        def process_html_images(html_content: str) -> str:
            # Find all image URLs in the HTML
            img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
            img_matches = re.findall(img_pattern, html_content)
            
            for img_url in img_matches:
                if img_url.startswith('http'):
                    is_valid = check_image_url(img_url)
                    if not is_valid:
                        logging.warning(f"Image not accessible: {img_url}")
                        # Use a placeholder for broken images
                        placeholder = '''<div style="
                            width: 100%; 
                            height: 200px; 
                            background: linear-gradient(135deg, #e3f2fd 25%, #bbdefb 25%, #bbdefb 50%, #e3f2fd 50%, #e3f2fd 75%, #bbdefb 75%);
                            background-size: 20px 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: #1976d2;
                            font-size: 14px;
                            border: 2px dashed #1976d2;
                            border-radius: 8px;
                        "><i class="fas fa-image" style="margin-right: 8px;"></i> Image unavailable</div>'''
                        html_content = re.sub(
                            rf'<img[^>]+src=["\']' + re.escape(img_url) + r'["\'][^>]*>',
                            placeholder,
                            html_content
                        )
                        logging.info(f"Replaced broken image with placeholder: {img_url}")
            
            return html_content
        
        # Pre-process all HTML files to handle broken images
        for num, filename in html_files:
            filepath = os.path.join(slides_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            processed_html = process_html_images(html_content)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(processed_html)
        
        logging.info("Processed all slides for broken images")
        
        pdf_paths = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            
            for num, filename in html_files:
                filepath = os.path.abspath(os.path.join(slides_dir, filename))
                file_url = f"file:///{filepath.replace(os.sep, '/')}"
                
                logging.info(f"Rendering slide {num}: {filename}")
                
                # Create page with 3x scale for native 4K capture (1280*3=3840, 720*3=2160)
                page = browser.new_page(device_scale_factor=3)
                page.set_viewport_size({"width": 1280, "height": 720})
                page.goto(file_url, wait_until="networkidle")
                
                # Wait for content to fully render
                page.wait_for_timeout(2000)
                
                # Apply strict styling to ensure exact 1280x720 - NO overflow or underflow
                page.add_style_tag(content="""
                    * { box-sizing: border-box !important; }
                    html, body {
                        width: 1280px !important;
                        height: 720px !important;
                        max-width: 1280px !important;
                        max-height: 720px !important;
                        min-width: 1280px !important;
                        min-height: 720px !important;
                        overflow: hidden !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        background: white !important;
                    }
                    body {
                        display: flex !important;
                        justify-content: center !important;
                        align-items: flex-start !important;
                    }
                    .slide-container {
                        width: 1280px !important;
                        height: 720px !important;
                        max-width: 1280px !important;
                        max-height: 720px !important;
                        min-width: 1280px !important;
                        min-height: 720px !important;
                        overflow: hidden !important;
                        margin: 0 !important;
                        border-radius: 0 !important;
                        box-shadow: none !important;
                    }
                """)
                
                # Wait for styles to apply
                page.wait_for_timeout(500)
                
                # Take exact viewport screenshot - strict 1280x720, no overflow/underflow
                screenshot_path = os.path.join(slides_dir, f"slide_{num}.png")
                page.screenshot(
                    path=screenshot_path,
                    clip={"x": 0, "y": 0, "width": 1280, "height": 720}
                )
                
                pdf_paths.append(screenshot_path)
                logging.info(f"Captured slide {num} with strict 1280x720 (no overflow/underflow)")
                page.close()
            
            browser.close()
        
        # 4K target resolution (native from 3x scale factor)
        TARGET_4K_WIDTH = 3840
        TARGET_4K_HEIGHT = 2160
        
        # Convert screenshots to PDF - already captured at 4K natively
        images = []
        for img_path in pdf_paths:
            img = Image.open(img_path)
            # Convert to RGB if necessary (PNG might have alpha channel)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # With device_scale_factor=3 and clip 1280x720, images should be exactly 3840x2160 (4K)
            # No scaling needed - strict capture ensures exact dimensions
            logging.info(f"Image dimensions: {img.width}x{img.height}")
            
            # Verify dimensions match 4K
            if img.width != TARGET_4K_WIDTH or img.height != TARGET_4K_HEIGHT:
                logging.warning(f"Unexpected dimensions {img.width}x{img.height}, expected {TARGET_4K_WIDTH}x{TARGET_4K_HEIGHT}")
                # Resize to exact 4K if needed
                img_resized = img.resize((TARGET_4K_WIDTH, TARGET_4K_HEIGHT), Image.LANCZOS)
                img.close()
                img = img_resized
            
            images.append(img)
            logging.info(f"Added 4K image: {img.width}x{img.height}")
        
        # Save as PDF with 270 DPI
        # 3840x2160 pixels at 270 DPI = 14.2" x 8" page (close to widescreen format)
        final_pdf_path = os.path.join(slides_dir, "presentation.pdf")
        if images:
            images[0].save(
                final_pdf_path,
                save_all=True,
                append_images=images[1:] if len(images) > 1 else [],
                resolution=300.0
            )
        
        # Close all images
        for img in images:
            img.close()
        
        # Clean up screenshot files
        for img_path in pdf_paths:
            try:
                os.remove(img_path)
            except:
                pass
        
        logging.info(f"PDF created successfully: {final_pdf_path}")
        return final_pdf_path
        
    except ImportError as e:
        logging.error(f"Required packages not installed. Run: pip install playwright requests && playwright install chromium. Error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error converting to PDF: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None


async def convert_slides_to_pdf():
    """
    Convert slides to PDF by running a separate Python process.
    This completely avoids Windows asyncio subprocess issues.
    Uses Html2Image for high-resolution output.
    """
    import subprocess
    
    logging.info("Starting PDF conversion (using Html2Image subprocess)")
    
    try:
        # Get the path to the Python interpreter in the venv
        if sys.platform == 'win32':
            python_exe = os.path.join(os.path.dirname(sys.executable), 'python.exe')
        else:
            python_exe = sys.executable
        
        # Path to the conversion script (using Html2Image version)
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'convert_pdf_html2image.py')
        
        logging.info(f"Running PDF conversion script: {script_path}")
        
        # Run the conversion script as a subprocess
        result = subprocess.run(
            [python_exe, script_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        # Log output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logging.info(f"PDF Converter: {line}")
        
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                logging.warning(f"PDF Converter stderr: {line}")
        
        if result.returncode == 0:
            pdf_path = os.path.join("slides", "presentation.pdf")
            if os.path.exists(pdf_path):
                logging.info(f"PDF created successfully: {pdf_path}")
                return pdf_path
            else:
                logging.error("PDF file not found after conversion")
                return None
        else:
            logging.error(f"PDF conversion failed with return code {result.returncode}")
            return None
            
    except Exception as e:
        logging.error(f"Error running PDF conversion subprocess: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None


@tool
async def create_slide(outline: str, slide_no: int) -> str:
    '''Helps to create one slide at a time'''
    try:
        # Add delay before API call to respect rate limits (sequential processing)
        import asyncio
        await asyncio.sleep(3)  # Wait 3 seconds between slides
        
        logging.info(f"Inside the create slide tool with outline {outline}")
        ppt_creator = get_ppt_creator()
        result = await ppt_creator.ainvoke(
            {"messages": f"Create a single slide using the outline {outline}"},
            config={"configurable":{"thread_id": thread_id}}
        )

        content = result["messages"][-1].content
        logging.info(f"PPT Creator response: {content[:500]}...")  # Log first 500 chars
        
        # Try to extract HTML code
        start = content.find('```html')
        if start == -1:
            # Try without language specifier
            start = content.find('```')
        
        if start != -1:
            end = content.find('```', start + 7 if '```html' in content else start + 3)
            if end != -1:
                if '```html' in content:
                    html_code = content[start + 7:end].strip()
                else:
                    html_code = content[start + 3:end].strip()
            else:
                html_code = content  # Use full content if no closing ```
        else:
            html_code = content  # Use full content if no code blocks

        logging.info(f"Extracted HTML code length: {len(html_code)}")

        # create slide dir. if not exist
        os.makedirs("slides", exist_ok=True)
        logging.info("Slides directory created/verified")
        
        async with aiofiles.open(f"slides/{slide_no}.html", 'w', encoding="utf-8") as f:
            await f.write(html_code)

        logging.info(f"Slide {slide_no} saved successfully to slides/{slide_no}.html")
        return f"{slide_no} has been successfully created and saved"
    except Exception as e:
        logging.error(f"Faced error while creating slide inside create_slide tool and error is {str(e)}")
        return f"There was an error creating the ppt the error is {e}"


