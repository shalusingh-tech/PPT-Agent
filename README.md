# 🎯 PPT Agent - AI-Powered Presentation Generator

An intelligent presentation generator that uses AI agents to create professional HTML/PDF presentations from your documents, URLs, or topics.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51+-red.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 🤖 **Multi-Agent Architecture** - Uses specialized AI agents for research, file understanding, outline creation, and slide generation
- 📄 **Document Support** - Upload PDFs and documents to generate presentations from your content
- 🌐 **Web Research** - Provide URLs or topics for the AI to research and create presentations
- 🖼️ **Image Support** - Include your own images in the presentation
- 📊 **Beautiful HTML Slides** - Generates responsive, professional HTML slides
- 📑 **PDF Export** - Automatically converts slides to high-quality PDF
- ⚙️ **Configurable LLMs** - Support for multiple LLM providers (OpenRouter, Groq, Ollama, etc.)
- 🎨 **Live Preview** - View and navigate through slides in the web interface

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                               │
│              (Topic/URL + Documents + Images)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Router                                  │
│                (Decides processing path)                         │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
          Has Files │                       │ No Files
                    ▼                       ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │   File Understanding  │   │   Researcher Agent    │
    │        Agent          │   │   (Web Search with    │
    │  (PDF/Doc Analysis)   │   │      Tavily)          │
    └───────────────────────┘   └───────────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
            ┌───────────────────────────────────┐
            │       Outline Creation Agent      │
            │    (Structures the content)       │
            └───────────────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────┐
            │       Presentation Agent          │
            │   (Creates HTML slides using      │
            │      create_slide tool)           │
            └───────────────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────┐
            │         PDF Converter             │
            │    (Html2Image + Pillow)          │
            └───────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Output                                      │
│              (HTML Slides + PDF + ZIP Download)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Descriptions

| Agent | Purpose |
|-------|---------|
| **Router** | Determines if user has files or needs web research |
| **File Understanding Agent** | Reads and summarizes uploaded documents |
| **Researcher Agent** | Searches the web using Tavily for topic research |
| **Outline Creation Agent** | Creates structured presentation outline |
| **Presentation Agent** | Generates HTML slides from the outline |

## 📁 Project Structure

```
PPT-Agent/
├── app.py                      # Main Streamlit application
├── config.yaml                 # LLM configuration (create from example)
├── config.yaml.example         # Example configuration template
├── config_loader.py            # Configuration loader utility
├── convert_pdf_html2image.py   # HTML to PDF converter
├── logger.py                   # Logging configuration
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create from example)
├── .env.example                # Example environment template
│
├── agents/                     # AI Agent definitions
│   ├── understand_files.py     # File understanding agent
│   ├── researcher_agent.py     # Web research agent
│   ├── outline_creation_agent.py # Outline creation agent
│   ├── presentation_agent.py   # Slide creation agent
│   └── presentation_agent_graph.py # LangGraph workflow
│
├── agent_tools/                # Tools used by agents
│   ├── files_tools.py          # Document/image processing tools
│   ├── researcher_tool.py      # Tavily web search tool
│   ├── outline_agent_tool.py   # Outline generation tool
│   └── presentation_agent_tool.py # Slide creation tool
│
├── agent_prompts/              # System prompts for agents
│   ├── file_agent_prompt.py
│   ├── researcher_prompt.py
│   ├── outline_agent_prompt.py
│   ├── presentation_agent_prompt.py
│   ├── summarizer_prompts.py
│   └── img_description_prompt.py
│
├── assets/                     # Static assets (logo, etc.)
├── slides/                     # Generated slides output
├── user_files/                 # Uploaded documents
├── user_images/                # Uploaded images
└── files/                      # Temporary processing files
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Chrome/Chromium browser (for PDF generation)
- API keys for:
  - [OpenRouter](https://openrouter.ai/) (or other LLM provider)
  - [Tavily](https://tavily.com/) (for web search)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/shalusingh-tech/PPT-Agent.git
   cd PPT-Agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (for PDF generation)
   ```bash
   playwright install chromium
   ```

5. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your API keys
   ```

   Required keys in `.env`:
   ```env
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

6. **Configure LLM settings**
   ```bash
   # Copy the example file
   cp config.yaml.example config.yaml
   
   # Edit config.yaml and add your API key
   ```

   Update `config.yaml` with your OpenRouter API key:
   ```yaml
   default:
     model: openrouter/x-ai/grok-4.1-fast:free
     api_key: YOUR_OPENROUTER_API_KEY
     temperature: 0.7
   ```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Configure your API keys**
   ```bash
   # Copy example files
   cp .env.example .env
   cp config.yaml.example config.yaml
   
   # Edit .env and config.yaml with your API keys
   ```

2. **Build and run**
   ```bash
   docker-compose up --build
   ```

3. **Access the app** at `http://localhost:8501`

### Using Docker CLI

```bash
# Build the image
docker build -t ppt-agent .

# Run the container
docker run -p 8501:8501 \
  -e TAVILY_API_KEY=your_tavily_key \
  -v ./config.yaml:/app/config.yaml:ro \
  ppt-agent
```

### Docker Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TAVILY_API_KEY` | Yes | API key for web search |
| `LANGSMITH_TRACING` | No | Enable LangSmith tracing (`true`/`false`) |
| `LANGSMITH_API_KEY` | No | LangSmith API key |
| `LANGSMITH_PROJECT` | No | LangSmith project name |

### Docker Volumes

The `docker-compose.yml` mounts these volumes:
- `./config.yaml:/app/config.yaml` - LLM configuration
- `./output/slides:/app/slides` - Generated slides persist here
- `./output/files:/app/files` - Temporary files

## 📖 Usage

1. **Enter a Topic or URL**
   - Type a topic like "Artificial Intelligence in Healthcare"
   - Or provide a URL for the AI to research

2. **Upload Documents** (Optional)
   - Upload PDF files that you want to base the presentation on
   - The AI will extract and summarize the content

3. **Upload Images** (Optional)
   - Add images to be included in the presentation

4. **Set Number of Slides**
   - Choose how many slides you want (default: 10)

5. **Configure LLM** (Optional)
   - Adjust the model and API key in the sidebar if needed

6. **Generate Presentation**
   - Click "Generate Presentation" and watch the AI work
   - View progress in real-time

7. **Download Results**
   - Preview slides in the browser
   - Download individual slides or the complete PDF
   - Export all files as a ZIP

## ⚙️ Configuration

### LLM Providers

The app supports multiple LLM providers through LiteLLM:

| Provider | Model Format Example |
|----------|---------------------|
| OpenRouter | `openrouter/x-ai/grok-4.1-fast:free` |
| Groq | `groq/llama-3.3-70b-versatile` |
| Ollama | `ollama/llama3.2` |
| OpenAI | `openai/gpt-4` |
| Google | `gemini/gemini-pro` |

### Customizing Agents

Each agent can use a different model. Edit `config.yaml`:

```yaml
agents:
  researcher:
    model: openrouter/x-ai/grok-4.1-fast:free
    api_key: YOUR_API_KEY
    temperature: 0
  presentation:
    model: groq/llama-3.3-70b-versatile
    api_key: YOUR_GROQ_KEY
    temperature: 0.7
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| PDF generation fails | Ensure Playwright Chromium is installed: `playwright install chromium` |
| Web search not working | Check your `TAVILY_API_KEY` in `.env` |
| LLM errors | Verify your API key in `config.yaml` is correct |
| Import errors | Make sure all dependencies are installed: `pip install -r requirements.txt` |

### Logs

Check `ppt_creation.log` for detailed logs and error messages.

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **AI Framework**: LangChain, LangGraph
- **LLM Integration**: LiteLLM (supports multiple providers)
- **Web Search**: Tavily
- **Document Processing**: PyMuPDF, PyPDF2
- **PDF Generation**: Html2Image, Pillow
- **Async**: asyncio, aiofiles

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the AI framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- [Streamlit](https://streamlit.io/) for the web interface
- [Tavily](https://tavily.com/) for web search capabilities
- [OpenRouter](https://openrouter.ai/) for LLM access

---

Made with ❤️ by [Shalu Singh](https://github.com/shalusingh-tech)
