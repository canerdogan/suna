'use client';

import React, { useState } from 'react';
import { Brain, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

interface ThinkingToggleProps {
  thinkingEnabled?: boolean;
  onThinkingChange?: (enabled: boolean) => void;
  reasoningEffort?: string;
  onReasoningEffortChange?: (effort: string) => void;
  disabled?: boolean;
}

const reasoningOptions = [
  { value: 'low', label: 'Low', description: 'Quick thinking' },
  { value: 'medium', label: 'Medium', description: 'Balanced reasoning' },
  { value: 'high', label: 'High', description: 'Deep analysis' },
];

export const ThinkingToggle: React.FC<ThinkingToggleProps> = ({
  thinkingEnabled = false,
  onThinkingChange,
  reasoningEffort = 'low',
  onReasoningEffortChange,
  disabled = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(thinkingEnabled);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const isMobile = useIsMobile();

  const handleToggle = () => {
    const newEnabled = !thinkingEnabled;
    onThinkingChange?.(newEnabled);
    setIsExpanded(newEnabled);
  };

  const handleReasoningChange = (effort: string) => {
    onReasoningEffortChange?.(effort);
  };

  const currentReasoning = reasoningOptions.find(opt => opt.value === reasoningEffort);

  return (
    <div className="flex items-center">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleToggle}
              disabled={disabled}
              className={cn(
                'h-8 rounded-xl transition-all duration-300 ease-in-out overflow-hidden',
                thinkingEnabled 
                  ? 'bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-950/50' 
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
                // Mobile: Always show just icon, Desktop: Expand when enabled
                isMobile 
                  ? 'w-8 px-0' 
                  : (isExpanded ? 'px-3' : 'w-8 px-0')
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Brain className="h-4 w-4 flex-shrink-0" />
                {/* Only show expanded content on desktop when expanded */}
                {!isMobile && (
                  <div 
                    className={cn(
                      'flex items-center gap-1 transition-all duration-300 ease-in-out overflow-hidden whitespace-nowrap',
                      isExpanded ? 'max-w-[120px] opacity-100' : 'max-w-0 opacity-0'
                    )}
                  >
                    {thinkingEnabled && (
                      <>
                        <span className="text-xs font-medium">Thinking</span>
                        {reasoningEffort && (
                          <>
                            <span className="text-xs text-muted-foreground">·</span>
                            <DropdownMenu 
                              open={dropdownOpen} 
                              onOpenChange={(open) => {
                                setDropdownOpen(open);
                                // Don't change thinking state when dropdown opens/closes
                              }}
                            >
                              <DropdownMenuTrigger asChild>
                                <span 
                                  className="flex items-center gap-1 text-xs hover:text-foreground cursor-pointer"
                                  onClick={(e) => {
                                    e.stopPropagation(); // Prevent parent button toggle
                                    setDropdownOpen(!dropdownOpen);
                                  }}
                                >
                                  <span>{currentReasoning?.label}</span>
                                  <ChevronDown className="h-3 w-3" />
                                </span>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="w-40">
                                {reasoningOptions.map((option) => (
                                  <DropdownMenuItem
                                    key={option.value}
                                    onClick={(e) => {
                                      e.stopPropagation(); // Prevent parent button toggle
                                      handleReasoningChange(option.value);
                                      setDropdownOpen(false);
                                    }}
                                    className={cn(
                                      'cursor-pointer flex flex-col items-start',
                                      reasoningEffort === option.value && 'bg-accent'
                                    )}
                                  >
                                    <span className="font-medium">{option.label}</span>
                                    <span className="text-xs text-muted-foreground">{option.description}</span>
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-xs">
            <p>
              {thinkingEnabled ? 'Disable thinking mode' : 'Enable thinking mode'}
              {/* Mobile: Show current effort in tooltip */}
              {isMobile && thinkingEnabled && currentReasoning && (
                <span className="block text-muted-foreground">
                  Current: {currentReasoning.label}
                </span>
              )}
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      
      {/* Mobile: Separate reasoning effort dropdown */}
      {isMobile && thinkingEnabled && reasoningEffort && (
        <DropdownMenu 
          open={dropdownOpen} 
          onOpenChange={setDropdownOpen}
        >
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 ml-1 text-muted-foreground hover:text-foreground hover:bg-accent/50"
            >
              <ChevronDown className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            {reasoningOptions.map((option) => (
              <DropdownMenuItem
                key={option.value}
                onClick={() => {
                  handleReasoningChange(option.value);
                  setDropdownOpen(false);
                }}
                className={cn(
                  'cursor-pointer flex flex-col items-start',
                  reasoningEffort === option.value && 'bg-accent'
                )}
              >
                <span className="font-medium">{option.label}</span>
                <span className="text-xs text-muted-foreground">{option.description}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
};