import React, { useState, useEffect } from 'react';
import { ToolViewProps } from '../types';
import { formatTimestamp, getToolTitle, extractToolData } from '../utils';
import { cn } from '@/lib/utils';
import { useTheme } from 'next-themes';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from "@/components/ui/scroll-area";
import { LoadingState } from '../shared/LoadingState';
import { 
  Palette, 
  Image, 
  Box, 
  Download, 
  CheckCircle, 
  AlertTriangle, 
  CircleDashed,
  FileImage,
  Wand2,
  Clock,
  Zap,
  Loader2
} from 'lucide-react';

interface AssetData {
  prompt?: string;
  output_file?: string;
  game_style?: string;
  asset_type?: string;
  width?: number;
  height?: number;
  format?: string;
  aspect_ratio?: string;
  number_of_images?: number;
}

interface AssetResult {
  isEachlabsWorkflow: boolean;
  isGoogleImagen: boolean;
  isAsyncProcessing: boolean;
  hasImages: boolean;
  images: string[];
  workflowDetails?: string;
  errorMessage?: string;
}

export function AssetGenerationToolView({
  name = 'generate-3d-asset',
  assistantContent,
  toolContent,
  assistantTimestamp,
  toolTimestamp,
  isSuccess = true,
  isStreaming = false,
}: ToolViewProps) {
  const { resolvedTheme } = useTheme();
  const isDarkTheme = resolvedTheme === 'dark';
  const [progress, setProgress] = useState(0);
  const [expandedPrompt, setExpandedPrompt] = useState(false);

  const toolTitle = getToolTitle(name);
  const is3D = name.includes('3d');
  const is2D = name.includes('2d');
  const isImageGeneration = name.includes('ai_image') || name.includes('generate_asset');
  const isEachlabsWorkflow = is2D || is3D;

  // Parse asset data from assistant content
  const extractAssetData = (content: any): AssetData => {
    if (!content) return {};

    let contentStr = '';
    if (typeof content === 'string') {
      contentStr = content;
    } else if (typeof content === 'object') {
      contentStr = JSON.stringify(content);
    }

    const data: AssetData = {};

    // Extract from XML parameters
    const promptMatch = contentStr.match(/<parameter name="prompt">([\s\S]*?)<\/parameter>/);
    if (promptMatch) data.prompt = promptMatch[1].trim();

    const outputFileMatch = contentStr.match(/<parameter name="output_file">([\s\S]*?)<\/parameter>/);
    if (outputFileMatch) data.output_file = outputFileMatch[1].trim();

    const gameStyleMatch = contentStr.match(/<parameter name="game_style">([\s\S]*?)<\/parameter>/);
    if (gameStyleMatch) data.game_style = gameStyleMatch[1].trim();

    const widthMatch = contentStr.match(/<parameter name="width">([\s\S]*?)<\/parameter>/);
    if (widthMatch) data.width = parseInt(widthMatch[1].trim());

    const heightMatch = contentStr.match(/<parameter name="height">([\s\S]*?)<\/parameter>/);
    if (heightMatch) data.height = parseInt(heightMatch[1].trim());

    const formatMatch = contentStr.match(/<parameter name="format">([\s\S]*?)<\/parameter>/);
    if (formatMatch) data.format = formatMatch[1].trim();

    return data;
  };

  const assetData = extractAssetData(assistantContent);

  // Parse tool result to understand the response type
  const parseToolResult = (content: any): AssetResult => {
    if (!content) {
      return {
        isEachlabsWorkflow: false,
        isGoogleImagen: false,
        isAsyncProcessing: false,
        hasImages: false,
        images: [],
      };
    }

    let contentStr = '';
    if (typeof content === 'string') {
      contentStr = content;
    } else if (typeof content === 'object') {
      contentStr = JSON.stringify(content);
    }

    // Check for error messages
    if (contentStr.includes('Error:') || contentStr.includes('error')) {
      return {
        isEachlabsWorkflow: false,
        isGoogleImagen: false,
        isAsyncProcessing: false,
        hasImages: false,
        images: [],
        errorMessage: contentStr,
      };
    }

    // Detect Google Imagen results (immediate images)
    const imageMatches = contentStr.match(/\[View Image\]\((https?:\/\/[^\)]+)\)/g);
    if (imageMatches || contentStr.includes('Image Generated Successfully') || contentStr.includes('Images Generated Successfully')) {
      const images = imageMatches ? imageMatches.map(match => {
        const urlMatch = match.match(/\((https?:\/\/[^\)]+)\)/);
        return urlMatch ? urlMatch[1] : '';
      }).filter(Boolean) : [];
      
      return {
        isEachlabsWorkflow: false,
        isGoogleImagen: true,
        isAsyncProcessing: false,
        hasImages: images.length > 0,
        images,
      };
    }

    // Detect Eachlabs workflow results (async processing)
    if (contentStr.includes('Asset Generation Started') || contentStr.includes('Workflow executed successfully')) {
      return {
        isEachlabsWorkflow: true,
        isGoogleImagen: false,
        isAsyncProcessing: true,
        hasImages: false,
        images: [],
        workflowDetails: contentStr,
      };
    }

    // Default fallback
    return {
      isEachlabsWorkflow: false,
      isGoogleImagen: false,
      isAsyncProcessing: false,
      hasImages: false,
      images: [],
    };
  };

  const toolResult = parseToolResult(toolContent);

  // Simulate progress when streaming - different behavior for different tools
  useEffect(() => {
    if (isStreaming) {
      const timer = setInterval(() => {
        setProgress((prevProgress) => {
          if (isImageGeneration) {
            // Google Imagen - faster progress, completes quickly
            if (prevProgress >= 95) {
              clearInterval(timer);
              return prevProgress;
            }
            return prevProgress + 8; // Faster for immediate image generation
          } else if (isEachlabsWorkflow) {
            // Eachlabs workflows - slower, stops at workflow trigger
            if (prevProgress >= 30) {
              clearInterval(timer);
              return 30; // Stops at workflow trigger, not completion
            }
            return prevProgress + 2; // Slower progress for workflow trigger
          }
          return prevProgress + 3; // Default
        });
      }, isImageGeneration ? 400 : 1000); // Faster interval for image generation
      return () => clearInterval(timer);
    } else {
      if (toolResult.isAsyncProcessing) {
        setProgress(30); // Workflow triggered but not complete
      } else {
        setProgress(100); // Immediate completion
      }
    }
  }, [isStreaming, isImageGeneration, isEachlabsWorkflow, toolResult.isAsyncProcessing]);

  // Get appropriate icon
  const getAssetIcon = () => {
    if (is3D) return Box;
    if (is2D) return Image;
    return Palette;
  };

  const AssetIcon = getAssetIcon();

  const renderParameters = () => {
    if (!assetData.prompt && !assetData.output_file) return null;

    return (
      <div className="space-y-3">
        {assetData.prompt && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Prompt</span>
              {assetData.prompt.length > 200 && (
                <button
                  onClick={() => setExpandedPrompt(!expandedPrompt)}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {expandedPrompt ? 'Show less' : 'Show more'}
                </button>
              )}
            </div>
            <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg border">
              <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
                {expandedPrompt ? assetData.prompt : assetData.prompt.slice(0, 200) + (assetData.prompt.length > 200 ? '...' : '')}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {assetData.output_file && (
            <div className="space-y-1">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Output File</span>
              <div className="flex items-center gap-2 p-2 bg-zinc-50 dark:bg-zinc-800 rounded border">
                <FileImage className="h-4 w-4 text-zinc-500" />
                <span className="text-sm font-mono text-zinc-700 dark:text-zinc-300 truncate">
                  {assetData.output_file}
                </span>
              </div>
            </div>
          )}

          {assetData.game_style && (
            <div className="space-y-1">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Style</span>
              <div className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded border">
                <span className="text-sm text-zinc-700 dark:text-zinc-300 capitalize">
                  {assetData.game_style}
                </span>
              </div>
            </div>
          )}

          {(assetData.width || assetData.height) && (
            <div className="space-y-1">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Dimensions</span>
              <div className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded border">
                <span className="text-sm text-zinc-700 dark:text-zinc-300">
                  {assetData.width || '?'} × {assetData.height || '?'}
                </span>
              </div>
            </div>
          )}

          {assetData.format && (
            <div className="space-y-1">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Format</span>
              <div className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded border">
                <span className="text-sm text-zinc-700 dark:text-zinc-300 uppercase">
                  {assetData.format}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderResult = () => {
    if (!toolContent || isStreaming) return null;

    // Handle error cases
    if (toolResult.errorMessage) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <span className="text-sm font-medium text-red-700 dark:text-red-400">Generation Failed</span>
          </div>
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">
              {toolResult.errorMessage}
            </p>
          </div>
        </div>
      );
    }

    // Handle Google Imagen immediate results (with images)
    if (toolResult.isGoogleImagen && toolResult.hasImages) {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span className="text-sm font-medium text-green-700 dark:text-green-400">
              {toolResult.images.length === 1 ? 'Image Generated' : `${toolResult.images.length} Images Generated`}
            </span>
            <Badge variant="outline" className="ml-2 text-xs">
              <Zap className="h-3 w-3 mr-1" />
              Instant
            </Badge>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {toolResult.images.map((imageUrl, index) => (
              <div key={index} className="group relative">
                <div className="aspect-square bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden border">
                  <img 
                    src={imageUrl} 
                    alt={`Generated image ${index + 1}`}
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik03NSA3NUwxMjUgMTI1TTEyNSA3NUw3NSAxMjUiIHN0cm9rZT0iIzZCNzI4MCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+';
                    }}
                  />
                </div>
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <a 
                    href={imageUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-2 bg-white/90 dark:bg-zinc-900/90 rounded-full shadow-lg hover:bg-white dark:hover:bg-zinc-900 transition-colors"
                  >
                    <Download className="h-4 w-4 text-zinc-700 dark:text-zinc-300" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // Handle Eachlabs workflow results (async processing)
    if (toolResult.isEachlabsWorkflow && toolResult.isAsyncProcessing) {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-500" />
            <span className="text-sm font-medium text-blue-700 dark:text-blue-400">Workflow Started</span>
            <Badge variant="outline" className="ml-2 text-xs">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              Processing
            </Badge>
          </div>
          
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-blue-700 dark:text-blue-300">
                  Asset generation in progress...
                </span>
              </div>
              
              <div className="text-xs text-blue-600 dark:text-blue-400 space-y-1">
                <p>✅ Workflow triggered successfully</p>
                <p>🔄 Processing your request with Eachlabs</p>
                <p>⏳ Results will be available through webhook notification</p>
                <p className="italic">Note: Webhook handling will be added in a future update</p>
              </div>
            </div>
          </div>

          {toolResult.workflowDetails && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100">
                View workflow details
              </summary>
              <div className="mt-2 p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg border">
                <pre className="text-xs text-zinc-600 dark:text-zinc-300 whitespace-pre-wrap">
                  {toolResult.workflowDetails}
                </pre>
              </div>
            </details>
          )}
        </div>
      );
    }

    // Fallback for other content
    return (
      <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg border">
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          {typeof toolContent === 'string' ? toolContent : JSON.stringify(toolContent, null, 2)}
        </p>
      </div>
    );
  };

  if (isStreaming) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center p-2 bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900 dark:to-pink-900 rounded-lg">
              <AssetIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                {toolTitle}
              </h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {isImageGeneration 
                  ? 'Generating AI images...'
                  : is3D 
                    ? 'Starting 3D asset workflow...' 
                    : is2D 
                      ? 'Starting 2D asset workflow...' 
                      : 'Generating asset...'
                }
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Generation Progress</span>
                <span className="text-sm text-zinc-500 dark:text-zinc-400">{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="w-full" />
              <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
                <CircleDashed className="h-4 w-4 animate-spin" />
                {isImageGeneration 
                  ? 'Generating images with Google Imagen 4...'
                  : isEachlabsWorkflow
                    ? 'Triggering Eachlabs workflow...'
                    : 'Processing AI generation request...'
                }
              </div>
            </div>

            {renderParameters()}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center p-2 bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900 dark:to-pink-900 rounded-lg">
            <AssetIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {toolTitle}
            </h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {isImageGeneration 
                ? 'AI Image Generation'
                : is3D 
                  ? '3D Asset Generation' 
                  : is2D 
                    ? '2D Asset Generation' 
                    : 'Asset Generation'
              }
            </p>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {renderParameters()}
          {renderResult()}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex items-center gap-2">
            {isSuccess ? (
              <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
            )}
            <span>
              {!isSuccess 
                ? "Generation failed" 
                : toolResult.isAsyncProcessing
                  ? "Workflow started - processing in background"
                  : toolResult.hasImages
                    ? "Images generated successfully"
                    : "Generation completed"
              }
            </span>
          </div>
          <div className="text-xs">
            {toolTimestamp ? formatTimestamp(toolTimestamp) : assistantTimestamp ? formatTimestamp(assistantTimestamp) : ""}
          </div>
        </div>
      </div>
    </div>
  );
} 