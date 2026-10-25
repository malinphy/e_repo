import React from 'react';
import { User, Sparkles, ShoppingCart, Search, CreditCard, HelpCircle, MessageSquare } from 'lucide-react';
import type { ChatMessage, Product } from '../types';
import { ProductGrid } from './ProductGrid';
import { CheckoutInterruptCard } from './CheckoutInterruptCard';

interface MessageBubbleProps {
  message: ChatMessage;
  onAddToCart?: (product: Product) => void;
  onResumeCheckout?: (approved: boolean) => Promise<void>;
}

// Intent badge helper
const getIntentInfo = (intent?: string) => {
  switch (intent?.toLowerCase()) {
    case 'search':
      return { label: 'Arama', icon: Search, colorClass: 'intent-search' };
    case 'cart':
      return { label: 'Sepet İşlemi', icon: ShoppingCart, colorClass: 'intent-cart' };
    case 'checkout':
      return { label: 'Ödeme / Onay', icon: CreditCard, colorClass: 'intent-checkout' };
    case 'qa':
    case 'product_qa':
      return { label: 'Ürün Soru-Cevap', icon: HelpCircle, colorClass: 'intent-qa' };
    case 'chitchat':
      return { label: 'Sohbet', icon: MessageSquare, colorClass: 'intent-chat' };
    default:
      return null;
  }
};

// Simple Markdown Formatter
const renderFormattedText = (text: string) => {
  if (!text) return null;

  // Split into paragraphs / lines
  const lines = text.split('\n');

  return lines.map((line, idx) => {
    if (!line.trim()) {
      return <div key={idx} className="bubble-line-break" />;
    }

    // Bold replacement (**text**)
    const parts = line.split(/(\*\*.*?\*\*)/g);
    const formattedParts = parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });

    // List item check
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      return (
        <li key={idx} className="bubble-list-item">
          {formattedParts}
        </li>
      );
    }

    return (
      <p key={idx} className="bubble-paragraph">
        {formattedParts}
      </p>
    );
  });
};

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onAddToCart,
  onResumeCheckout,
}) => {
  const isUser = message.role === 'user';
  const intentInfo = !isUser ? getIntentInfo(message.intent) : null;
  const IntentIcon = intentInfo?.icon;

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'assistant-row'} fade-in`}>
      {/* Avatar */}
      <div className={`avatar-box ${isUser ? 'user-avatar' : 'assistant-avatar'}`}>
        {isUser ? (
          <User size={18} color="#ffffff" />
        ) : (
          <Sparkles size={18} color="#6366f1" />
        )}
      </div>

      {/* Bubble Content */}
      <div className="message-content-wrapper">
        <div className="message-header-meta">
          <span className="sender-name">{isUser ? 'Siz' : 'ShopAgent AI'}</span>
          {intentInfo && IntentIcon && (
            <span className={`intent-badge ${intentInfo.colorClass}`}>
              <IntentIcon size={12} />
              <span>{intentInfo.label}</span>
            </span>
          )}
        </div>

        <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          <div className="bubble-text">{renderFormattedText(message.content)}</div>
        </div>

        {/* Product Grid if products attached */}
        {message.products && message.products.length > 0 && (
          <ProductGrid products={message.products} onAddToCart={onAddToCart} />
        )}

        {/* Human-in-the-Loop Checkout Interrupt Card */}
        {message.pending_action && onResumeCheckout && (
          <CheckoutInterruptCard
            pendingAction={message.pending_action}
            onApprove={onResumeCheckout}
          />
        )}
      </div>
    </div>
  );
};
