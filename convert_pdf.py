"""
Standalone script to convert HTML slides to PDF using Playwright.
This runs as a separate process to avoid Windows asyncio issues.
"""
import os
import sys

def convert_slides_to_pdf():
    """Convert HTML slides to PDF using sync Playwright"""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    import requests
    
    # Remove PIL limit for large images
    Image.MAX_IMAGE_PIXELS = None
    
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
        print("ERROR: No HTML slides found")
        return None
    
    print(f"Found {len(html_files)} slides to convert")
    
    screenshot_paths = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        for num, filename in html_files:
            filepath = os.path.abspath(os.path.join(slides_dir, filename))
            file_url = f"file:///{filepath.replace(os.sep, '/')}"
            
            print(f"Rendering slide {num}: {filename}")
            
            # Create page with 12x scale for 16K (1280*12=15360, 720*12=8640)
            page = browser.new_page(device_scale_factor=12)
            page.set_viewport_size({"width": 1280, "height": 720})
            page.goto(file_url, wait_until="domcontentloaded", timeout=15000)
            
            # Inject CSS to ensure exact dimensions
            page.add_style_tag(content="""
                * { box-sizing: border-box !important; }
                html, body {
                    width: 1280px !important;
                    height: 720px !important;
                    max-width: 1280px !important;
                    max-height: 720px !important;
                    overflow: hidden !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
            """)
            
            # Wait for content to load
            page.wait_for_timeout(3000)
            
            # Take screenshot
            screenshot_path = os.path.join(slides_dir, f"slide_{num}.png")
            page.screenshot(
                path=screenshot_path,
                clip={"x": 0, "y": 0, "width": 1280, "height": 720}
            )
            screenshot_paths.append(screenshot_path)
            print(f"  Screenshot saved: {screenshot_path}")
            
            page.close()
        
        browser.close()
    
    print("Converting screenshots to PDF...")
    
    # 16K target
    TARGET_WIDTH = 15360
    TARGET_HEIGHT = 8640
    
    # Convert screenshots to PDF
    images = []
    for img_path in screenshot_paths:
        img = Image.open(img_path)
        
        # Convert to RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize to 16K if needed
        if img.width != TARGET_WIDTH or img.height != TARGET_HEIGHT:
            img_resized = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)
            img.close()
            img = img_resized
        
        images.append(img)
        print(f"  Processed: {img_path} -> {img.width}x{img.height}")
    
    # Save as PDF
    pdf_path = os.path.join(slides_dir, "presentation.pdf")
    if images:
        images[0].save(
            pdf_path,
            save_all=True,
            append_images=images[1:] if len(images) > 1 else [],
            resolution=300.0
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
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
