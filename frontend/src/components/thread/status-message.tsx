import React from 'react';
import { Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatusMessageProps {
  phase?: number;
  total?: number;
  message: string;
  className?: string;
}

export const StatusMessage: React.FC<StatusMessageProps> = ({
  phase,
  total,
  message,
  className,
}) => {
  return (
    <div className={cn(
      'flex items-center gap-3 p-3 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950',
      className
    )}>
      <div className="flex-shrink-0">
        <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-sm text-foreground">
            {message}
          </span>
          {phase && total && (
            <span className="text-xs text-muted-foreground font-mono ml-2">
              {phase}/{total}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatusMessage;