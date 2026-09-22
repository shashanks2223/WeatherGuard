import React, { useEffect, useRef } from 'react';
import { ShieldCheck, Loader2 } from 'lucide-react';
import { ChatMessage } from '../types';
import { MessageItem } from './MessageItem';

interface ChatThreadProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export const ChatThread: React.FC<ChatThreadProps> = ({ messages, isLoading }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-thread">
      {messages.length === 0 ? (
        <div className="welcome-box">
          <ShieldCheck className="welcome-icon" />
          <h2 className="welcome-title">WeatherGuard Safety Engine</h2>
          <p className="welcome-desc">
            Natural language outdoor safety advisory governed by deterministic SOP policies and live Open-Meteo weather facts.
            The LLM never independently invents safety rules or estimates forecast numbers.
          </p>
        </div>
      ) : (
        messages.map((msg) => <MessageItem key={msg.id} message={msg} />)
      )}

      {isLoading && (
        <div className="loading-indicator">
          <Loader2 size={16} className="spin-icon" />
          <span>Retrieving live weather & evaluating deterministic SOP policies...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
