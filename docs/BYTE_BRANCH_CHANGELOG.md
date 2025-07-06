# Byte Branch Changelog (Changes Since `latest`)

## 1. Introduction

This document details all new features, modifications, and architectural changes introduced in the `byte` branch that are not present in the `latest` branch. It serves as a technical guide for developers and LLM agents to understand the specific contributions made in this branch.

---

## 2. Core Feature Enhancements

### 2.1. Agent-to-Agent Communication (`AgentCallTool`)

This is a major new feature enabling agents to delegate tasks to one another.

-   **New File:** `backend/agent/tools/agent_call_tool.py`
    -   Introduces the `AgentCallTool`, a tool that allows an agent to hand off a conversation to another agent by its ID.

-   **New File:** `frontend/src/app/(dashboard)/projects/[projectId]/thread/_hooks/useAgentCall.ts`
    -   A new React hook that manages the frontend logic for agent-to-agent calls, including stopping the current agent's stream and initiating a new one with the target agent.

-   **File Modified:** `backend/agentpress/thread_manager.py`
    -   A new method, `_add_available_agents_to_system_prompt`, was added to dynamically inject a list of callable agents into the system prompt, making the feature accessible to the LLM.

-   **File Modified:** `frontend/src/hooks/useAgentStream.ts`
    -   The hook was updated to include an `onAgentCall` callback, which is triggered when the backend sends an `agent_call` tool message.

### 2.2. AI-Powered Asset Generation

This feature introduces a powerful, multi-provider tool for creating visual assets.

-   **New File:** `backend/agent/tools/sb_asset_generator_tool.py`
    -   Introduces the `SandboxAssetGeneratorTool`, which can generate images using Google Imagen 4 and is designed to be extensible for other services like Eachlabs.

-   **New File:** `frontend/src/components/thread/tool-views/asset-generation/AssetGenerationToolView.tsx`
    -   A new UI component to display the results and status of the asset generation tool.

-   **File Modified:** `backend/agent/run.py`
    -   The `SandboxAssetGeneratorTool` is now conditionally registered with the agent, replacing the older `SandboxImageEditTool`.

## 3. Architectural and State Management Refinements

### 3.1. Centralized Frontend State Management

-   **File Modified:** `frontend/src/app/(dashboard)/projects/[projectId]/thread/[threadId]/page.tsx`
    -   This component has been refactored to be the single source of truth for chat-related state, including the selected model, `thinkingEnabled`, and `reasoningEffort`.
    -   **Reason:** This change was critical to ensure that user settings are preserved seamlessly when an agent-to-agent handoff occurs.

-   **File Modified:** `frontend/src/components/thread/chat-input/chat-input.tsx`
    -   This component was updated to be a "controlled" component, receiving its state via props from the parent `page.tsx` rather than managing it internally. This supports the centralized state model.

### 3.2. Direct Google Gemini Integration

-   **File Modified:** `backend/utils/constants.py`
    -   The model alias for `google/gemini-2.5-pro` was changed to point directly to `gemini/gemini-2.5-pro`, removing the `openrouter/` prefix. This reflects a strategic shift to a direct integration.

-   **File Modified:** `backend/agent/api.py`
    -   The model used for generating project names has been updated to a direct Gemini model for consistency.

## 4. New Documentation and UI Components

-   **New File:** `docs/Tool_System_Guide.md`
    -   A comprehensive guide for developers on how to create and integrate new tools into the system.

-   **New File:** `frontend/src/components/thread/status-message.tsx`
    -   A new, reusable UI component for displaying various status messages within the chat interface.

-   **New File:** `MERGE_GUIDE_main_to_byte.md`
    -   A detailed guide created to assist with the complex task of merging the `main` branch into `byte`, documenting all key differences and merge strategies.

---

This document provides a clear overview of the value-added features and architectural improvements that define the `byte` branch. All changes listed are unique to this branch and should be preserved during any future code merges.