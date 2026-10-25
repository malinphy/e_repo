import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Loader2, ArrowUpRight } from 'lucide-react';
import type { ChatMessage, Product } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
  isInitializing?: boolean;
  onSendMessage: (text: string) => void;
  onAddToCart?: (product: Product) => void;
  onResumeCheckout?: (approved: boolean) => Promise<void>;
}

const QUICK_SUGGESTIONS = [
  { label: '🎧 Bluetooth headphones under $100', text: 'Find the best bluetooth headphones under 100 dollars' },
  { label: '💻 Mechanical keyboard for coders', text: 'Recommend a wireless mechanical keyboard for software developers' },
  { label: '🛍️ View my shopping cart', text: 'What items are currently in my cart?' },
  { label: '💳 Checkout and review order', text: 'Review my cart and start checkout' },
];

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  isInitializing = false,
  onSendMessage,
  onAddToCart,
  onResumeCheckout,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const prevMessagesCount = useRef(messages.length);

  // Auto scroll to bottom when new messages arrive or loading toggles
  useEffect(() => {
    if (messages.length > 0) {
      // Use instant scroll on initial message load to prevent layout flicker, smooth scroll on new turns
      const isInitialRender = prevMessagesCount.current === 0;
      prevMessagesCount.current = messages.length;

      messagesEndRef.current?.scrollIntoView({
        behavior: isInitialRender ? 'auto' : 'smooth',
      });
    }
  }, [messages.length, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-area">
      {/* Messages Stream */}
      <div className="messages-scroll-area">
        {isInitializing ? (
          <div className="welcome-hero fade-in">
            <div className="loading-bubble" style={{ margin: 'auto' }}>
              <Loader2 size={18} className="spin-icon" color="#818cf8" />
              <span>Loading chat history...</span>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="welcome-hero fade-in">
            <div className="welcome-icon-glow">
              <Sparkles size={36} color="#6366f1" />
            </div>
            <h2 className="welcome-title">What can I find for you today?</h2>
            <p className="welcome-subtitle">
              I can compare prices in real time across Walmart, eBay, and Amazon,
              manage your shopping cart, and guide you through seamless checkout.
            </p>

            <div className="suggestions-grid">
              {QUICK_SUGGESTIONS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(item.text)}
                  className="suggestion-card"
                >
                  <span>{item.label}</span>
                  <ArrowUpRight size={14} className="suggestion-arrow" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onAddToCart={onAddToCart}
                onResumeCheckout={onResumeCheckout}
              />
            ))}

            {isLoading && (
              <div className="assistant-loading-indicator fade-in">
                <div className="avatar-box assistant-avatar">
                  <Sparkles size={18} color="#6366f1" />
                </div>
                <div className="loading-bubble">
                  <Loader2 size={16} className="spin-icon" color="#818cf8" />
                  <span>Searching marketplaces and preparing response...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="chat-input-wrapper">
        <form onSubmit={handleSubmit} className="chat-input-form">
          <textarea
            ref={inputRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search for products, manage cart, or ask questions... (e.g. 'Add the 2nd item to cart')"
            rows={1}
            disabled={isLoading}
            className="chat-textarea"
          />

          <button
            type="submit"
            disabled={!inputText.trim() || isLoading}
            className="btn-send-message"
            title="Send (Enter)"
          >
            {isLoading ? (
              <Loader2 size={18} className="spin-icon" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </form>
        <div className="input-helper-text">
          Press Enter to send • Shift + Enter for new line • Routed by LangGraph
        </div>
      </div>
    </div>
  );
};
