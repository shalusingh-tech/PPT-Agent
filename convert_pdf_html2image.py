"""
Alternative PDF conversion using Html2Image package.
Run this script to convert HTML slides to PDF.
Renders at native 4K resolution for crisp output.
"""
import os
import sys
import glob
from html2image import Html2Image
from PIL import Image

# Remove PIL limit for large images
Image.MAX_IMAGE_PIXELS = None

# Render at native slide size (content designed for 1280x720)
# Extra height to capture any overflow content
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 900

# PDF page dimensions - 4K (16:9 aspect ratio)
PAGE_WIDTH = 3840
PAGE_HEIGHT = 2160


def find_chromium_path():
    """Find Playwright's bundled Chromium executable or Chrome (cross-platform)"""
    
    # Get user home directory (works on all platforms)
    home = os.path.expanduser("~")
    
    # Platform-specific Playwright cache locations
    if sys.platform == 'win32':
        playwright_cache = os.path.join(home, "AppData", "Local", "ms-playwright")
    elif sys.platform == 'darwin':  # macOS
        playwright_cache = os.path.join(home, "Library", "Caches", "ms-playwright")
    else:  # Linux
        playwright_cache = os.path.join(home, ".cache", "ms-playwright")
    
    if os.path.exists(playwright_cache):
        print(f"Looking in Playwright cache: {playwright_cache}")
        # Look for chromium folders
        chromium_dirs = glob.glob(os.path.join(playwright_cache, "chromium-*"))
        for chromium_dir in sorted(chromium_dirs, reverse=True):  # Get latest version
            # Platform-specific browser executable
            if sys.platform == 'win32':
                chrome_path = os.path.join(chromium_dir, "chrome-win", "chrome.exe")
            elif sys.platform == 'darwin':
                chrome_path = os.path.join(chromium_dir, "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium")
            else:  # Linux
                chrome_path = os.path.join(chromium_dir, "chrome-linux", "chrome")
            
            if os.path.exists(chrome_path):
                return chrome_path
    
    # Fallback: try system Chrome/Chromium
    if sys.platform == 'win32':
        chrome_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(home, 'AppData', 'Local', 'Google', 'Chrome', 'Application', 'chrome.exe'),
        ]
    elif sys.platform == 'darwin':
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
        ]
    else:  # Linux
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/snap/bin/chromium',
        ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    
    return None


def convert_slides_to_pdf():
    """Convert HTML slides to PDF using Html2Image"""
    
    slides_dir = "slides"
    output_dir = "slides"
    
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
        print("ERROR: No HTML slides found")
        return None
    
    print(f"Found {len(html_files)} slides to convert")
    
    # Find Chrome/Chromium path
    chrome_path = find_chromium_path()
    if chrome_path:
        print(f"Using browser: {chrome_path}")
    else:
        print("ERROR: Could not find Chrome or Chromium.")
        return None
    
    # Initialize Html2Image at native 4K resolution
    hti = Html2Image(
        output_path=output_dir,
        browser_executable=chrome_path,
        size=(VIEWPORT_WIDTH, VIEWPORT_HEIGHT),
        custom_flags=[
            '--hide-scrollbars',
            '--disable-gpu',
            '--no-sandbox'
        ]
    )
    
    print(f"Rendering at native {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} pixels")
    
    screenshot_paths = []
    
    for num, filename in html_files:
        filepath = os.path.abspath(os.path.join(slides_dir, filename))
        output_name = f"slide_{num}.png"
        
        print(f"Rendering slide {num}: {filename}")
        
        # Read HTML content
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # CSS to render at native slide size
        wrapper_css = f"""
            * {{ box-sizing: border-box !important; }}
            html, body {{
                width: {VIEWPORT_WIDTH}px !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: visible !important;
                background: #f8f9fa !important;
            }}
            body {{
                min-height: auto !important;
                height: auto !important;
                display: block !important;
            }}
            .slide-container {{
                min-height: auto !important;
                height: auto !important;
                box-shadow: none !important;
                margin: 0 !important;
            }}
        """
        
        try:
            hti.screenshot(
                html_str=html_content,
                css_str=wrapper_css,
                save_as=output_name
            )
            
            screenshot_path = os.path.join(output_dir, output_name)
            if os.path.exists(screenshot_path):
                screenshot_paths.append(screenshot_path)
                print(f"  Screenshot saved: {screenshot_path}")
            else:
                print(f"  WARNING: Screenshot not created for slide {num}")
        except Exception as e:
            print(f"  ERROR rendering slide {num}: {e}")
            continue
    
    if not screenshot_paths:
        print("ERROR: No screenshots were created")
        return None
    
    print("Converting screenshots to PDF...")
    print(f"Target page size: {PAGE_WIDTH}x{PAGE_HEIGHT} pixels (16:9)")
    
    # Convert screenshots to PDF
    images = []
    for img_path in screenshot_paths:
        img = Image.open(img_path)
        print(f"  Original size: {img.width}x{img.height}")
        
        # Convert to RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Crop to 16:9 aspect ratio from top
        target_height = int(img.width * 9 / 16)
        if img.height > target_height:
            print(f"  Cropping to 16:9: {img.width}x{img.height} -> {img.width}x{target_height}")
            img = img.crop((0, 0, img.width, target_height))
        
        # Resize if needed
        if img.width != PAGE_WIDTH or img.height != PAGE_HEIGHT:
            print(f"  Resizing: {img.width}x{img.height} -> {PAGE_WIDTH}x{PAGE_HEIGHT}")
            img_resized = img.resize((PAGE_WIDTH, PAGE_HEIGHT), Image.LANCZOS)
            img.close()
            img = img_resized
        
        images.append(img)
        print(f"  Final: {img.width}x{img.height}")
    
    # Save as PDF
    pdf_path = os.path.join(slides_dir, "presentation.pdf")
    if images:
        images[0].save(
            pdf_path,
            save_all=True,
            append_images=images[1:] if len(images) > 1 else [],
            resolution=270.0
        )
        print(f"PDF created: {pdf_path}")
    
    # Close all images
    for img in images:
        img.close()
    
    # Clean up screenshot files
    for img_path in screenshot_paths:
        try:
            os.remove(img_path)
        except:
            pass
    
    print("SUCCESS")
    return pdf_path


if __name__ == "__main__":
    try:
        result = convert_slides_to_pdf()
        if result:
            print(f"\nPDF saved to: {result}")
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
