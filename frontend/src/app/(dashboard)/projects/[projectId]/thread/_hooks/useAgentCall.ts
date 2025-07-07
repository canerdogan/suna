import { useCallback, useState } from 'react';
import { toast } from 'sonner';
import { useAddUserMessageMutation } from '@/hooks/react-query/threads/use-messages';
import { useStartAgentMutation, useStopAgentMutation } from '@/hooks/react-query/threads/use-agent-run';
import { UnifiedMessage } from '../_types';

export interface UseAgentCallReturn {
  handleAgentCall: (agentId: string, message?: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
}

export interface UseAgentCallParams {
  threadId: string;
  currentAgentRunId: string | null;
  currentAgentStatus: string;
  setAgentRunId: (id: string | null) => void;
  setSelectedAgentId: (id: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<UnifiedMessage[]>>;
  currentModelSettings?: {
    model_name?: string;
    enable_thinking?: boolean;
    reasoning_effort?: string;
  };
}

export function useAgentCall({
  threadId,
  currentAgentRunId,
  currentAgentStatus,
  setAgentRunId,
  setSelectedAgentId,
  setMessages,
  currentModelSettings,
}: UseAgentCallParams): UseAgentCallReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mutations
  const addUserMessageMutation = useAddUserMessageMutation();
  const startAgentMutation = useStartAgentMutation();
  const stopAgentMutation = useStopAgentMutation();

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const handleAgentCall = useCallback(async (agentId: string, message?: string) => {
    console.log('%c🚀 AGENT CALL HANDLER TRIGGERED! 🚀', 'background: magenta; color: white; font-size: 16px; padding: 5px;');
    console.log('%c🆔 [AGENT_CALL] Target Agent ID:', 'color: blue; font-size: 14px; font-weight: bold;', agentId);
    console.log('%c💬 [AGENT_CALL] Handoff Message:', 'color: green; font-size: 14px; font-weight: bold;', message || 'No message provided');
    console.log('%c⚙️ [AGENT_CALL] Current Model Settings:', 'color: purple; font-size: 14px; font-weight: bold;', currentModelSettings);
    
    if (!threadId) {
      const errorMsg = 'No thread ID available for agent call';
      console.error('[AGENT_CALL]', errorMsg);
      setError(errorMsg);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Stop current agent if running
      if (currentAgentRunId && currentAgentStatus === 'running') {
        console.log('%c🛑 [AGENT_CALL] Stopping current agent:', 'color: orange; font-weight: bold;', currentAgentRunId);
        await stopAgentMutation.mutateAsync(currentAgentRunId);
      }

      // Add the handoff message to the conversation if provided
      if (message) {
        console.log('%c📝 [AGENT_CALL] Adding handoff message to conversation', 'color: blue; font-weight: bold;');
        
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
        
        // Add to local state immediately for optimistic UI
        setMessages(prev => [...prev, handoffMessage]);
        
        // Save the handoff message to backend
        await addUserMessageMutation.mutateAsync({
          threadId,
          message
        });
      }

      // Start the new agent with current model settings preserved
      console.log('%c🔄 [AGENT_CALL] Starting target agent:', 'color: green; font-weight: bold;', agentId);
      
      // Combine agent_id with current model settings to preserve user's choices
      const agentOptions = {
        agent_id: agentId,
        ...currentModelSettings, // Spread current model settings to preserve them
      };
      
      console.log('%c🎛️ [AGENT_CALL] Agent options (preserving settings):', 'color: blue; font-weight: bold;', agentOptions);
      
      const agentResult = await startAgentMutation.mutateAsync({
        threadId,
        options: agentOptions
      });
      console.log('%c✅ [AGENT_CALL] Agent started with run ID:', 'color: green; font-weight: bold;', agentResult.agent_run_id);

      // Update state
      setAgentRunId(agentResult.agent_run_id);
      setSelectedAgentId(agentId);
      
      console.log('%c🎉 [AGENT_CALL] Successfully switched to agent with preserved settings!', 'background: green; color: white; font-weight: bold;');
      toast.success('Successfully switched to agent');
      
    } catch (error: any) {
      const errorMsg = error.message || 'Failed to switch to agent';
      console.error('%c❌ [AGENT_CALL] Error in agent call:', 'background: red; color: white; font-weight: bold;', error);
      setError(errorMsg);
      toast.error(`Failed to switch to agent: ${errorMsg}`);
    } finally {
      setIsLoading(false);
    }
  }, [
    threadId,
    currentAgentRunId,
    currentAgentStatus,
    setAgentRunId,
    setSelectedAgentId,
    setMessages,
    stopAgentMutation,
    addUserMessageMutation,
    startAgentMutation,
    currentModelSettings, // Add to dependencies to properly react to settings changes
  ]);

  return {
    handleAgentCall,
    isLoading,
    error,
    clearError,
  };
} 