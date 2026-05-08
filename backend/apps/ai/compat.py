import os


try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    END = START = StateGraph = None
    LANGGRAPH_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI

    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    ChatOpenAI = None
    LANGCHAIN_OPENAI_AVAILABLE = False

try:
    from langchain_core.documents import Document

    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    Document = None
    LANGCHAIN_CORE_AVAILABLE = False

try:
    import langchain  # noqa: F401

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import langchain_community  # noqa: F401

    LANGCHAIN_COMMUNITY_AVAILABLE = True
except ImportError:
    LANGCHAIN_COMMUNITY_AVAILABLE = False

try:
    import langchain_mcp_adapters  # noqa: F401

    LANGCHAIN_MCP_ADAPTERS_AVAILABLE = True
except ImportError:
    LANGCHAIN_MCP_ADAPTERS_AVAILABLE = False

try:
    from mcp import __version__ as MCP_VERSION

    MCP_AVAILABLE = True
except ImportError:
    MCP_VERSION = ""
    MCP_AVAILABLE = False

try:
    import chromadb  # noqa: F401

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


def ai_model_env_ready():
    return bool(os.getenv("AI_API_KEY", "").strip()) and bool(os.getenv("AI_MODEL", "").strip())


def build_runtime_capabilities():
    return {
        "langgraph_available": LANGGRAPH_AVAILABLE,
        "langchain_openai_available": LANGCHAIN_OPENAI_AVAILABLE,
        "langchain_core_available": LANGCHAIN_CORE_AVAILABLE,
        "langchain_available": LANGCHAIN_AVAILABLE,
        "langchain_community_available": LANGCHAIN_COMMUNITY_AVAILABLE,
        "langchain_mcp_adapters_available": LANGCHAIN_MCP_ADAPTERS_AVAILABLE,
        "mcp_available": MCP_AVAILABLE,
        "chroma_available": CHROMA_AVAILABLE,
        "ai_model_env_ready": ai_model_env_ready(),
        "preferred_runtime": "langgraph" if LANGGRAPH_AVAILABLE else "pipeline",
        "mcp_version": MCP_VERSION,
        "model_name": os.getenv("AI_MODEL", "").strip(),
    }
