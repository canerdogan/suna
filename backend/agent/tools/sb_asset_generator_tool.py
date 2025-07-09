import os
import base64
import requests
from typing import Dict, Any, Optional
from pydantic import BaseModel

from sandbox.tool_base import SandboxToolsBase
from utils.config import config
from agentpress.tool import ToolResult, openapi_schema, xml_schema


class SandboxAssetGeneratorTool(SandboxToolsBase):
    """
    Asset generator tool that supports multiple asset generation methods:
    - AI Image generation using Google Imagen 4
    - 2D Asset generation using Eachlabs workflows  
    - 3D Asset generation using Eachlabs workflows
    """

    def __init__(self, project_id: str, thread_id: str, thread_manager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @property
    def is_available(self) -> bool:
        """Check if the tool is available by verifying API keys"""
        return bool(config.GEMINI_API_KEY or (config.EACHLABS_API_KEY and 
                                               (config.EACHLABS_2D_ASSET_WORKFLOW_ID or 
                                                config.EACHLABS_3D_ASSET_WORKFLOW_ID)))

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "generate_ai_image",
            "description": "Generate high-quality images using AI. Perfect for creating realistic photos, artistic illustrations, logos, and visual content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate. Be specific about style, colors, composition, and details.",
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["1:1", "9:16", "16:9", "4:3", "3:4"],
                        "description": "Aspect ratio for the generated image",
                        "default": "1:1"
                    },
                    "number_of_images": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 4,
                        "description": "Number of images to generate (1-4)",
                        "default": 1
                    }
                },
                "required": ["prompt"],
            },
        },
    })
    @xml_schema(
        tag_name="generate-ai-image",
        mappings=[
            {"param_name": "prompt", "node_type": "attribute", "path": "."},
            {"param_name": "aspect_ratio", "node_type": "attribute", "path": "."},
            {"param_name": "number_of_images", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="generate_ai_image">
        <parameter name="prompt">A beautiful sunset over a mountain landscape, golden hour lighting, photorealistic style</parameter>
        <parameter name="aspect_ratio">16:9</parameter>
        <parameter name="number_of_images">1</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def generate_ai_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1
    ) -> ToolResult:
        """Generate high-quality images using Google Imagen 4"""
        try:
            if not config.GEMINI_API_KEY:
                return ToolResult(
                    output="Error: Google AI API key not configured. Please set GEMINI_API_KEY in environment variables.",
                    error="Google AI API key not configured"
                )

            from google import genai
            
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            
            # Generate images using Google Imagen 4
            result = client.models.generate_images(
                model="models/imagen-4.0-generate-preview-06-06",
                prompt=prompt,
                config=dict(
                    number_of_images=number_of_images,
                    output_mime_type="image/jpeg",
                    aspect_ratio=aspect_ratio,
                    safety_filter_level="block_only_high",
                    person_generation="allow_adult"
                )
            )
            
            if not result or not hasattr(result, '_result') or not result._result.images:
                return ToolResult(
                    output="Error: No images were generated. Please try a different prompt.",
                    error="No images generated"
                )
            
            file_urls = []
            for i, image in enumerate(result._result.images):
                # Get image data as bytes
                image_data = image._pil_image.copy()
                
                # Convert to bytes
                import io
                img_byte_arr = io.BytesIO()
                image_data.save(img_byte_arr, format='JPEG', quality=95)
                img_bytes = img_byte_arr.getvalue()
                
                # Upload to sandbox file system
                filename = f"generated_image_{i+1}.jpg"
                file_url = await self.sandbox.fs.upload_file(
                    filename=filename,
                    content=img_bytes,
                    content_type="image/jpeg"
                )
                file_urls.append(file_url)
            
            if len(file_urls) == 1:
                success_message = f"✅ Image generated successfully!\n\nGenerated image: {file_urls[0]}\n\nPrompt used: {prompt}"
            else:
                file_list = "\n".join([f"- {url}" for url in file_urls])
                success_message = f"✅ {len(file_urls)} images generated successfully!\n\nGenerated images:\n{file_list}\n\nPrompt used: {prompt}"
            
            return ToolResult(output=success_message)
                
        except ImportError:
            return ToolResult(
                output="Error: Google AI library not installed. Please install google-genai package.",
                error="Google AI library not installed"
            )
        except Exception as e:
            return ToolResult(
                output=f"Error generating image: {str(e)}",
                error=f"Image generation failed: {str(e)}"
            )

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "generate_2d_asset",
            "description": "Generate 2D game assets like sprites, icons, UI elements, and textures using specialized workflows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the 2D asset to generate. Specify the type (icon, sprite, texture, etc.) and visual style.",
                    },
                    "game_style": {
                        "type": "string",
                        "description": "Game art style for the 2D asset",
                        "default": "fantasy RPG"
                    }
                },
                "required": ["prompt"],
            },
        },
    })
    @xml_schema(
        tag_name="generate-2d-asset",
        mappings=[
            {"param_name": "prompt", "node_type": "attribute", "path": "."},
            {"param_name": "game_style", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="generate_2d_asset">
        <parameter name="prompt">Archer character icon with bow and arrow, pixel art style</parameter>
        <parameter name="game_style">fantasy RPG</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def generate_2d_asset(
        self,
        prompt: str,
        game_style: str = "fantasy RPG"
    ) -> ToolResult:
        """Generate 2D game assets using Eachlabs workflow"""
        try:
            if not config.EACHLABS_API_KEY:
                return ToolResult(
                    output="Error: Eachlabs API key not configured. Please set EACHLABS_API_KEY in environment variables.",
                    error="Eachlabs API key not configured"
                )
            
            if not config.EACHLABS_2D_ASSET_WORKFLOW_ID:
                return ToolResult(
                    output="Error: 2D asset workflow ID not configured. Please set EACHLABS_2D_ASSET_WORKFLOW_ID in environment variables.",
                    error="2D asset workflow ID not configured"
                )

            parameters = {
                "prompt": prompt,
                "game_style": game_style
            }
            
            result = await self._run_workflow(
                workflow_id=config.EACHLABS_2D_ASSET_WORKFLOW_ID,
                parameters=parameters
            )
            
            success_message = f"✅ 2D asset generation started successfully!\n\n{result}\n\nPrompt: {prompt}\nStyle: {game_style}"
            return ToolResult(output=success_message)
            
        except Exception as e:
            return ToolResult(
                output=f"Error generating 2D asset: {str(e)}",
                error=f"2D asset generation failed: {str(e)}"
            )

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "generate_3d_asset",
            "description": "Generate 3D game assets like models, props, characters, and environments using specialized workflows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the 3D asset to generate. Specify the type (character, prop, environment, etc.) and visual style.",
                    },
                    "game_style": {
                        "type": "string",
                        "description": "Game art style for the 3D asset",
                        "default": "fantasy RPG"
                    }
                },
                "required": ["prompt"],
            },
        },
    })
    @xml_schema(
        tag_name="generate-3d-asset",
        mappings=[
            {"param_name": "prompt", "node_type": "attribute", "path": "."},
            {"param_name": "game_style", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="generate_3d_asset">
        <parameter name="prompt">Medieval castle tower with stone texture and weathered details</parameter>
        <parameter name="game_style">fantasy RPG</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def generate_3d_asset(
        self,
        prompt: str,
        game_style: str = "fantasy RPG"
    ) -> ToolResult:
        """Generate 3D game assets using Eachlabs workflow"""
        try:
            if not config.EACHLABS_API_KEY:
                return ToolResult(
                    output="Error: Eachlabs API key not configured. Please set EACHLABS_API_KEY in environment variables.",
                    error="Eachlabs API key not configured"
                )
            
            if not config.EACHLABS_3D_ASSET_WORKFLOW_ID:
                return ToolResult(
                    output="Error: 3D asset workflow ID not configured. Please set EACHLABS_3D_ASSET_WORKFLOW_ID in environment variables.",
                    error="3D asset workflow ID not configured"
                )

            parameters = {
                "prompt": prompt,
                "game_style": game_style
            }
            
            result = await self._run_workflow(
                workflow_id=config.EACHLABS_3D_ASSET_WORKFLOW_ID,
                parameters=parameters
            )
            
            success_message = f"✅ 3D asset generation started successfully!\n\n{result}\n\nPrompt: {prompt}\nStyle: {game_style}"
            return ToolResult(output=success_message)
            
        except Exception as e:
            return ToolResult(
                output=f"Error generating 3D asset: {str(e)}",
                error=f"3D asset generation failed: {str(e)}"
            )

    async def _run_workflow(
        self,
        workflow_id: str,
        parameters: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> str:
        """Private helper method to execute Eachlabs workflows"""
        try:
            url = f"https://flows.eachlabs.ai/api/v1/{workflow_id}/trigger"
            
            headers = {
                "X-API-KEY": config.EACHLABS_API_KEY,
                "Content-Type": "application/json"
            }
            
            payload = {
                "parameters": parameters
            }
            
            if webhook_url:
                payload["webhook_url"] = webhook_url
            else:
                payload["webhook_url"] = ""
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    return f"Workflow executed successfully. Response: {result}"
                except:
                    return f"Workflow executed successfully. Response: {response.text}"
            else:
                return f"Workflow execution failed with status {response.status_code}: {response.text}"
                
        except requests.exceptions.Timeout:
            return "Error: Request timeout. The workflow service might be busy."
        except requests.exceptions.RequestException as e:
            return f"Error: Network error occurred: {str(e)}"
        except Exception as e:
            return f"Error: Unexpected error occurred: {str(e)}" 