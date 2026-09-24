import React from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip';
import { HelpCircle } from 'lucide-react';

export const HelpTip = ({ text, side = 'top', children }) => (
  <TooltipProvider delayDuration={200}>
    <Tooltip>
      <TooltipTrigger asChild>
        {children || (
          <span className="inline-flex items-center cursor-help">
            <HelpCircle className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600 transition-colors" />
          </span>
        )}
      </TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs text-xs">
        <p>{text}</p>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
);
