import os
import base64
import json
import requests
from typing import Dict, Any, Optional
from pydantic import BaseModel

from sandbox.tool_base import SandboxToolsBase
from utils.config import config
from utils.logger import logger
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
        logger.info(f"SandboxAssetGeneratorTool initialized for project_id={project_id}, thread_id={thread_id}")

    @property
    def is_available(self) -> bool:
        """Check if the tool is available by verifying API keys"""
        gemini_available = bool(config.GEMINI_API_KEY)
        eachlabs_available = bool(config.EACHLABS_API_KEY and 
                                               (config.EACHLABS_2D_ASSET_WORKFLOW_ID or 
                                  config.EACHLABS_3D_ASSET_WORKFLOW_ID))
        
        available = gemini_available or eachlabs_available
        logger.debug(f"Asset generator availability check: gemini={gemini_available}, eachlabs={eachlabs_available}, overall={available}")
        
        return available

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "generate_asset",
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
        tag_name="generate-asset",
        mappings=[
            {"param_name": "prompt", "node_type": "attribute", "path": "."},
            {"param_name": "aspect_ratio", "node_type": "attribute", "path": "."},
            {"param_name": "number_of_images", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="generate_asset">
        <parameter name="prompt">A beautiful sunset over a mountain landscape, golden hour lighting, photorealistic style</parameter>
        <parameter name="aspect_ratio">16:9</parameter>
        <parameter name="number_of_images">1</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def generate_asset(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1
    ) -> ToolResult:
        """Generate high-quality images using Google Imagen 4"""
        logger.info(f"Starting AI image generation - prompt: '{prompt[:100]}...', aspect_ratio: {aspect_ratio}, count: {number_of_images}")
        
        try:
            if not config.GEMINI_API_KEY:
                logger.error("Google AI API key not configured")
                return self.fail_response("Error: Google AI API key not configured. Please set GEMINI_API_KEY in environment variables.")

            logger.debug("Importing Google GenAI library")
            from google import genai
            
            logger.debug("Creating Google GenAI client")
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            
            # Generate images using Google Imagen 4
            logger.info(f"Calling Google Imagen 4 API with model='imagen-4.0-generate-preview-06-06'")
            logger.debug(f"Request config: number_of_images={number_of_images}, aspect_ratio={aspect_ratio}")
            
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
            
            logger.debug(f"Google API response received: has_result={bool(result)}, has_result_attr={hasattr(result, '_result') if result else False}")
            
            if not result or not hasattr(result, '_result') or not result._result.images:
                logger.warning("No images were generated by Google API")
                return self.fail_response("Error: No images were generated. Please try a different prompt.")
            
            images_count = len(result._result.images)
            logger.info(f"Successfully received {images_count} images from Google API")
            
            file_urls = []
            for i, image in enumerate(result._result.images):
                logger.debug(f"Processing image {i+1}/{images_count}")
                
                try:
                    # Get image data as bytes
                    image_data = image._pil_image.copy()
                    
                    # Convert to bytes
                    import io
                    img_byte_arr = io.BytesIO()
                    image_data.save(img_byte_arr, format='JPEG', quality=95)
                    img_bytes = img_byte_arr.getvalue()
                    
                    logger.debug(f"Image {i+1} converted to bytes, size: {len(img_bytes)} bytes")
                    
                    # Upload to sandbox file system
                    filename = f"generated_image_{i+1}.jpg"
                    logger.debug(f"Uploading image {i+1} to sandbox as '{filename}'")
                    
                    file_url = await self.sandbox.fs.upload_file(
                        filename=filename,
                        content=img_bytes,
                        content_type="image/jpeg"
                    )
                    file_urls.append(file_url)
                    logger.info(f"Image {i+1} uploaded successfully: {file_url}")
                    
                except Exception as img_error:
                    logger.error(f"Error processing image {i+1}: {str(img_error)}")
                    # Continue with other images instead of failing completely
                    continue
            
            # Check if we have any successful uploads
            if not file_urls:
                logger.error("All image processing failed, no images uploaded")
                return self.fail_response("Error: Failed to process any generated images. Please try again.")
            
            if len(file_urls) == 1:
                success_message = f"✅ **Image Generated Successfully!**\n\n📸 **Generated Image:** [View Image]({file_urls[0]})\n\n💬 **Prompt:** {prompt}\n\n🎨 **Details:**\n- Model: Google Imagen 4\n- Aspect Ratio: {aspect_ratio}\n- Generation: Completed immediately"
            else:
                file_list = "\n".join([f"📸 [Image {i+1}]({url})" for i, url in enumerate(file_urls)])
                success_message = f"✅ **{len(file_urls)} Images Generated Successfully!**\n\n{file_list}\n\n💬 **Prompt:** {prompt}\n\n🎨 **Details:**\n- Model: Google Imagen 4\n- Aspect Ratio: {aspect_ratio}\n- Generation: Completed immediately"
            
            logger.info(f"AI image generation completed successfully: {len(file_urls)} images")
            return self.success_response(success_message)
                
        except ImportError as import_error:
            logger.error(f"Google AI library import failed: {str(import_error)}")
            return self.fail_response("Error: Google AI library not installed. Please install google-genai package.")
        except Exception as e:
            logger.error(f"Unexpected error during AI image generation: {str(e)}", exc_info=True)
            return self.fail_response(f"Error generating image: {str(e)}")

    # @openapi_schema({
    #     "type": "function",
    #     "function": {
    #         "name": "generate_2d_asset",
    #         "description": "Generate 2D game assets like sprites, icons, UI elements, and textures using specialized workflows.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "prompt": {
    #                     "type": "string",
    #                     "description": "Detailed description of the 2D asset to generate. Specify the type (icon, sprite, texture, etc.) and visual style.",
    #                 },
    #                 "game_style": {
    #                     "type": "string",
    #                     "description": "Game art style for the 2D asset",
    #                     "default": "fantasy RPG"
    #                 }
    #             },
    #             "required": ["prompt"],
    #         },
    #     },
    # })
    # @xml_schema(
    #     tag_name="generate-2d-asset",
    #     mappings=[
    #         {"param_name": "prompt", "node_type": "attribute", "path": "."},
    #         {"param_name": "game_style", "node_type": "attribute", "path": "."}
    #     ],
    #     example='''
    #     <function_calls>
    #     <invoke name="generate_2d_asset">
    #     <parameter name="prompt">Archer character icon with bow and arrow, pixel art style</parameter>
    #     <parameter name="game_style">fantasy RPG</parameter>
    #     </invoke>
    #     </function_calls>
    #     '''
    # )
    # async def generate_2d_asset(
    #     self,
    #     prompt: str,
    #     game_style: str = "fantasy RPG"
    # ) -> ToolResult:
    #     """Generate 2D game assets using Eachlabs workflow"""
    #     logger.info(f"Starting 2D asset generation - prompt: '{prompt[:100]}...', style: {game_style}")
        
    #     try:
    #         if not config.EACHLABS_API_KEY:
    #             logger.error("Eachlabs API key not configured")
    #             return self.fail_response("Error: Eachlabs API key not configured. Please set EACHLABS_API_KEY in environment variables.")
            
    #         if not config.EACHLABS_2D_ASSET_WORKFLOW_ID:
    #             logger.error("Eachlabs 2D asset workflow ID not configured")
    #             return self.fail_response("Error: 2D asset workflow ID not configured. Please set EACHLABS_2D_ASSET_WORKFLOW_ID in environment variables.")

    #         parameters = {
    #             "prompt": prompt,
    #             "game_style": game_style
    #         }
            
    #         logger.debug(f"Calling Eachlabs 2D workflow with ID: {config.EACHLABS_2D_ASSET_WORKFLOW_ID}")
    #         logger.debug(f"Workflow parameters: {parameters}")
            
    #         result = await self._run_workflow(
    #             workflow_id=config.EACHLABS_2D_ASSET_WORKFLOW_ID,
    #             parameters=parameters
    #         )
            
    #         success_message = f"✅ **2D Asset Generation Started!**\n\n🎮 **Asset Type:** 2D Game Asset\n💬 **Prompt:** {prompt}\n🎨 **Style:** {game_style}\n\n📊 **Status:** Workflow executed successfully\n🔄 **Processing:** Your asset is being generated by Eachlabs workflow\n⏱️ **Expected:** Results will be available through webhook (feature coming soon)\n\n📋 **Workflow Details:**\n{result}"
    #         logger.info("2D asset generation workflow started successfully")
    #         return self.success_response(success_message)
            
    #     except Exception as e:
    #         logger.error(f"Error during 2D asset generation: {str(e)}", exc_info=True)
    #         return self.fail_response(f"Error generating 2D asset: {str(e)}")

    # @openapi_schema({
    #     "type": "function",
    #     "function": {
    #         "name": "generate_3d_asset",
    #         "description": "Generate 3D game assets like models, props, characters, and environments using specialized workflows.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "prompt": {
    #                     "type": "string",
    #                     "description": "Detailed description of the 3D asset to generate. Specify the type (character, prop, environment, etc.) and visual style.",
    #                 },
    #                 "game_style": {
    #                     "type": "string",
    #                     "description": "Game art style for the 3D asset",
    #                     "default": "fantasy RPG"
    #                 }
    #             },
    #             "required": ["prompt"],
    #         },
    #     },
    # })
    # @xml_schema(
    #     tag_name="generate-3d-asset",
    #     mappings=[
    #         {"param_name": "prompt", "node_type": "attribute", "path": "."},
    #         {"param_name": "game_style", "node_type": "attribute", "path": "."}
    #     ],
    #     example='''
    #     <function_calls>
    #     <invoke name="generate_3d_asset">
    #     <parameter name="prompt">Medieval castle tower with stone texture and weathered details</parameter>
    #     <parameter name="game_style">fantasy RPG</parameter>
    #     </invoke>
    #     </function_calls>
    #     '''
    # )
    # async def generate_3d_asset(
    #     self,
    #     prompt: str,
    #     game_style: str = "fantasy RPG"
    # ) -> ToolResult:
    #     """Generate 3D game assets using Eachlabs workflow"""
    #     logger.info(f"Starting 3D asset generation - prompt: '{prompt[:100]}...', style: {game_style}")
        
    #     try:
    #         if not config.EACHLABS_API_KEY:
    #             logger.error("Eachlabs API key not configured")
    #             return self.fail_response("Error: Eachlabs API key not configured. Please set EACHLABS_API_KEY in environment variables.")
            
    #         if not config.EACHLABS_3D_ASSET_WORKFLOW_ID:
    #             logger.error("Eachlabs 3D asset workflow ID not configured")
    #             return self.fail_response("Error: 3D asset workflow ID not configured. Please set EACHLABS_3D_ASSET_WORKFLOW_ID in environment variables.")

    #         parameters = {
    #             "prompt": prompt,
    #             "game_style": game_style
    #         }
            
    #         logger.debug(f"Calling Eachlabs 3D workflow with ID: {config.EACHLABS_3D_ASSET_WORKFLOW_ID}")
    #         logger.debug(f"Workflow parameters: {parameters}")
            
    #         result = await self._run_workflow(
    #             workflow_id=config.EACHLABS_3D_ASSET_WORKFLOW_ID,
    #             parameters=parameters
    #         )
            
    #         success_message = f"✅ **3D Asset Generation Started!**\n\n🎮 **Asset Type:** 3D Game Asset\n💬 **Prompt:** {prompt}\n🎨 **Style:** {game_style}\n\n📊 **Status:** Workflow executed successfully\n🔄 **Processing:** Your asset is being generated by Eachlabs workflow\n⏱️ **Expected:** Results will be available through webhook (feature coming soon)\n\n📋 **Workflow Details:**\n{result}"
    #         logger.info("3D asset generation workflow started successfully")
    #         return self.success_response(success_message)
            
    #     except Exception as e:
    #         logger.error(f"Error during 3D asset generation: {str(e)}", exc_info=True)
    #         return self.fail_response(f"Error generating 3D asset: {str(e)}")

    # async def _run_workflow(
    #     self,
    #     workflow_id: str,
    #     parameters: Dict[str, Any],
    #     webhook_url: Optional[str] = None
    # ) -> str:
    #     """Private helper method to execute Eachlabs workflows"""
    #     logger.info(f"Starting Eachlabs workflow execution for workflow_id: {workflow_id}")
        
    #     try:
    #         url = f"https://flows.eachlabs.ai/api/v1/{workflow_id}/trigger"
    #         logger.debug(f"Eachlabs API URL: {url}")
            
    #         headers = {
    #             "X-API-KEY": config.EACHLABS_API_KEY,
    #             "Content-Type": "application/json"
    #         }
            
    #         payload = {
    #             "parameters": parameters
    #         }
            
    #         if webhook_url:
    #             payload["webhook_url"] = webhook_url
    #             logger.debug(f"Using webhook URL: {webhook_url}")
    #         else:
    #             payload["webhook_url"] = ""
    #             logger.debug("No webhook URL provided")
            
    #         # Log request details (without sensitive data)
    #         safe_headers = {k: v for k, v in headers.items() if k != "X-API-KEY"}
    #         safe_headers["X-API-KEY"] = "***" if headers.get("X-API-KEY") else None
    #         logger.debug(f"Request headers: {safe_headers}")
    #         logger.debug(f"Request payload: {payload}")
            
    #         logger.info(f"Sending POST request to Eachlabs API...")
    #         response = requests.post(url, headers=headers, json=payload, timeout=30)
            
    #         logger.info(f"Eachlabs API response received - status: {response.status_code}")
    #         logger.debug(f"Response headers: {dict(response.headers)}")
    #         logger.debug(f"Response content: {response.text[:500]}..." if len(response.text) > 500 else f"Response content: {response.text}")
            
    #         if response.status_code == 200:
    #             logger.info("Eachlabs workflow executed successfully")
    #             try:
    #                 result = response.json()
    #                 logger.debug(f"Parsed JSON response: {result}")
    #                 return f"Workflow executed successfully. Response: {result}"
    #             except json.JSONDecodeError as json_error:
    #                 logger.warning(f"Failed to parse JSON response: {str(json_error)}")
    #                 logger.debug(f"Raw response text: {response.text}")
    #                 return f"Workflow executed successfully. Response: {response.text}"
    #         else:
    #             logger.error(f"Eachlabs workflow failed with status {response.status_code}")
    #             logger.error(f"Error response: {response.text}")
    #             return f"Workflow execution failed with status {response.status_code}: {response.text}"
                
    #     except requests.exceptions.Timeout as timeout_error:
    #         logger.error(f"Eachlabs API request timeout: {str(timeout_error)}")
    #         return "Error: Request timeout. The workflow service might be busy."
    #     except requests.exceptions.ConnectionError as conn_error:
    #         logger.error(f"Eachlabs API connection error: {str(conn_error)}")
    #         return f"Error: Failed to connect to Eachlabs service: {str(conn_error)}"
    #     except requests.exceptions.RequestException as req_error:
    #         logger.error(f"Eachlabs API request error: {str(req_error)}")
    #         return f"Error: Network error occurred: {str(req_error)}"
    #     except Exception as e:
    #         logger.error(f"Unexpected error during Eachlabs workflow execution: {str(e)}", exc_info=True)
    #         return f"Error: Unexpected error occurred: {str(e)}" 