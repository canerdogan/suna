# GameByte Project: Detailed Technical Changelog & Suna Base Comparison
## Version 2.1

### 1. Introduction & LLM Agent Instructions

**To the Developer/LLM Agent:** This document is your primary guide for understanding the technical differences between the **Suna** project (the upstream base) and the **GameByte** project (the customized fork). Your task during a code merge is to use this document to correctly integrate new changes from Suna without breaking GameByte's unique features.

**Core Principles for Merging:**
1.  **GameByte's Features are Priority:** GameByte-specific additions, such as the Agent Communication Framework and Asset Generation Tools, are the project's core value. They must be preserved in their entirety.
2.  **Intentional Divergence:** GameByte has intentionally modified or replaced some Suna systems (e.g., feature flags, LLM provider routing). This changelog is the source of truth for these divergences. Do not revert GameByte's intentional changes.
3.  **Analyze Conflicts:** When both projects modify the same file, this document will provide a **Merge Directive**. Follow it carefully. If a conflict is not covered here, flag it for human review.
4.  **Code is Truth:** The code snippets provided herein are the ground truth for GameByte's implementation.

---

### 2. GameByte Core Feature Layer (Exclusive Additions)

These features are new and exist **only** in the GameByte project.

#### 2.1. Multi-Agent Communication Framework

**High-Level Goal:** To allow agents to delegate tasks to other, more specialized agents.

**Step 1: The `AgentCallTool`**
-   **File Added:** `backend/agent/tools/agent_call_tool.py`
-   **Purpose:** A new, terminating tool that allows an agent to end its current task and hand off the conversation to another agent.
-   **Merge Directive:** **DO NOT REMOVE.** This file is critical for GameByte's multi-agent functionality.
-   **Code Implementation:**
    ```python
    # File: backend/agent/tools/agent_call_tool.py
    from typing import Optional
    from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema
    from utils.logger import logger

    class AgentCallTool(Tool):
        """Tool for calling another agent to continue the conversation..."""
        # ... (constructor) ...
        @openapi_schema({
            "type": "function",
            "function": {
                "name": "agent_call",
                "description": "Call another agent... CRITICAL: Use the exact agent_id...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The unique ID of the agent to call..."
                        },
                        "handoff_message": {
                            "type": "string",
                            "description": "Optional message to send to the target agent..."
                        }
                    },
                    "required": ["agent_id"]
                }
            }
        })
        async def agent_call(self, agent_id: str, handoff_message: Optional[str] = None) -> ToolResult:
            if not agent_id or not agent_id.strip():
                # ... error handling ...
            
            exact_agent_id = agent_id.strip()
            logger.info(f"🚨 AGENT CALL TOOL EXECUTED! ...")
            
            result = ToolResult(
                output={
                    "action": "agent_call",
                    "target_agent_id": exact_agent_id,
                    "message": handoff_message,
                    "status": "success"
                },
                success=True
            )
            return result
    ```

**Step 2: Dynamic Agent Directory in System Prompt**
-   **File Modified:** `backend/agentpress/thread_manager.py`
-   **Purpose:** To inform the active LLM about which other agents are available for delegation via the `agent_call` tool.
-   **Merge Directive:** **PRIORITY: GameByte.** Suna's changes to `thread_manager.py` must be carefully merged to preserve the `_add_available_agents_to_system_prompt` method and its call within `run_thread`.
-   **Code Implementation:**
    ```python
    # Added to backend/agentpress/thread_manager.py

    async def _add_available_agents_to_system_prompt(self, working_system_prompt: Dict[str, Any], thread_id: str):
        """Add available agents list to system prompt for agent_call tool."""
        try:
            # ... (fetches agents from database) ...
            agents_info = """
# 🤖 AVAILABLE AGENTS FOR AGENT_CALL TOOL
You have access to the following agents that you can call using the agent_call tool.
## ⚠️ CRITICAL INSTRUCTIONS FOR AGENT IDs:
- Agent IDs are 36-character UUIDs...
- You MUST copy the agent_id EXACTLY as shown below...
## 📋 AGENT DIRECTORY:
"""
            for i, agent_data in enumerate(agents_result.data, 1):
                # ... (builds the directory string) ...
            
            # ... (appends the directory to the system prompt content) ...
        except Exception as e:
            logger.warning(f"Failed to fetch available agents for system prompt: {e}")

    async def run_thread(self, ...):
        # ...
        working_system_prompt = system_prompt.copy()

        # ADDED LINE:
        await self._add_available_agents_to_system_prompt(working_system_prompt, thread_id)

        if include_xml_examples and config.xml_tool_calling:
            # ...
    ```

**Step 3: Making `agent_call` a Terminating Tool**
-   **File Modified:** `backend/agentpress/response_processor.py`
-   **Purpose:** To ensure the current agent stops processing after calling another agent.
-   **Merge Directive:** **PRIORITY: GameByte.** Suna's changes must be merged around this logic. The string `'agent_call'` must be included in all checks for terminating tools.
-   **Code Implementation:**
    ```python
    # Modified in backend/agentpress/response_processor.py
    
    # Example 1 (of 3 similar changes in the file)
    if tool_name in ['ask', 'complete', 'agent_call']:
        logger.info(f"Terminating tool '{tool_name}' completed during streaming...")
        agent_should_terminate = True
    ```

#### 2.2. AI Asset Generation Tool

**High-Level Goal:** To enable agents to create images and game assets from text prompts.

-   **File Added:** `backend/agent/tools/sb_asset_generator_tool.py`
-   **Purpose:** Provides a tool for generating images using external AI providers.
-   **Merge Directive:** **DO NOT REMOVE.** This is a core GameByte feature.
-   **Code Implementation:**
    ```python
    # File: backend/agent/tools/sb_asset_generator_tool.py
    import os
    import base64
    from sandbox.tool_base import SandboxToolsBase
    from utils.config import config
    from agentpress.tool import ToolResult, openapi_schema

    class SandboxAssetGeneratorTool(SandboxToolsBase):
        # ... (constructor) ...
        @property
        def is_available(self) -> bool:
            gemini_available = bool(config.GEMINI_API_KEY)
            # ... (other provider checks) ...
            return gemini_available or eachlabs_available

        @openapi_schema({ "name": "generate_asset", ... })
        async def generate_asset(self, prompt: str, ...):
            try:
                if not config.GEMINI_API_KEY:
                    return self.fail_response("Error: Google AI API key not configured...")
                
                from google import genai
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                
                result = client.models.generate_images(
                    model="models/imagen-4.0-generate-preview-06-06",
                    prompt=prompt,
                    ...
                )
                
                # ... (processes images and uploads to sandbox) ...
                file_urls = []
                for i, image in enumerate(result._result.images):
                    # ...
                    file_url = await self.sandbox.fs.upload_file(...)
                    file_urls.append(file_url)
                
                return self.success_response(f"✅ **Image Generated Successfully!**...")
            except Exception as e:
                return self.fail_response(f"Error generating image: {str(e)}")
        
        # NOTE: The file also contains commented-out placeholders for 
        # generate_2d_asset and generate_3d_asset, indicating future work.
    ```

---

### 3. Architectural Divergences (GameByte's Modifications to Suna's Code)

These are intentional changes where GameByte's architecture and implementation differ from Suna's.

#### 3.1. Direct LLM Provider Integration (Google Gemini)

-   **File Modified:** `backend/services/llm.py`
-   **Change:** GameByte removed the dependency on OpenRouter for Google models and now connects directly to the Gemini API via `litellm`.
-   **Reason:** To gain direct control over the API, improve logging, and reduce external dependencies.
-   **Merge Directive:** **PRIORITY: GameByte.** This is a deliberate architectural choice. Do not revert to the OpenRouter implementation for Gemini models. Preserve the `StructlogLiteLLMHandler` and the direct `GEMINI_API_KEY` setup.
-   **Code Implementation:**
    ```python
    # Added to backend/services/llm.py
    from litellm.integrations.custom_logger import CustomLogger

    class StructlogLiteLLMHandler(CustomLogger):
        # ... (detailed logging for pre-call, success, and failure) ...

    _llm_logger = StructlogLiteLLMHandler()
    litellm.callbacks = [_llm_logger]

    # Modified in backend/services/llm.py
    def setup_api_keys() -> None:
        providers = ['OPENAI', 'ANTHROPIC', 'GROQ', 'OPENROUTER', 'GEMINI'] # 'GEMINI' was added
        # ...
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
    
    # Modified in backend/utils/constants.py
    MODEL_NAME_ALIASES = {
        # Suna version: "google/gemini-2.5-pro": "openrouter/google/gemini-2.5-pro",
        "google/gemini-2.5-pro": "gemini/gemini-2.5-pro", # GameByte version
    }
    ```

#### 3.2. Feature Flag System Deactivation

-   **File Modified:** `backend/flags/flags.py`
-   **Change:** The feature flag check is hardcoded by GameByte to always return `True`.
-   **Reason:** To simplify the development environment by ensuring all features are always enabled, removing the need for a configured Redis instance for this purpose.
-   **Merge Directive:** **CONFLICT / DIVERGENCE.** This is a major architectural difference. Suna's implementation is dynamic and Redis-based. GameByte's is static. **Action:** Retain the GameByte implementation (`return True;`). If a new feature from Suna depends heavily on the dynamic flag system, it will require manual adaptation to work within the GameByte architecture.
-   **Code Implementation:**
    ```python
    # Modified in backend/flags/flags.py
    class FeatureFlagManager:
        async def is_enabled(self, key: str) -> bool:
            """Check if a feature flag is enabled"""
            try:
                return True # <-- GameByte's static implementation
                # The original Suna implementation using redis_client is bypassed.
            except Exception:
                return False
    ```

#### 3.3. MCP (Model Context Protocol) for Local Tools

-   **File Modified:** `backend/mcp_service/mcp_custom.py`
-   **Change:** GameByte added support for a new MCP server type: `'json'`.
-   **Reason:** To allow agents to use local scripts or command-line tools as if they were remote APIs, which is extremely useful for game development workflows (e.g., running a build script).
-   **Merge Directive:** **PRIORITY: GameByte.** This is a new feature. If Suna modifies this file, their changes must be merged carefully to preserve the `'json'` type handling logic.
-   **Code Implementation:**
    ```python
    # Added to backend/mcp_service/mcp_custom.py
    from mcp.client.stdio import stdio_client, StdioServerParameters # type: ignore

    async def discover_custom_tools(request_type: str, config: Dict[str, Any]):
        # ... (existing http and sse logic)
        elif request_type == 'json':
            if 'command' not in config:
                raise HTTPException(status_code=400, detail="JSON configuration must include 'command' field")
            
            server_params = StdioServerParameters(
                command=config['command'],
                args=config.get('args', []),
                env=config.get('env', {})
            )
            
            async with stdio_client(server_params) as (read, write):
                # ... (logic to list tools from the stdio client)
        else:
            raise HTTPException(status_code=400, detail="Invalid server type. Must be 'http', 'sse', or 'json'")
    ```

---

### 4. Configuration and Dependency Changes (GameByte-Specific)

-   **New Dependencies:**
    -   **File:** `backend/pyproject.toml`
    -   **Change:** Added `google-genai>=1.24.0`.
    -   **Merge Directive:** Retain this dependency; it is required for the `SandboxAssetGeneratorTool`.

-   **New Configuration Variables:**
    -   **File:** `backend/utils/config.py`
    -   **Change:** Added the following to the `Configuration` class:
        ```python
        GEMINI_API_KEY: Optional[str] = None
        EACHLABS_API_KEY: Optional[str] = None
        EACHLABS_2D_ASSET_WORKFLOW_ID: Optional[str] = None
        EACHLABS_3D_ASSET_WORKFLOW_ID: Optional[str] = None
        ```
    -   **Merge Directive:** Retain these variables.

-   **Docker Environment:**
    -   **File:** `backend/sandbox/docker/docker-compose.yml`
    -   **Change:** The new API keys are passed as environment variables to the sandbox service.
    -   **Merge Directive:** Retain these environment variable passthroughs.
