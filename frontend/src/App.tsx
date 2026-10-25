import React, { useState, useEffect, useCallback } from 'react';
import { api } from './services/api';
import type { ChatMessage, ThreadSummary, CartItem, Product } from './types';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatArea } from './components/ChatArea';
import { CartDrawer } from './components/CartDrawer';
import './App.css';

export const App: React.FC = () => {
  const [userId] = useState<string>('guest_user');
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeThreadTitle, setActiveThreadTitle] = useState<string>('New Shopping Chat');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(true);

  // Cart State
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartTotal, setCartTotal] = useState<number>(0);
  const [cartCurrency, setCartCurrency] = useState<string>('USD');

  // Fetch Cart
  const refreshCart = useCallback(async () => {
    try {
      const res = await api.getCart(userId);
      setCartItems(res.items || []);
      setCartTotal(res.total_amount || 0);
      setCartCurrency(res.currency || 'USD');
    } catch (err) {
      console.warn('Could not refresh cart:', err);
    }
  }, [userId]);

  // Fetch Threads
  const loadThreads = useCallback(async () => {
    try {
      const list = await api.getThreads(userId);
      setThreads(list);
      setIsBackendConnected(true);
      return list;
    } catch (err) {
      console.error('Failed to load threads:', err);
      setIsBackendConnected(false);
      return [];
    }
  }, [userId]);

  // Select Thread & Load its messages
  const handleSelectThread = useCallback(async (threadId: string, title?: string) => {
    try {
      setActiveThreadId(threadId);
      if (title) {
        setActiveThreadTitle(title);
      } else {
        setThreads((current) => {
          const matched = current.find((t) => t.thread_id === threadId);
          if (matched) setActiveThreadTitle(matched.title);
          return current;
        });
      }

      setIsLoading(true);
      const threadMsgs = await api.getThreadMessages(threadId);
      const formatted: ChatMessage[] = threadMsgs.map((m) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        intent: m.intent,
        created_at: m.created_at,
        products: m.metadata?.products,
        cart: m.metadata?.cart,
        pending_action: m.metadata?.pending_action,
      }));
      setMessages(formatted);
    } catch (err) {
      console.error('Failed to load messages for thread:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial Load
  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      setIsInitializing(true);
      try {
        const list = await loadThreads();
        await refreshCart();
        if (isMounted && list && list.length > 0) {
          await handleSelectThread(list[0].thread_id, list[0].title);
        }
      } finally {
        if (isMounted) {
          setIsInitializing(false);
        }
      }
    };
    init();
    return () => {
      isMounted = false;
    };
  }, [loadThreads, refreshCart, handleSelectThread]);

  // New Chat
  const handleNewChat = () => {
    setActiveThreadId(null);
    setActiveThreadTitle('New Shopping Chat');
    setMessages([]);
  };

  // Delete Thread
  const handleDeleteThread = async (threadId: string) => {
    try {
      await api.deleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
      if (activeThreadId === threadId) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
  };

  // Send Message
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await api.sendMessage(text, userId, activeThreadId);

      // If was a new chat, update activeThreadId and reload threads list
      if (!activeThreadId) {
        setActiveThreadId(response.thread_id);
        setActiveThreadTitle(text.slice(0, 40));
        loadThreads();
      }

      const assistantMessage: ChatMessage = {
        id: response.chat_id || `asst_${Date.now()}`,
        role: 'assistant',
        content: response.reply,
        intent: response.intent,
        products: response.products,
        cart: response.cart,
        pending_action: response.pending_action,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If cart was modified, refresh cart drawer
      if (response.intent === 'cart' || response.cart) {
        refreshCart();
      }
      setIsBackendConnected(true);
    } catch (err: any) {
      console.error('Chat error:', err);
      const errorMessage: ChatMessage = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `⚠️ An error occurred: ${err.message || 'Could not connect to server. Please verify the backend is running.'}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsBackendConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  // Quick Add to Cart from Product Card
  const handleAddToCart = (product: Product) => {
    handleSendMessage(`Add "${product.title}" to cart`);
  };

  // Human-in-the-Loop: Resume Checkout Approval / Cancel
  const handleResumeCheckout = async (approved: boolean) => {
    if (!activeThreadId) return;

    try {
      setIsLoading(true);
      const response = await api.resumeCheckout(activeThreadId, approved, userId);

      const resumeMessage: ChatMessage = {
        id: `res_${Date.now()}`,
        role: 'assistant',
        content: response.reply,
        intent: 'checkout',
        cart: response.cart,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, resumeMessage]);
      refreshCart();
    } catch (err: any) {
      console.error('Resume checkout error:', err);
      const errorMessage: ChatMessage = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `⚠️ Error processing order confirmation: ${err.message}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Remove Item from Cart Drawer
  const handleRemoveCartItem = async (itemRef: string) => {
    try {
      await api.removeCartItem(userId, itemRef);
      refreshCart();
    } catch (err) {
      console.error('Failed to remove cart item:', err);
    }
  };

  // Start Checkout from Cart Drawer
  const handleStartCheckout = () => {
    setIsCartOpen(false);
    handleSendMessage('Review my cart and proceed to checkout');
  };

  return (
    <div className="app-container">
      {/* ChatGPT-style Left Sidebar */}
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        onDeleteThread={handleDeleteThread}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((prev) => !prev)}
        userId={userId}
      />

      {/* Main Content Area */}
      <div className="main-content">
        <Header
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          onOpenCart={() => setIsCartOpen(true)}
          cartItemCount={cartItems.length}
          activeThreadTitle={activeThreadTitle}
          isBackendConnected={isBackendConnected}
        />

        <ChatArea
          messages={messages}
          isLoading={isLoading}
          isInitializing={isInitializing}
          onSendMessage={handleSendMessage}
          onAddToCart={handleAddToCart}
          onResumeCheckout={handleResumeCheckout}
        />
      </div>

      {/* Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        items={cartItems}
        totalAmount={cartTotal}
        currency={cartCurrency}
        onRemoveItem={handleRemoveCartItem}
        onStartCheckout={handleStartCheckout}
      />
    </div>
  );
};

export default App;
