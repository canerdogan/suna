import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { getAgentAvatar } from '../../lib/utils/get-agent-style';
import {
  ChatInput,
  ChatInputHandles
} from '@/components/thread/chat-input/chat-input';
import { ThreadContent } from '@/components/thread/content/ThreadContent';
import { UnifiedMessage } from '@/components/thread/types';
import { useInitiateAgentWithInvalidation } from '@/hooks/react-query/dashboard/use-initiate-agent';
import { useAgentStream } from '@/hooks/useAgentStream';
import { useAddUserMessageMutation } from '@/hooks/react-query/threads/use-messages';
import { useStartAgentMutation, useStopAgentMutation } from '@/hooks/react-query/threads/use-agent-run';
import { BillingError } from '@/lib/api';
import { normalizeFilenameToNFC } from '@/lib/utils/unicode';
import { useQueryClient } from '@tanstack/react-query';

interface Agent {
  agent_id: string;
  name: string;
  description?: string;
  system_prompt: string;
  configured_mcps: Array<{ name: string; qualifiedName: string; config: any; enabledTools?: string[] }>;
  agentpress_tools: Record<string, { enabled: boolean; description: string }>;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

interface AgentPreviewProps {
  agent: Agent;
}

export const AgentPreview = ({ agent }: AgentPreviewProps) => {
  const [messages, setMessages] = useState<UnifiedMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [threadId, setThreadId] = useState<string | null>(null);
  const [agentRunId, setAgentRunId] = useState<string | null>(null);
  const [agentStatus, setAgentStatus] = useState<'idle' | 'running' | 'connecting' | 'error'>('idle');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasStartedConversation, setHasStartedConversation] = useState(false);

  // Model settings state for agent preview
  const [thinkingEnabled, setThinkingEnabled] = useState(false);
  const [reasoningEffort, setReasoningEffort] = useState('low');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<ChatInputHandles>(null);
  const queryClient = useQueryClient();

  const getAgentStyling = () => {
    const agentData = agent as any;
    if (agentData.avatar && agentData.avatar_color) {
      return {
        avatar: agentData.avatar,
        color: agentData.avatar_color,
      };
    }
    return getAgentAvatar(agent.agent_id);
  };

  const { avatar, color } = getAgentStyling();

  const initiateAgentMutation = useInitiateAgentWithInvalidation();
  const addUserMessageMutation = useAddUserMessageMutation();
  const startAgentMutation = useStartAgentMutation();
  const stopAgentMutation = useStopAgentMutation();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleNewMessageFromStream = useCallback((message: UnifiedMessage) => {
    console.log(`[PREVIEW STREAM] Received message: ID=${message.message_id}, Type=${message.type}`);

    setMessages((prev) => {
      const messageExists = prev.some((m) => m.message_id === message.message_id);
      if (messageExists) {
        return prev.map((m) => m.message_id === message.message_id ? message : m);
      } else {
        return [...prev, message];
      }
    });
  }, []);

  const handleStreamStatusChange = useCallback((hookStatus: string) => {
    console.log(`[PREVIEW] Stream status changed: ${hookStatus}`);
    switch (hookStatus) {
      case 'idle':
      case 'completed':
      case 'stopped':
      case 'agent_not_running':
      case 'error':
      case 'failed':
        setAgentStatus('idle');
        setAgentRunId(null);
        break;
      case 'connecting':
        setAgentStatus('connecting');
        break;
      case 'streaming':
        setAgentStatus('running');
        break;
    }
  }, []);

  const handleStreamError = useCallback((errorMessage: string) => {
    console.error(`[PREVIEW] Stream error: ${errorMessage}`);
    if (!errorMessage.toLowerCase().includes('not found') &&
      !errorMessage.toLowerCase().includes('agent run is not running')) {
      toast.error(`Stream Error: ${errorMessage}`);
    }
  }, []);

  const handleStreamClose = useCallback(() => {
    console.log(`[PREVIEW] Stream closed`);
  }, []);

  const handleAgentCall = useCallback(async (agentId: string, message?: string) => {
    console.log('%c🚀 AGENT CALL CALLBACK TRIGGERED! 🚀', 'background: magenta; color: white; font-size: 16px; padding: 5px;');
    console.log('%c🆔 [AGENT_CALL] Target Agent ID:', 'color: blue; font-size: 14px; font-weight: bold;', agentId);
    console.log('%c💬 [AGENT_CALL] Handoff Message:', 'color: green; font-size: 14px; font-weight: bold;', message || 'No message provided');
    
    // Add window alert for testing
    alert(`🚀 AGENT CALL CALLBACK! Target: ${agentId}`);
    
    if (!threadId) {
      console.error('❌ [AGENT_CALL] No thread ID available for agent call');
      return;
    }

    try {
      // Find the agent by ID
      const { data: agentsResponse } = await queryClient.fetchQuery({
        queryKey: ['agents'],
        queryFn: () => fetch('/api/agents').then(res => res.json())
      });
      
      const targetAgent = agentsResponse?.agents?.find((agent: Agent) => 
        agent.agent_id === agentId
      );

      if (!targetAgent) {
        console.error('❌ [AGENT_CALL] Agent not found with ID:', agentId);
        toast.error(`Agent with ID "${agentId}" not found`);
        return;
      }

      console.log('✅ [AGENT_CALL] Target agent found:', targetAgent.name);

      // Add the handoff message to the conversation if provided
      if (message) {
        console.log('📝 [AGENT_CALL] Adding handoff message to conversation');
        const handoffMessage: UnifiedMessage = {
          message_id: `handoff-${Date.now()}`,
          thread_id: threadId,
          type: 'user',
          is_llm_message: false,
          content: message,
          metadata: '{}',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, handoffMessage]);
        
        // Save the handoff message to backend
        console.log('💾 [AGENT_CALL] Saving handoff message to backend');
        await addUserMessageMutation.mutateAsync({
          threadId,
          message
        });
        console.log('✅ [AGENT_CALL] Handoff message saved successfully');
      }

      // Start the new agent
      console.log('🔄 [AGENT_CALL] Starting target agent:', targetAgent.agent_id);
      const agentResult = await startAgentMutation.mutateAsync({
        threadId,
        options: { agent_id: targetAgent.agent_id }
      });
      console.log('✅ [AGENT_CALL] Agent started with run ID:', agentResult.agent_run_id);

      setAgentRunId(agentResult.agent_run_id);
      console.log('🎉 [AGENT_CALL] Successfully switched to agent:', targetAgent.name);
      toast.success(`Switched to ${targetAgent.name}`);
      
    } catch (error: any) {
      console.error('❌ [AGENT_CALL] Error in agent call:', error);
      toast.error(`Failed to switch to agent: ${error.message}`);
    }
  }, [threadId, queryClient, addUserMessageMutation, startAgentMutation, setMessages]);

  const {
    status: streamHookStatus,
    textContent: streamingTextContent,
    toolCall: streamingToolCall,
    error: streamError,
    agentRunId: currentHookRunId,
    startStreaming,
    stopStreaming,
  } = useAgentStream(
    {
      onMessage: handleNewMessageFromStream,
      onStatusChange: handleStreamStatusChange,
      onError: handleStreamError,
      onClose: handleStreamClose,
      onAgentCall: handleAgentCall,
    },
    threadId,
    setMessages,
  );

  useEffect(() => {
    if (agentRunId && agentRunId !== currentHookRunId && threadId) {
      console.log(`[PREVIEW] Starting stream for agentRunId: ${agentRunId}, threadId: ${threadId}`);
      startStreaming(agentRunId);
    }
  }, [agentRunId, startStreaming, currentHookRunId, threadId]);

  useEffect(() => {
    console.log('[PREVIEW] State update:', {
      threadId,
      agentRunId,
      currentHookRunId,
      agentStatus,
      streamHookStatus,
      messagesCount: messages.length,
      hasStartedConversation
    });
  }, [threadId, agentRunId, currentHookRunId, agentStatus, streamHookStatus, messages.length, hasStartedConversation]);

  useEffect(() => {
    if (streamingTextContent) {
      scrollToBottom();
    }
  }, [streamingTextContent]);

  const handleSubmitFirstMessage = async (
    message: string,
    options?: {
      model_name?: string;
      enable_thinking?: boolean;
      reasoning_effort?: string;
      stream?: boolean;
      enable_context_manager?: boolean;
    },
  ) => {
    if (!message.trim() && !chatInputRef.current?.getPendingFiles().length) return;

    setIsSubmitting(true);
    setHasStartedConversation(true);

    try {
      const files = chatInputRef.current?.getPendingFiles() || [];

      const agentFormData = new FormData();
      agentFormData.append('prompt', message);
      agentFormData.append('target_agent_id', agent.agent_id);

      files.forEach((file) => {
        const normalizedName = normalizeFilenameToNFC(file.name);
        agentFormData.append('files', file, normalizedName);
      });

      // Use component state for model settings if not overridden in options
      if (options?.model_name) agentFormData.append('model_name', options.model_name);
      agentFormData.append('enable_thinking', String(options?.enable_thinking ?? thinkingEnabled));
      agentFormData.append('reasoning_effort', options?.reasoning_effort ?? reasoningEffort);
      agentFormData.append('stream', String(options?.stream ?? true));
      agentFormData.append('enable_context_manager', String(options?.enable_context_manager ?? false));

      console.log('[PREVIEW] Initiating agent...');
      const result = await initiateAgentMutation.mutateAsync(agentFormData);
      console.log('[PREVIEW] Agent initiated:', result);

      if (result.thread_id) {
        setThreadId(result.thread_id);
        if (result.agent_run_id) {
          console.log('[PREVIEW] Setting agent run ID:', result.agent_run_id);
          setAgentRunId(result.agent_run_id);
        } else {
          console.log('[PREVIEW] No agent_run_id in result, starting agent manually...');
          try {
            const agentResult = await startAgentMutation.mutateAsync({
              threadId: result.thread_id,
              options
            });
            console.log('[PREVIEW] Agent started manually:', agentResult);
            setAgentRunId(agentResult.agent_run_id);
          } catch (startError) {
            console.error('[PREVIEW] Error starting agent manually:', startError);
            toast.error('Failed to start agent');
          }
        }
        const userMessage: UnifiedMessage = {
          message_id: `user-${Date.now()}`,
          thread_id: result.thread_id,
          type: 'user',
          is_llm_message: false,
          content: message,
          metadata: '{}',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setMessages([userMessage]);
      }

      chatInputRef.current?.clearPendingFiles();
      setInputValue('');
    } catch (error: any) {
      console.error('[PREVIEW] Error during initiation:', error);
      if (error instanceof BillingError) {
        toast.error('Billing limit reached. Please upgrade your plan.');
      } else {
        toast.error('Failed to start conversation');
      }
      setHasStartedConversation(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitMessage = useCallback(
    async (
      message: string,
      options?: { model_name?: string; enable_thinking?: boolean; reasoning_effort?: string; enable_context_manager?: boolean },
    ) => {
      if (!message.trim() || !threadId) return;
      setIsSubmitting(true);

      const optimisticUserMessage: UnifiedMessage = {
        message_id: `temp-user-${Date.now()}-${Math.random()}`,
        thread_id: threadId,
        type: 'user',
        is_llm_message: false,
        content: message,
        metadata: '{}',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, optimisticUserMessage]);
      setInputValue('');

      try {
        const messagePromise = addUserMessageMutation.mutateAsync({
          threadId,
          message
        });

        // Preserve component model settings if not overridden in options
        const finalOptions = {
          agent_id: agent.agent_id,
          ...options,
          enable_thinking: options?.enable_thinking !== undefined ? options.enable_thinking : thinkingEnabled,
          reasoning_effort: options?.reasoning_effort || reasoningEffort,
        };

        const agentPromise = startAgentMutation.mutateAsync({
          threadId,
          options: finalOptions
        });

        const results = await Promise.allSettled([messagePromise, agentPromise]);

        if (results[0].status === 'rejected') {
          throw new Error(`Failed to send message: ${results[0].reason?.message || results[0].reason}`);
        }
        if (results[1].status === 'rejected') {
          const error = results[1].reason;
          if (error instanceof BillingError) {
            toast.error('Billing limit reached. Please upgrade your plan.');
            setMessages(prev => prev.filter(m => m.message_id !== optimisticUserMessage.message_id));
            return;
          }
          throw new Error(`Failed to start agent: ${error?.message || error}`);
        }
        const agentResult = results[1].value;
        setAgentRunId(agentResult.agent_run_id);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Operation failed');
        setMessages((prev) => prev.filter(m => m.message_id !== optimisticUserMessage.message_id));
      } finally {
        setIsSubmitting(false);
      }
    },
    [threadId, addUserMessageMutation, startAgentMutation, agent.agent_id, thinkingEnabled, reasoningEffort],
  );

  const handleStopAgent = useCallback(async () => {
    console.log('[PREVIEW] Stopping agent...');
    setAgentStatus('idle');
    await stopStreaming();

    if (agentRunId) {
      try {
        await stopAgentMutation.mutateAsync(agentRunId);
      } catch (error) {
        console.error('[PREVIEW] Error stopping agent:', error);
      }
    }
  }, [stopStreaming, agentRunId, stopAgentMutation]);

  const handleToolClick = useCallback((assistantMessageId: string | null, toolName: string) => {
    console.log('[PREVIEW] Tool clicked:', toolName);
    toast.info(`Tool: ${toolName} (Preview mode - tool details not available)`);
  }, []);


  return (
    <div className="h-full flex flex-col bg-muted dark:bg-muted/30">
      <div className="flex-shrink-0 flex items-center gap-3 p-8">
        <div
          className="h-10 w-10 flex items-center justify-center rounded-lg text-lg"
          style={{ backgroundColor: color }}
        >
          {avatar}
        </div>
        <div className="flex-1">
          <h3 className="font-semibold">{agent.name || 'Unnamed Agent'}</h3>
        </div>
        <Badge variant="highlight" className="text-sm">Preview Mode</Badge>
      </div>
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto scrollbar-hide">
          <ThreadContent
            messages={messages}
            streamingTextContent={streamingTextContent}
            streamingToolCall={streamingToolCall}
            agentStatus={agentStatus}
            handleToolClick={handleToolClick}
            handleOpenFileViewer={() => { }}
            streamHookStatus={streamHookStatus}
            isPreviewMode={true}
            agentName={agent.name}
            agentAvatar={avatar}
            emptyStateComponent={
              <div className="flex flex-col items-center text-center text-muted-foreground/80">
                <div className="flex w-20 aspect-square items-center justify-center rounded-2xl bg-muted-foreground/10 p-4 mb-4">
                  <div className="text-4xl">{avatar}</div>
                </div>
                <p className='w-[60%] text-2xl mb-3'>Start conversation with <span className='text-primary/80 font-semibold'>{agent.name}</span></p>
                <p className='w-[70%] text-sm text-muted-foreground/60'>Test your agent's configuration and chat back and forth to see how it performs with your current settings, tools, and knowledge base.</p>
              </div>
            }
          />
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="flex-shrink-0">
        <div className="p-0 md:p-4 md:px-10">
          <ChatInput
            ref={chatInputRef}
            onSubmit={threadId ? handleSubmitMessage : handleSubmitFirstMessage}
            loading={isSubmitting}
            placeholder={`Message ${agent.name || 'agent'}...`}
            value={inputValue}
            onChange={setInputValue}
            disabled={isSubmitting}
            isAgentRunning={agentStatus === 'running' || agentStatus === 'connecting'}
            onStopAgent={handleStopAgent}
            agentName={agent.name}
            hideAttachments={false}
            bgColor='bg-muted-foreground/10'
            selectedAgentId={agent.agent_id}
            onAgentSelect={() => {
              toast.info("You can only test the agent you are currently configuring");
            }}
            thinkingEnabled={thinkingEnabled}
            onThinkingChange={setThinkingEnabled}
            reasoningEffort={reasoningEffort}
            onReasoningEffortChange={setReasoningEffort}
          />
        </div>
      </div>
    </div>
  );
};