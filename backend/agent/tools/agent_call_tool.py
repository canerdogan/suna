from typing import Optional
from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema
from utils.logger import logger

class AgentCallTool(Tool):
    """Tool for calling another agent to continue the conversation.
    
    This tool allows agents to hand off the conversation to another agent
    by specifying the target agent's name. The tool will terminate the current
    agent run and trigger agent switching on the frontend.
    """

    def __init__(self, **kwargs):
        """Initialize the agent call tool."""
        super().__init__()

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "agent_call",
            "description": "Call another agent to continue the conversation. Use this to hand off the conversation to a different agent when their expertise is needed. The target agent will receive the conversation context and continue from where this agent left off. This tool automatically terminates the current agent run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The unique ID of the agent to call. CRITICAL: Use the exact agent_id from the available agents list in the system prompt. The agent_id is case-sensitive and must be used exactly as displayed without any modifications."
                    },
                    "handoff_message": {
                        "type": "string",
                        "description": "Optional message to send to the target agent explaining the context or what needs to be done."
                    }
                },
                "required": ["agent_id"]
            }
        }
    })
    @xml_schema(
        tag_name="agent-call",
        mappings=[
            {"param_name": "agent_id", "node_type": "attribute", "path": "."},
            {"param_name": "handoff_message", "node_type": "content", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="agent_call">
        <parameter name="agent_id">agent_abc123</parameter>
        <parameter name="handoff_message">I've completed the market research. Here are the findings: [research summary]. Please proceed with the game design documentation.</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def agent_call(self, agent_id: str, handoff_message: Optional[str] = None) -> ToolResult:
        """Call another agent to continue the conversation.
        
        Args:
            agent_id: The unique ID of the agent to call (case-sensitive, must be exact)
            handoff_message: Optional message to send to the target agent
            
        Returns:
            ToolResult indicating the agent call was initiated and current agent should terminate
        """
        # Validate that agent_id is provided and not empty
        if not agent_id or not agent_id.strip():
            logger.error("Agent call failed: agent_id is empty or missing")
            return ToolResult(
                output={
                    "action": "agent_call",
                    "error": "agent_id is required and cannot be empty",
                    "status": "failed"
                },
                success=False
            )
        
        # Use the agent_id exactly as provided (no modifications)
        exact_agent_id = agent_id.strip()
        logger.info(f"🚨 AGENT CALL TOOL EXECUTED! exact_agent_id='{exact_agent_id}', handoff_message={handoff_message}")
        print(f"🚨 AGENT CALL TOOL EXECUTED! exact_agent_id='{exact_agent_id}', handoff_message={handoff_message}")
        
        # Return success result - agent termination will be handled automatically
        # by the response processor since agent_call is now a terminating tool
        result = ToolResult(
            output={
                "action": "agent_call",
                "target_agent_id": exact_agent_id,
                "message": handoff_message,
                "status": "success"
            },
            success=True
        )
        
        logger.info(f"🎯 AGENT CALL RESULT: {result.output}")
        print(f"🎯 AGENT CALL RESULT: {result.output}")
        
        return result 