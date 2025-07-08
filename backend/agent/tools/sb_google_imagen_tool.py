from typing import Optional
from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from google import genai
import uuid
import base64
from io import BytesIO
from PIL import Image
from utils.config import config
from utils.logger import logger
import os


class SandboxGoogleImagenTool(SandboxToolsBase):
    """Tool for generating images using Google Imagen 4 via Gemini API."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY is required for Google Imagen tool")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "google_imagen_generate",
            "description": "Generate high-quality images using Google Imagen 4. Creates realistic and artistic images from detailed text prompts with advanced AI capabilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed text prompt describing the image to generate. Be specific about style, colors, composition, lighting, and other visual elements."
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"],
                        "description": "Image aspect ratio. Options: '1:1' (square), '16:9' (horizontal), '9:16' (vertical), '4:3' (landscape), '3:4' (portrait), '3:2' (wide), '2:3' (tall). Default: '1:1'",
                        "default": "1:1"
                    },
                    "number_of_images": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Number of images to generate (1-8). Default: 1",
                        "default": 1
                    },
                    "person_generation": {
                        "type": "string",
                        "enum": ["ALLOW_ADULT", "DONT_ALLOW"],
                        "description": "Policy for person generation. 'ALLOW_ADULT' for adult people, 'DONT_ALLOW' to avoid people. Default: 'ALLOW_ADULT'",
                        "default": "ALLOW_ADULT"
                    },
                    "output_mime_type": {
                        "type": "string",
                        "enum": ["image/jpeg", "image/png"],
                        "description": "Output format. 'image/jpeg' for JPEG, 'image/png' for PNG. Default: 'image/jpeg'",
                        "default": "image/jpeg"
                    }
                },
                "required": ["prompt"]
            }
        }
    })
    @xml_schema(
        tag_name="google-imagen-generate",
        mappings=[
            {"param_name": "prompt", "node_type": "attribute", "path": "."},
            {"param_name": "aspect_ratio", "node_type": "attribute", "path": "."},
            {"param_name": "number_of_images", "node_type": "attribute", "path": "."},
            {"param_name": "person_generation", "node_type": "attribute", "path": "."},
            {"param_name": "output_mime_type", "node_type": "attribute", "path": "."},
        ],
        example="""
        <function_calls>
        <invoke name="google_imagen_generate">
        <parameter name="prompt">A beautiful sunset over a mountain landscape, golden hour lighting, photorealistic style</parameter>
        <parameter name="aspect_ratio">16:9</parameter>
        <parameter name="number_of_images">1</parameter>
        <parameter name="person_generation">ALLOW_ADULT</parameter>
        <parameter name="output_mime_type">image/jpeg</parameter>
        </invoke>
        </function_calls>
        """,
    )
    async def google_imagen_generate(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = "1:1",
        number_of_images: Optional[int] = 1,
        person_generation: Optional[str] = "ALLOW_ADULT",
        output_mime_type: Optional[str] = "image/jpeg"
    ) -> ToolResult:
        """
        Generate images using Google Imagen 4.

        Args:
            prompt: Detailed description of the image to generate
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3). Default is 1:1
            number_of_images: Number of images to generate (1-8). Default is 1
            person_generation: Policy for person generation (ALLOW_ADULT, DONT_ALLOW). Default is ALLOW_ADULT
            output_mime_type: Output format (image/jpeg, image/png). Default is image/jpeg

        Returns:
            ToolResult: Generated image information including file paths and metadata
        """
        try:
            # Validate inputs
            if not prompt or len(prompt.strip()) == 0:
                return ToolResult(
                    output="Error: Prompt cannot be empty",
                    error="Invalid prompt provided"
                )

            # Validate aspect ratio
            valid_ratios = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]
            if aspect_ratio not in valid_ratios:
                return ToolResult(
                    output=f"Error: Invalid aspect ratio. Must be one of: {', '.join(valid_ratios)}",
                    error="Invalid aspect ratio"
                )

            # Validate number of images
            if number_of_images < 1 or number_of_images > 8:
                return ToolResult(
                    output="Error: Number of images must be between 1 and 8",
                    error="Invalid number of images"
                )

            # Validate person generation policy
            valid_policies = ["ALLOW_ADULT", "DONT_ALLOW"]
            if person_generation not in valid_policies:
                return ToolResult(
                    output=f"Error: Invalid person generation policy. Must be one of: {', '.join(valid_policies)}",
                    error="Invalid person generation policy"
                )

            # Validate output format
            valid_formats = ["image/jpeg", "image/png"]
            if output_mime_type not in valid_formats:
                return ToolResult(
                    output=f"Error: Invalid output format. Must be one of: {', '.join(valid_formats)}",
                    error="Invalid output format"
                )

            logger.info(f"Generating {number_of_images} image(s) with prompt: {prompt[:100]}...")

            # Initialize Google GenAI client
            client = genai.Client(api_key=self.api_key)

            # Generate images using Google Imagen 4
            result = client.models.generate_images(
                model="models/imagen-4.0-generate-preview-06-06",
                prompt=prompt,
                config=dict(
                    number_of_images=number_of_images,
                    output_mime_type=output_mime_type,
                    person_generation=person_generation,
                    aspect_ratio=aspect_ratio,
                ),
            )

            if not result.generated_images:
                return ToolResult(
                    output="Error: No images were generated by Imagen 4",
                    error="Generation failed"
                )

            if len(result.generated_images) != number_of_images:
                logger.warning(f"Expected {number_of_images} images, but got {len(result.generated_images)}")

            # Process and save generated images
            generated_files = []
            for i, generated_image in enumerate(result.generated_images):
                try:
                    # Convert bytes to PIL Image
                    image = Image.open(BytesIO(generated_image.image.image_bytes))
                    
                    # Generate unique filename
                    file_extension = "jpg" if output_mime_type == "image/jpeg" else "png"
                    filename = f"imagen_generated_{uuid.uuid4().hex[:8]}_{i+1}.{file_extension}"
                    
                    # Save to sandbox
                    await self._ensure_sandbox()
                    sandbox_path = f"{self.workspace_path}/{filename}"
                    await self.sandbox.fs.upload_file(generated_image.image.image_bytes, sandbox_path)
                    
                    generated_files.append({
                        "filename": filename,
                        "size": f"{image.width}x{image.height}",
                        "format": output_mime_type,
                        "aspect_ratio": aspect_ratio
                    })
                    
                    logger.info(f"Generated image {i+1} saved as {filename}")
                    
                except Exception as e:
                    logger.error(f"Error processing generated image {i+1}: {str(e)}")
                    continue

            if not generated_files:
                return ToolResult(
                    output="Error: Failed to process any generated images",
                    error="Image processing failed"
                )

            # Create success response using the same pattern as sb_image_edit_tool
            if len(generated_files) == 1:
                success_message = f"Successfully generated image using Google Imagen 4. Image saved as: {generated_files[0]['filename']}. " \
                                f"Size: {generated_files[0]['size']}, Format: {generated_files[0]['format']}, " \
                                f"Aspect Ratio: {aspect_ratio}. You can use the ask tool to display the image."
            else:
                files_info = ", ".join([f"{file['filename']} ({file['size']})" for file in generated_files])
                success_message = f"Successfully generated {len(generated_files)} images using Google Imagen 4. " \
                                f"Images saved as: {files_info}. " \
                                f"Format: {output_mime_type}, Aspect Ratio: {aspect_ratio}. " \
                                f"You can use the ask tool to display the images."

            return ToolResult(output=success_message)

        except Exception as e:
            error_msg = f"Google Imagen generation failed: {str(e)}"
            logger.error(error_msg)
            return ToolResult(
                output=f"Error: {error_msg}",
                error=error_msg
            )

    def get_available_tools(self):
        """Return list of available tools."""
        return ["google_imagen_generate"] 