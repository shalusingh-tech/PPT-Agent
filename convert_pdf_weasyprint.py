"""
PDF conversion using WeasyPrint package.
Run this script to convert HTML slides to PDF.
WeasyPrint is a pure Python HTML/CSS to PDF converter.
"""
import os
import sys
from weasyprint import HTML, CSS
from PIL import Image
import io

# Remove PIL limit for large images
Image.MAX_IMAGE_PIXELS = None


def convert_slides_to_pdf():
    """Convert HTML slides to PDF using WeasyPrint"""
    
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
    
    # CSS to ensure proper slide dimensions (16:9 aspect ratio)
    # Using A4 landscape-ish dimensions that maintain 16:9
    page_css = CSS(string='''
        @page {
            size: 1280px 720px;
            margin: 0;
        }
        html, body {
            width: 1280px;
            height: 720px;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }
    ''')
    
    pdf_documents = []
    
    for num, filename in html_files:
        filepath = os.path.abspath(os.path.join(slides_dir, filename))
        print(f"Rendering slide {num}: {filename}")
        
        try:
            # Create HTML object from file
            html = HTML(filename=filepath, base_url=os.path.dirname(filepath))
            
            # Render to PDF
            pdf_doc = html.render(stylesheets=[page_css])
            pdf_documents.append(pdf_doc)
            print(f"  Rendered slide {num}")
            
        except Exception as e:
            print(f"  ERROR rendering slide {num}: {e}")
            continue
    
    if not pdf_documents:
        print("ERROR: No slides were rendered")
        return None
    
    print("Combining slides into single PDF...")
    
    # Combine all pages into one PDF
    pdf_path = os.path.join(slides_dir, "presentation.pdf")
    
    # Get all pages from all documents
    all_pages = []
    for doc in pdf_documents:
        all_pages.extend(doc.pages)
    
    # Write combined PDF
    if all_pages:
        # Use the first document's metadata and combine pages
        pdf_documents[0].copy(all_pages).write_pdf(pdf_path)
        print(f"PDF created: {pdf_path}")
    else:
        print("ERROR: No pages to combine")
        return None
    
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
