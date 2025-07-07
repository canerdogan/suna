import asyncio
from typing import Dict, Any, Optional
from agentpress.tool import Tool
from utils.logger import logger
import structlog
import uuid

class AgentCallTool(Tool):
    """Tool for calling another agent and handing off the conversation."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def get_function_definitions(self) -> Dict[str, Any]:
        return {
            "agent_call": {
                "type": "function",
                "function": {
                    "name": "agent_call",
                    "description": """Call another agent to handle a specific task or expertise area. This will hand off the conversation to the specified agent.

⚠️ CRITICAL AGENT ID REQUIREMENTS:
1. You MUST use the EXACT agent_id as provided in the system prompt's AVAILABLE AGENTS section
2. The agent_id is a 36-character UUID format (e.g., 16bf42b5-c9de-4fb1-85b5-36da44058a48)  
3. DO NOT modify, truncate, shorten, or change ANY characters in the agent_id
4. DO NOT remove hyphens or any part of the UUID
5. Copy the agent_id EXACTLY character-for-character from the available agents list
6. Even a single missing or changed character will cause the agent call to fail

VERIFICATION CHECKLIST before calling:
- Is the agent_id exactly 36 characters long?
- Does it match exactly with one from the available agents list?
- Have you copied it without any modifications?

If you're unsure about the agent_id, refer back to the AVAILABLE AGENTS section in the system prompt.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "The exact 36-character UUID of the agent to call. MUST be copied exactly from the AVAILABLE AGENTS list in the system prompt. Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
                            },
                            "handoff_message": {
                                "type": "string", 
                                "description": "Message to pass to the new agent explaining the context and what needs to be done."
                            }
                        },
                        "required": ["agent_id", "handoff_message"]
                    }
                }
            }
        }

    async def agent_call(self, agent_id: str, handoff_message: str) -> Dict[str, Any]:
        """
        Call another agent to handle a specific task.
        
        Args:
            agent_id: The exact ID of the agent to call
            handoff_message: Message to pass to the new agent
            
        Returns:
            Dictionary with call result
        """
        try:
            logger.info(f"🚨 AGENT CALL TOOL EXECUTED! agent_id='{agent_id}', handoff_message={handoff_message}")
            
            # DEBUG: Log detailed information about the received agent_id
            logger.info(f"🔍 DEBUG: RECEIVED AGENT_ID DETAILS:")
            logger.info(f"🔍 Agent ID: '{agent_id}'")
            logger.info(f"🔍 Length: {len(agent_id)}")
            logger.info(f"🔍 Type: {type(agent_id)}")
            logger.info(f"🔍 Repr: {repr(agent_id)}")
            
            # Check if it's a valid UUID format
            try:
                uuid_obj = uuid.UUID(agent_id)
                logger.info(f"🔍 Valid UUID: {uuid_obj}")
                logger.info(f"🔍 UUID String: {str(uuid_obj)}")
                logger.info(f"🔍 UUID String Length: {len(str(uuid_obj))}")
            except ValueError as ve:
                logger.warning(f"🔍 Invalid UUID format: {ve}")
            
            result = {
                "action": "agent_call",
                "target_agent_id": agent_id,
                "message": handoff_message,
                "status": "success"
            }
            
            logger.info(f"🎯 AGENT CALL RESULT: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ AGENT CALL ERROR: {str(e)}", exc_info=True)
            return {
                "action": "agent_call",
                "status": "error",
                "error": str(e)
            } 