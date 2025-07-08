# Complete Guide: Adding New Tools to Suna

This guide provides a comprehensive step-by-step process for adding new tools to the Suna codebase. The tool system in Suna is built around the AgentPress framework and consists of backend tool implementations, registration systems, and frontend UI components.

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Frontend Integration](#frontend-integration)
5. [Testing](#testing)
6. [Deployment Considerations](#deployment-considerations)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

## System Architecture Overview

### Core Components

The Suna tool system consists of several key components:

- **Tool Base Class** (`backend/agentpress/tool.py`) - Abstract base class for all tools
- **Tool Registry** (`backend/agentpress/tool_registry.py`) - Manages tool registration and discovery
- **Thread Manager** (`backend/agentpress/thread_manager.py`) - Handles tool addition via `add_tool()` method
- **Response Processor** (`backend/agentpress/response_processor.py`) - Executes tool calls
- **Frontend Tool Views** (`frontend/src/components/thread/tool-views/`) - UI components for tool display

### Tool Types

1. **Standard Tools** - Inherit from `Tool` base class
2. **Sandbox Tools** - Inherit from `SandboxToolsBase` for workspace operations
3. **MCP Tools** - External tools via Model Context Protocol

### Schema Types

Tools can define schemas using decorators:
- `@openapi_schema` - For LLM function calling
- `@xml_schema` - For XML-based tool invocation
- `@custom_schema` - For custom schema types

## Prerequisites

Before adding a new tool, ensure you have:

1. Understanding of the tool's purpose and functionality
2. Access to the Suna development environment
3. Basic knowledge of Python async programming
4. Familiarity with React/TypeScript for frontend components
5. Understanding of the existing tool patterns in the codebase

## Step-by-Step Implementation

### Step 1: Create the Backend Tool Implementation

#### 1.1 Create the Tool File

Create a new Python file in `backend/agent/tools/` directory:

```bash
touch backend/agent/tools/my_new_tool.py
```

#### 1.2 Implement the Tool Class

```python
from typing import Optional, Dict, Any, List
from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema
from utils.logger import logger

class MyNewTool(Tool):
    """Tool for [describe the tool's purpose].
    
    This tool provides [detailed description of capabilities].
    """

    def __init__(self, **kwargs):
        """Initialize the tool with required dependencies."""
        super().__init__()
        # Initialize any required dependencies
        # e.g., self.api_client = SomeAPIClient()

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "my_tool_function",
            "description": "Clear description of what this function does and when to use it",
            "parameters": {
                "type": "object",
                "properties": {
                    "parameter_name": {
                        "type": "string",
                        "description": "Description of this parameter"
                    },
                    "optional_param": {
                        "type": "string",
                        "description": "Optional parameter description"
                    }
                },
                "required": ["parameter_name"]
            }
        }
    })
    @xml_schema(
        tag_name="my-tool-function",
        mappings=[
            {"param_name": "parameter_name", "node_type": "attribute", "path": ".", "required": True},
            {"param_name": "optional_param", "node_type": "element", "path": "optional_param", "required": False}
        ],
        example='''
        <function_calls>
        <invoke name="my_tool_function">
        <parameter name="parameter_name">example_value</parameter>
        <parameter name="optional_param">optional_value</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def my_tool_function(
        self, 
        parameter_name: str, 
        optional_param: Optional[str] = None
    ) -> ToolResult:
        """Execute the main tool function.

        Args:
            parameter_name: Required parameter description
            optional_param: Optional parameter description

        Returns:
            ToolResult with execution results
        """
        try:
            logger.info(f"Executing my_tool_function with parameter: {parameter_name}")
            
            # Implement your tool logic here
            result = self._perform_tool_operation(parameter_name, optional_param)
            
            return self.success_response({
                "status": "success",
                "result": result,
                "message": "Tool executed successfully"
            })
            
        except Exception as e:
            logger.error(f"Error in my_tool_function: {str(e)}")
            return self.fail_response(f"Error executing tool: {str(e)}")

    def _perform_tool_operation(self, param1: str, param2: Optional[str] = None) -> Dict[str, Any]:
        """Private method to perform the actual tool operation."""
        # Implement your core logic here
        return {"operation": "completed", "input": param1}
```

#### 1.3 Follow Best Practices

- Use descriptive class and method names
- Include comprehensive docstrings
- Handle errors gracefully with try/catch blocks
- Use `self.success_response()` and `self.fail_response()` for consistent responses
- Log important operations for debugging
- Use type hints for all parameters and return values

### Step 2: Register the Tool in the Agent Runner

#### 2.1 Import the Tool

Add your tool import to `backend/agent/run.py`:

```python
from agent.tools.my_new_tool import MyNewTool
```

#### 2.2 Register the Tool

Add the tool registration logic in the appropriate section of `backend/agent/run.py`:

```python
# For tools that should always be available:
if enabled_tools is None:
    # Add to the section with other always-available tools
    thread_manager.add_tool(MyNewTool, **tool_specific_kwargs)

# For configurable tools:
else:
    if enabled_tools.get('my_new_tool', {}).get('enabled', False):
        thread_manager.add_tool(MyNewTool, **tool_specific_kwargs)
```

### Step 3: Add Frontend Configuration (If Configurable)

#### 3.1 Add to Frontend Tool Configuration

If your tool should be configurable by users, add it to `frontend/src/app/(dashboard)/agents/_data/tools.ts`:

```typescript
export const DEFAULT_AGENTPRESS_TOOLS: Record<string, { 
    enabled: boolean; 
    description: string; 
    icon: string; 
    color: string 
}> = {
    // ... existing tools
    'my_new_tool': { 
        enabled: false, 
        description: 'Clear description of what this tool does for users', 
        icon: '🔧', 
        color: 'bg-purple-100 dark:bg-purple-800/50' 
    },
};
```

#### 3.2 Add Display Name

Add a display name mapping in the same file:

```typescript
export const getToolDisplayName = (toolName: string): string => {
    const displayNames: Record<string, string> = {
        // ... existing mappings
        'my_new_tool': 'My Tool Name',
    };
    
    return displayNames[toolName] || toolName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};
```

### Step 4: Create Frontend Tool View (Optional)

#### 4.1 Create Tool View Component

Create a specialized frontend component in `frontend/src/components/thread/tool-views/`:

```bash
mkdir frontend/src/components/thread/tool-views/my-tool/
touch frontend/src/components/thread/tool-views/my-tool/MyToolView.tsx
```

#### 4.2 Implement the Component

```typescript
'use client'

import React from 'react';
import { ToolViewProps } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Wrench, CheckCircle, AlertTriangle } from 'lucide-react';
import { formatTimestamp, getToolTitle, extractToolData } from '../utils';
import { LoadingState } from '../shared/LoadingState';

export function MyToolView({
  name = 'my-tool-function',
  assistantContent,
  toolContent,
  assistantTimestamp,
  toolTimestamp,
  isSuccess = true,
  isStreaming = false,
}: ToolViewProps) {
  const toolTitle = getToolTitle(name);

  // Parse tool-specific data
  const { toolResult } = extractToolData(toolContent);

  return (
    <Card className="gap-0 flex border shadow-none border-t border-b-0 border-x-0 p-0 rounded-none flex-col h-full overflow-hidden bg-white dark:bg-zinc-950">
      <CardHeader className="h-14 bg-zinc-50/80 dark:bg-zinc-900/80 backdrop-blur-sm border-b p-2 px-4 space-y-2">
        <div className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/20">
              <Wrench className="w-5 h-5 text-purple-500 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-base font-medium text-zinc-900 dark:text-zinc-100">
                {toolTitle}
              </CardTitle>
            </div>
          </div>

          {!isStreaming && (
            <Badge
              variant="secondary"
              className={
                isSuccess
                  ? "bg-gradient-to-b from-emerald-200 to-emerald-100 text-emerald-700 dark:from-emerald-800/50 dark:to-emerald-900/60 dark:text-emerald-300"
                  : "bg-gradient-to-b from-rose-200 to-rose-100 text-rose-700 dark:from-rose-800/50 dark:to-rose-900/60 dark:text-rose-300"
              }
            >
              {isSuccess ? (
                <CheckCircle className="h-3.5 w-3.5" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5" />
              )}
              {isSuccess ? 'Completed' : 'Failed'}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0 h-full flex-1 overflow-hidden relative">
        {isStreaming ? (
          <LoadingState
            icon={Wrench}
            iconColor="text-purple-500 dark:text-purple-400"
            bgColor="bg-gradient-to-b from-purple-100 to-purple-50 shadow-inner dark:from-purple-800/40 dark:to-purple-900/60 dark:shadow-purple-950/20"
            title="Executing tool"
            filePath={name}
            showProgress={true}
          />
        ) : (
          <div className="p-4">
            {/* Render tool-specific content here */}
            <div className="space-y-4">
              {toolResult && (
                <div>
                  <h3 className="text-sm font-medium mb-2">Result</h3>
                  <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-3 rounded overflow-auto">
                    {JSON.stringify(toolResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        )}
      </CardContent>
    </Card>
  );
}
```

#### 4.3 Register the Tool View

Add your tool view to `frontend/src/components/thread/tool-views/wrapper/ToolViewRegistry.tsx`:

```typescript
import { MyToolView } from '../my-tool/MyToolView';

const defaultRegistry: ToolViewRegistryType = {
  // ... existing mappings
  'my-tool-function': MyToolView,
  
  'default': GenericToolView,
};
```

#### 4.4 Add Tool Display Names

Update `frontend/src/components/thread/utils.ts`:

```typescript
const TOOL_DISPLAY_NAMES = new Map([
  // ... existing mappings
  ['my-tool-function', 'My Tool Display Name'],
]);
```

### Step 5: Update Tool Title and Component Mappings

#### 5.1 Add to Tool Title Mapping

In `frontend/src/components/thread/tool-views/utils.ts`, add your tool to the title mapping:

```typescript
export function getToolTitle(toolName: string): string {
  const normalizedName = toolName.toLowerCase();

  const toolTitles: Record<string, string> = {
    // ... existing mappings
    'my-tool-function': 'My Tool Title',
  };

  // ... rest of function
}
```

#### 5.2 Add to Component Mapping

In the same file, add component mapping:

```typescript
export function getToolComponent(toolName: string): string {
  const normalizedName = toolName.toLowerCase();

  switch (normalizedName) {
    // ... existing cases
    case 'my-tool-function':
      return 'MyToolView';
    
    default:
      return 'GenericToolView';
  }
}
```

## Frontend Integration

### Tool View Design Patterns

1. **Use consistent styling** - Follow the established Card-based design
2. **Handle loading states** - Use LoadingState component for streaming
3. **Parse tool data** - Use extractToolData utility for consistent parsing
4. **Responsive design** - Ensure components work on different screen sizes
5. **Error handling** - Display errors gracefully with proper styling

### Common UI Components

- `Card`, `CardContent`, `CardHeader`, `CardTitle` - Main container structure
- `Badge` - Status indicators
- `LoadingState` - Streaming state display
- `ScrollArea` - Scrollable content areas
- Icons from `lucide-react` - Consistent iconography

## Testing

### Backend Testing

1. **Unit Tests** - Test individual tool methods
2. **Integration Tests** - Test tool registration and execution
3. **Error Handling** - Test error scenarios and edge cases

Example test structure:

```python
import asyncio
import pytest
from agent.tools.my_new_tool import MyNewTool

class TestMyNewTool:
    @pytest.fixture
    def tool_instance(self):
        return MyNewTool()

    @pytest.mark.asyncio
    async def test_my_tool_function_success(self, tool_instance):
        result = await tool_instance.my_tool_function("test_param")
        assert result.success == True
        assert "success" in result.output

    @pytest.mark.asyncio
    async def test_my_tool_function_error(self, tool_instance):
        # Test error scenarios
        result = await tool_instance.my_tool_function("")
        assert result.success == False
```

### Frontend Testing

1. **Component Tests** - Test tool view rendering
2. **Interaction Tests** - Test user interactions
3. **State Management** - Test loading and error states

### Manual Testing

1. **Register the tool** in an agent configuration
2. **Create a test thread** and invoke the tool
3. **Verify frontend display** of tool execution
4. **Test error scenarios** to ensure proper error handling

## Deployment Considerations

### Environment Variables

If your tool requires configuration:

1. Add environment variables to the appropriate config files
2. Document required environment variables
3. Add default values where appropriate

### Dependencies

1. **Backend dependencies** - Add to `requirements.txt` or `pyproject.toml`
2. **Frontend dependencies** - Add to `package.json`
3. **System dependencies** - Document in deployment guides

### Database Migrations

If your tool requires database changes:

1. Create appropriate migration files
2. Test migrations in development
3. Document any required schema changes

## Examples

### Simple API Tool Example

```python
class WeatherTool(Tool):
    """Tool for getting weather information."""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location"
                    }
                },
                "required": ["location"]
            }
        }
    })
    async def get_weather(self, location: str) -> ToolResult:
        try:
            # API call logic here
            weather_data = await self._fetch_weather(location)
            return self.success_response(weather_data)
        except Exception as e:
            return self.fail_response(f"Failed to get weather: {str(e)}")
```

### Sandbox Tool Example

```python
from sandbox.tool_base import SandboxToolsBase

class CustomSandboxTool(SandboxToolsBase):
    """Tool for custom sandbox operations."""

    def __init__(self, project_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "sandbox_operation",
            "description": "Perform operation in sandbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    })
    async def sandbox_operation(self, command: str) -> ToolResult:
        try:
            await self._ensure_sandbox()
            result = self.sandbox.process.exec(command)
            return self.success_response({
                "exit_code": result.exit_code,
                "output": result.output
            })
        except Exception as e:
            return self.fail_response(f"Sandbox operation failed: {str(e)}")
```

## Troubleshooting

### Common Issues

1. **Tool not appearing in agent** - Check registration in `run.py`
2. **Schema validation errors** - Verify OpenAPI schema format
3. **Frontend not displaying** - Check ToolViewRegistry registration
4. **Import errors** - Verify all dependencies are installed

### Debugging Tips

1. **Use logging** - Add logger statements for debugging
2. **Check console output** - Monitor both backend and frontend logs
3. **Test incrementally** - Test each component separately
4. **Use debugger** - Set breakpoints in critical sections

### Performance Considerations

1. **Async operations** - Use async/await for I/O operations
2. **Resource cleanup** - Properly clean up resources
3. **Error handling** - Don't let exceptions crash the system
4. **Memory usage** - Be mindful of memory consumption

## Conclusion

Adding new tools to Suna involves:

1. **Backend implementation** - Create tool class with proper schemas
2. **Registration** - Add tool to agent runner
3. **Frontend integration** - Create UI components and register views
4. **Testing** - Thoroughly test all components
5. **Documentation** - Document usage and configuration

Following this guide ensures your tools integrate seamlessly with the Suna platform and provide a consistent user experience.

Remember to:
- Follow existing code patterns and conventions
- Test thoroughly before deployment
- Document any special requirements or configuration
- Consider performance and security implications
- Update relevant documentation and help text 