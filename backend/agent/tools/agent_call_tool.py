from typing import Optional
from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema
from utils.logger import logger

class AgentCallTool(Tool):
    """Tool for calling another agent to continue the conversation.
    
    This tool allows agents to hand off the conversation to another agent
    by specifying the target agent's name. The actual agent switching happens
    on the frontend side.
    """

    def __init__(self, **kwargs):
        """Initialize the agent call tool."""
        super().__init__()

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "agent_call",
            "description": "Call another agent to continue the conversation. Use this when you need to hand off the conversation to a different agent with specific expertise.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "The name of the agent to call (e.g., 'Game Manager', 'Game Developer')"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message to pass to the next agent"
                    }
                },
                "required": ["agent_name"]
            }
        }
    })
    @xml_schema(
        tag_name="agent-call",
        mappings=[
            {"param_name": "agent_name", "node_type": "attribute", "path": ".", "required": True},
            {"param_name": "message", "node_type": "element", "path": "message", "required": False}
        ],
        example='''
        <function_calls>
        <invoke name="agent_call">
        <parameter name="agent_name">Game Manager</parameter>
        <parameter name="message">Please review the game design and provide feedback</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def agent_call(
        self, 
        agent_name: str, 
        message: Optional[str] = None
    ) -> ToolResult:
        """Call another agent to continue the conversation.

        Args:
            agent_name: Name of the agent to call
            message: Optional message to pass to the next agent

        Returns:
            ToolResult indicating the agent call was initiated
        """
        try:
            logger.info(f"Agent call initiated to: {agent_name}")
            
            # Create response data for frontend processing
            response_data = {
                "action": "agent_call",
                "target_agent": agent_name,
                "message": message or "",
                "status": "initiated"
            }
            
            return self.success_response(response_data)
            
        except Exception as e:
            logger.error(f"Error in agent_call: {str(e)}")
            return self.fail_response(f"Error calling agent: {str(e)}") 