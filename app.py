import streamlit as st
import asyncio
import os
import sys
import json
import yaml
from pathlib import Path
import base64
import zipfile
import io
from datetime import datetime
import requests

# Set page config first (must be first Streamlit command)
st.set_page_config(
    page_title="Presenter Generator Agent",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.messages import HumanMessage
from agents.understand_files import get_files_agent
from agents.outline_creation_agent import get_outline_agent
from agents.presentation_agent import get_ppt_agent
from agents.researcher_agent import get_web_researcher
from agent_tools.presentation_agent_tool import setup_slides_directory, convert_slides_to_pdf
from logger import logging

# Constants
SLIDES_DIR = "slides"
USER_FILES_DIR = "user_files"
USER_IMAGES_DIR = "user_images"

# Ensure directories exist
os.makedirs(USER_FILES_DIR, exist_ok=True)
os.makedirs(USER_IMAGES_DIR, exist_ok=True)
os.makedirs(SLIDES_DIR, exist_ok=True)


def validate_url(url: str) -> tuple[bool, str]:
    """Check if URL is reachable and readable"""
    if not url or not url.strip():
        return True, ""  # No URL provided, skip validation
    
    url = url.strip()
    
    # Check URL format
    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with http:// or https://"
    
    try:
        # Try to reach the URL with a timeout
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            return True, ""
        elif response.status_code == 403:
            # Some sites block HEAD requests, try GET
            response = requests.get(url, timeout=10, allow_redirects=True, stream=True)
            if response.status_code == 200:
                return True, ""
            return False, f"Access forbidden (HTTP {response.status_code})"
        elif response.status_code == 404:
            return False, "Page not found (HTTP 404)"
        else:
            return False, f"URL returned HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "Connection timed out - URL may be slow or unreachable"
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to URL - check if it's correct"
    except requests.exceptions.TooManyRedirects:
        return False, "Too many redirects - URL may be misconfigured"
    except Exception as e:
        return False, f"Error checking URL: {str(e)}"


def validate_files(uploaded_files) -> tuple[bool, str]:
    """Check if uploaded files are readable"""
    if not uploaded_files:
        return True, ""  # No files provided, skip validation
    
    errors = []
    
    for f in uploaded_files:
        try:
            # Try to read the file content
            content = f.read()
            f.seek(0)  # Reset file pointer for later use
            
            if len(content) == 0:
                errors.append(f"'{f.name}' is empty")
            elif len(content) > 10 * 1024 * 1024:  # 10MB limit
                errors.append(f"'{f.name}' is too large (max 10MB)")
                
        except Exception as e:
            errors.append(f"'{f.name}' could not be read: {str(e)}")
    
    if errors:
        return False, "\\n".join(errors)
    
    return True, ""


# Progress tracking class
class ProgressTracker:
    def __init__(self, steps_container):
        self.steps_container = steps_container
        self.completed_steps = []
        self.current_step = None
        self.is_complete = False
        self.steps = [
            {"id": "router", "label": "Analyzing"},
            {"id": "research", "label": "Researching"},
            {"id": "outline", "label": "Generating Outline"},
            {"id": "slides", "label": "Generating Slides"},
        ]
    
    def update(self, step_id: str, message: str = None):
        """Update progress to a specific step"""
        # Handle completion
        if step_id == "complete":
            self.is_complete = True
            if "slides" not in self.completed_steps:
                self.completed_steps.append("slides")
            self.current_step = None
            self._render_steps()
            return
        
        # Map pdf and files to appropriate steps
        if step_id == "pdf":
            step_id = "slides"
        elif step_id == "files":
            step_id = "research"
        
        # Mark previous step as completed if moving to new step
        if self.current_step and self.current_step != step_id:
            if self.current_step not in self.completed_steps:
                self.completed_steps.append(self.current_step)
        
        self.current_step = step_id
        self._render_steps()
    
    def _render_steps(self):
        """Render the steps with tick marks"""
        self.steps_container.empty()
        
        with self.steps_container.container():
            for step in self.steps:
                if self.is_complete or step["id"] in self.completed_steps:
                    # Completed - green tick
                    st.markdown(f"✅ {step['label']}")
                elif step["id"] == self.current_step:
                    # In progress - spinner
                    st.markdown(f"🔄 {step['label']}...")
                else:
                    # Pending - empty box
                    st.markdown(f"⬜ {step['label']}")


async def run_generation_with_progress(task: str, files: list, tracker: ProgressTracker):
    """Run the presentation generation with real-time progress updates"""
    
    state = {
        "files_data": "",
        "web_content": "",
        "outline": "",
        "ppt_content": ""
    }
    
    # Step 1: Router - determine path
    tracker.update("router", "Analyzing your request")
    await asyncio.sleep(0.3)  # Small delay for UI update
    
    has_files = files and len(files) > 0
    
    # Step 2: Research or File Analysis
    if has_files:
        tracker.update("files", "Reading and analyzing your files")
        files_agent = get_files_agent()
        response = await files_agent.ainvoke(
            {"messages": "Explore and provide the essence for the files mentioned: " + str(files)}
        )
        state["files_data"] = response["messages"][-1].content
        logging.info("Files analysis complete")
    else:
        tracker.update("research", "Researching topic online")
        web_researcher = get_web_researcher()
        response = await web_researcher.ainvoke(
            {"messages": "Research on this topic: " + task},
            config={"recursion_limit": 30}  # Increased limit for thorough research
        )
        state["web_content"] = response["messages"][-1].content
        logging.info("Web research complete")
    
    # Step 3: Create Outline
    tracker.update("outline", "Creating presentation outline")
    outline_agent = get_outline_agent()
    
    if has_files:
        response = await outline_agent.ainvoke(
            {"messages": f"The user query is: {task}. Create the outline using: {state['files_data']}"}
        )
    else:
        response = await outline_agent.ainvoke(
            {"messages": f"The user query is: {task}. Create ppt outline using: {state['web_content']}"}
        )
    state["outline"] = response["messages"][-1].content
    logging.info("Outline creation complete")
    
    # Step 4: Generate Slides
    tracker.update("slides", "Generating HTML slides")
    setup_slides_directory()
    
    ppt_agent = get_ppt_agent()
    response = await ppt_agent.ainvoke(
        {"messages": "This is the outline: " + state["outline"]},
        config={"recursion_limit": 50}  # Higher limit for multiple slide creation
    )
    state["ppt_content"] = response["messages"][-1].content
    logging.info("Slide generation complete")
    
    # Step 5: Convert to PDF
    tracker.update("pdf", "Converting slides to PDF")
    pdf_path = await convert_slides_to_pdf()
    logging.info(f"PDF conversion complete: {pdf_path}")
    
    # Complete!
    tracker.update("complete", "Presentation generated successfully!")
    
    return state, pdf_path


def get_slide_files():
    """Get all HTML slide files sorted by number"""
    if not os.path.exists(SLIDES_DIR):
        return []
    
    slides = []
    for f in os.listdir(SLIDES_DIR):
        if f.endswith('.html') and f[:-5].isdigit():
            slides.append(f)
    
    slides.sort(key=lambda x: int(x[:-5]))
    return slides


def save_uploaded_file(uploaded_file, directory):
    """Save uploaded file to specified directory"""
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def render_slide_preview(slide_path):
    """Render HTML slide in an iframe"""
    with open(slide_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Encode HTML for iframe
    b64 = base64.b64encode(html_content.encode()).decode()
    iframe_html = f'''
        <div style="border: 2px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <iframe src="data:text/html;base64,{b64}" 
                    width="100%" 
                    height="500" 
                    style="border: none;">
            </iframe>
        </div>
    '''
    st.markdown(iframe_html, unsafe_allow_html=True)


def render_pdf_preview(pdf_path):
    """Render PDF preview by converting pages to images with Previous/Next buttons"""
    try:
        import fitz  # PyMuPDF
        
        # Open PDF
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        
        # Initialize page number in session state
        if 'pdf_page_num' not in st.session_state:
            st.session_state.pdf_page_num = 1
        
        # Ensure page number is valid
        if st.session_state.pdf_page_num < 1:
            st.session_state.pdf_page_num = 1
        if st.session_state.pdf_page_num > num_pages:
            st.session_state.pdf_page_num = num_pages
        
        page_num = st.session_state.pdf_page_num
        
        # Navigation row with buttons and page indicator
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", use_container_width=True, disabled=(page_num <= 1), key="pdf_prev"):
                st.session_state.pdf_page_num -= 1
                st.rerun()
        
        with col2:
            st.markdown(f"<h4 style='text-align: center; margin: 0;'>Page {page_num} of {num_pages}</h4>", unsafe_allow_html=True)
        
        with col3:
            if st.button("Next ➡️", use_container_width=True, disabled=(page_num >= num_pages), key="pdf_next"):
                st.session_state.pdf_page_num += 1
                st.rerun()
        
        # Render selected page at 1x resolution (smaller)
        page = doc[page_num - 1]
        mat = fitz.Matrix(1.0, 1.0)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Display image centered with max width
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.image(img_data, use_container_width=True)
        
        doc.close()
        
    except ImportError:
        st.warning("⚠️ PDF preview requires PyMuPDF. Install with: `pip install pymupdf`")
        st.info("You can still download the PDF using the button below.")
    except Exception as e:
        st.error(f"Error rendering PDF: {str(e)}")
        st.info("PDF preview unavailable. Please download to view.")


def main():
    # Custom CSS
    st.markdown("""
        <style>
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }
        .main-header {
            font-size: 2.8rem;
            font-weight: bold;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #888;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        /* Modern Progress Steps */
        .progress-container {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 10px 0;
        }
        .progress-step-card {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            border-radius: 12px;
            transition: all 0.3s ease;
            gap: 12px;
        }
        .progress-step-card.done {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border: 1px solid #28a745;
        }
        .progress-step-card.active {
            background: linear-gradient(135deg, #e8f4fd 0%, #d1e7fd 100%);
            border: 1px solid #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
            animation: pulse 2s infinite;
        }
        .progress-step-card.pending {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            opacity: 0.6;
        }
        .step-indicator {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            flex-shrink: 0;
        }
        .progress-step-card.done .step-indicator {
            background: #28a745;
            color: white;
        }
        .progress-step-card.active .step-indicator {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            animation: pulse-dot 1.5s infinite;
        }
        .progress-step-card.pending .step-indicator {
            background: #dee2e6;
            color: #6c757d;
        }
        .step-content {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .step-icon {
            font-size: 18px;
        }
        .step-label {
            font-size: 14px;
            font-weight: 500;
            color: #333;
        }
        .progress-step-card.pending .step-label {
            color: #6c757d;
        }
        .progress-step-card.active .step-label {
            color: #667eea;
            font-weight: 600;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.01); }
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .slide-preview {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
        }
        
        /* Subtle delete buttons in sidebar - no border/background */
        [data-testid="stSidebar"] [data-testid="stExpander"] button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #888 !important;
            padding: 0 !important;
            min-height: 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] button[kind="secondary"]:hover {
            color: #dc3545 !important;
            background: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for generation tracking
    if 'is_generating' not in st.session_state:
        st.session_state.is_generating = False
    if 'stop_generation' not in st.session_state:
        st.session_state.stop_generation = False
    
    # Load config and initialize LLM settings from config.yaml
    config_path = Path(__file__).parent / "config.yaml"
    if 'llm_model' not in st.session_state or 'llm_api_key' not in st.session_state:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        st.session_state.llm_model = config.get("default", {}).get("model", "")
        st.session_state.llm_api_key = config.get("default", {}).get("api_key", "")
    
    # Check if generation is in progress
    is_generating = st.session_state.is_generating
    
    # Header with logo only (centered)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/logo.png", use_container_width=True)
    st.markdown('<p class="sub-header" style="text-align: center;">Create stunning presentations with AI-powered content generation</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("assets/logo.png", width=80)
        st.markdown("## ⚙️ Settings")
        
        # Show generating indicator
        if is_generating:
            st.error("🔄 **Generating...**")
        
        num_slides = st.slider(
            "📊 Number of Slides", 
            min_value=5, 
            max_value=20, 
            value=10, 
            disabled=is_generating,
            key="num_slides_slider"
        )
        
        st.divider()
        
        # LLM Configuration
        st.markdown("### 🤖 LLM Settings")
        
        llm_model = st.text_input(
            "Model",
            value=st.session_state.llm_model,
            placeholder="openrouter/x-ai/grok-4.1-fast:free",
            help="LiteLLM model name (e.g., openrouter/x-ai/grok-4.1-fast:free, ollama/llama3)",
            disabled=is_generating,
            key="llm_model_input"
        )
        
        llm_api_key = st.text_input(
            "API Key",
            value=st.session_state.llm_api_key,
            type="password",
            placeholder="Enter your API key",
            help="API key for the selected model provider",
            disabled=is_generating,
            key="llm_api_key_input"
        )
        
        # Save button to update config
        if st.button("💾 Save LLM Config", disabled=is_generating, use_container_width=True):
            # Load existing config
            config_path = Path(__file__).parent / "config.yaml"
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Update all sections with new model and api_key
            config["default"]["model"] = llm_model
            config["default"]["api_key"] = llm_api_key
            
            for agent in config.get("agents", {}):
                config["agents"][agent]["model"] = llm_model
                config["agents"][agent]["api_key"] = llm_api_key
            
            for tool in config.get("tools", {}):
                config["tools"][tool]["model"] = llm_model
                config["tools"][tool]["api_key"] = llm_api_key
            
            # Write back to config file
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            # Update session state
            st.session_state.llm_model = llm_model
            st.session_state.llm_api_key = llm_api_key
            
            # Clear the config cache in config_loader
            import config_loader
            config_loader._config_cache = None
            
            st.success("✅ Config saved!")
        
        st.divider()
        
        st.markdown("### 📁 Upload Documents")
        uploaded_docs = st.file_uploader(
            "Choose documents",
            accept_multiple_files=True,
            type=['pdf', 'txt', 'docx', 'md'],
            help="Upload PDF, TXT, DOCX, or Markdown files",
            label_visibility="collapsed",
            disabled=is_generating,
            key="doc_uploader"
        )
        
        # Save uploaded documents to user_files
        if uploaded_docs:
            for f in uploaded_docs:
                save_uploaded_file(f, USER_FILES_DIR)
        
        # Show contents of user_files folder
        user_files_list = [f for f in os.listdir(USER_FILES_DIR) if os.path.isfile(os.path.join(USER_FILES_DIR, f))]
        if user_files_list:
            col_status, col_clear = st.columns([3, 2])
            with col_status:
                st.success(f"✅ {len(user_files_list)} document(s)")
            with col_clear:
                if st.button("🗑️ Clear All", key="clear_docs", disabled=is_generating):
                    for f in user_files_list:
                        os.remove(os.path.join(USER_FILES_DIR, f))
                    st.rerun()
            with st.expander("📄 View Documents", expanded=False):
                for f in user_files_list:
                    col_f, col_del = st.columns([6, 1])
                    with col_f:
                        st.caption(f"📄 {f}")
                    with col_del:
                        if st.button("✕", key=f"del_doc_{f}", disabled=is_generating, help="Delete"):
                            os.remove(os.path.join(USER_FILES_DIR, f))
                            st.rerun()
        
        st.markdown("### 🖼️ Upload Images")
        uploaded_images = st.file_uploader(
            "Choose images",
            accept_multiple_files=True,
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="Upload PNG, JPG, JPEG, or WebP images",
            label_visibility="collapsed",
            disabled=is_generating,
            key="img_uploader"
        )
        
        # Save uploaded images to user_images
        if uploaded_images:
            for f in uploaded_images:
                save_uploaded_file(f, USER_IMAGES_DIR)
        
        # Show contents of user_images folder
        user_images_list = [f for f in os.listdir(USER_IMAGES_DIR) if os.path.isfile(os.path.join(USER_IMAGES_DIR, f))]
        if user_images_list:
            col_status, col_clear = st.columns([3, 2])
            with col_status:
                st.success(f"✅ {len(user_images_list)} image(s)")
            with col_clear:
                if st.button("🗑️ Clear All", key="clear_imgs", disabled=is_generating):
                    for f in user_images_list:
                        os.remove(os.path.join(USER_IMAGES_DIR, f))
                    st.rerun()
            with st.expander("🖼️ View Images", expanded=False):
                for f in user_images_list:
                    col_f, col_del = st.columns([6, 1])
                    with col_f:
                        st.caption(f"🖼️ {f}")
                    with col_del:
                        if st.button("✕", key=f"del_img_{f}", disabled=is_generating, help="Delete"):
                            os.remove(os.path.join(USER_IMAGES_DIR, f))
                            st.rerun()
        
        st.divider()
        
        st.markdown("### 📊 Quick Stats")
        slides = get_slide_files()
        pdf_path = os.path.join(SLIDES_DIR, "presentation.pdf")
        pdf_exists = os.path.exists(pdf_path)
        
        col1, col2 = st.columns(2)
        col1.metric("Slides", len(slides))
        col2.metric("PDF", "✅" if pdf_exists else "❌")
        
        if pdf_exists:
            size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            st.caption(f"PDF Size: {size_mb:.1f} MB")
        
        st.divider()
        st.markdown("### ℹ️ About")
        st.caption("Presenter Generator Agent uses LangGraph and multiple AI agents to create beautiful presentations.")
        
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🎨 Create", "📄 Preview PDF", "📥 Download"])
    
    # ==================== CREATE TAB ====================
    with tab1:
        st.markdown("### 📝 Create Your Presentation")
        
        # Show generating status banner
        if is_generating:
            st.warning("⏳ **Generation in progress...** Please wait or click Stop to cancel.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            topic = st.text_area(
                "What should your presentation be about?",
                placeholder="Enter your presentation topic...\n\nExample: Create a presentation comparing open-weight LLM models, covering architecture differences, performance benchmarks, and real-world use cases.",
                height=200,
                label_visibility="collapsed",
                disabled=is_generating,
                key="topic_input"
            )
            
            source_url = st.text_input(
                "🔗 Source URL (optional)",
                placeholder="https://example.com/article-to-use-as-source",
                help="Provide a URL for the AI to research and use as source",
                disabled=is_generating,
                key="source_url_input"
            )
        
        with col2:
            # Get counts from folders
            docs_count = len([f for f in os.listdir(USER_FILES_DIR) if os.path.isfile(os.path.join(USER_FILES_DIR, f))])
            imgs_count = len([f for f in os.listdir(USER_IMAGES_DIR) if os.path.isfile(os.path.join(USER_IMAGES_DIR, f))])
            
            st.markdown("#### 📋 Summary")
            st.info(f"""
            **Slides:** {num_slides}  
            **Documents:** {docs_count}  
            **Images:** {imgs_count}  
            **Source:** {'URL provided' if source_url else 'Web research'}
            """)
        
        st.divider()
        
        # Generate and Stop buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_btn = st.button(
                "🚀 Generate Presentation",
                type="primary",
                use_container_width=True,
                disabled=not topic or is_generating
            )
        
        # Show stop button if generating
        if is_generating:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🛑 Stop Generation", type="secondary", use_container_width=True):
                    st.session_state.stop_generation = True
                    st.session_state.is_generating = False
                    st.warning("⚠️ Generation stopped by user.")
                    st.rerun()
        
        # Generation process
        if generate_btn and topic and not is_generating:
            # Validate URL and files first
            validation_passed = True
            
            # Check URL
            if source_url:
                with st.spinner("🔍 Checking URL accessibility..."):
                    url_valid, url_error = validate_url(source_url)
                    if not url_valid:
                        st.error(f"❌ **URL Error:** {url_error}")
                        validation_passed = False
                    else:
                        st.success("✅ URL is accessible")
            
            # Stop if validation failed
            if not validation_passed:
                st.warning("⚠️ Please fix the errors above and try again.")
                st.stop()
            
            # Set generating state
            st.session_state.is_generating = True
            st.session_state.stop_generation = False
            
            st.divider()
            st.markdown("### 🔄 Progress")
            
            # Progress UI elements
            steps_container = st.empty()
            
            # Create progress tracker
            tracker = ProgressTracker(steps_container)
            
            # Build task string
            task = f"create a {num_slides} slide ppt on {topic}"
            if source_url:
                task += f" use this link for your source: link:{source_url}"
            
            # Get file paths from user_files and user_images folders
            file_paths = []
            for f in os.listdir(USER_FILES_DIR):
                fpath = os.path.join(USER_FILES_DIR, f)
                if os.path.isfile(fpath):
                    file_paths.append(fpath)
            for f in os.listdir(USER_IMAGES_DIR):
                fpath = os.path.join(USER_IMAGES_DIR, f)
                if os.path.isfile(fpath):
                    file_paths.append(fpath)
            
            # Run generation
            try:
                state, pdf_path = asyncio.run(
                    run_generation_with_progress(task, file_paths, tracker)
                )
                
                # Reset generating state on success
                st.session_state.is_generating = False
                
                st.balloons()
                
                # Show summary
                with st.expander("📋 Generation Summary", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    slides = get_slide_files()
                    col1.metric("Slides Created", len(slides))
                    
                    if pdf_path and os.path.exists(pdf_path):
                        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                        col2.metric("PDF Size", f"{size_mb:.1f} MB")
                    
                    
                    st.success("🎉 Your presentation is ready! Check the Preview and Download tabs.")
                
            except Exception as e:
                # Reset generating state on error
                st.session_state.is_generating = False
                
                st.error(f"❌ An error occurred: {str(e)}")
                logging.error(f"Generation error: {e}")
                import traceback
                with st.expander("🔍 Error Details"):
                    st.code(traceback.format_exc())
    
    # ==================== PREVIEW PDF TAB ====================
    with tab2:
        st.markdown("### 📄 Preview PDF")
        
        pdf_path = os.path.join(SLIDES_DIR, "presentation.pdf")
        
        if not os.path.exists(pdf_path):
            st.info("📭 No PDF generated yet. Go to the **Create** tab to generate a presentation.")
        else:
            # PDF Preview
            render_pdf_preview(pdf_path)
            
            st.divider()
            
            # Quick download button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=f.read(),
                        file_name="presentation.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                        key="pdf_download_preview_tab"
                    )
    
    # ==================== DOWNLOAD TAB ====================
    with tab3:
        st.markdown("### 📥 Download Your Presentation")
        
        slides = get_slide_files()
        pdf_path = os.path.join(SLIDES_DIR, "presentation.pdf")
        
        if not slides:
            st.info("📭 No presentation available. Generate one first!")
        else:
            col1, col2 = st.columns(2)
            
            # PDF Download
            with col1:
                st.markdown("#### 📄 PDF Presentation")
                
                if os.path.exists(pdf_path):
                    st.success("✅ PDF Ready")
                    
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=f.read(),
                            file_name="presentation.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                            key="pdf_download_main"
                        )
                else:
                    st.warning("⚠️ PDF not generated yet")
            
            # HTML Download
            with col2:
                st.markdown("#### 🌐 HTML Slides")
                
                st.success(f"✅ {len(slides)} slides ready")
                
                # Create ZIP
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for slide in slides:
                        slide_path_zip = os.path.join(SLIDES_DIR, slide)
                        zf.write(slide_path_zip, slide)
                
                st.download_button(
                    label="⬇️ Download All (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="presentation_slides.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="zip_download_html"
                )
            
            st.divider()
            
            # Individual slides
            st.markdown("#### 📑 Individual Slides")
            
            cols = st.columns(5)
            for idx, slide in enumerate(slides):
                slide_num = slide[:-5]
                slide_path_ind = os.path.join(SLIDES_DIR, slide)
                
                with cols[idx % 5]:
                    with open(slide_path_ind, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    st.download_button(
                        label=f"Slide {slide_num}",
                        data=content,
                        file_name=f"slide_{slide_num}.html",
                        mime="text/html",
                        use_container_width=True,
                        key=f"dl_{slide_num}"
                    )


if __name__ == "__main__":
    main()
