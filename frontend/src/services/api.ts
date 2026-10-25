import type {
  ChatResponse,
  CartViewResponse,
  ThreadSummary,
  ThreadMessageItem,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // POST /api/chat - Send message to LangGraph agent
  async sendMessage(
    message: string,
    userId: string = 'guest_user',
    threadId?: string | null
  ): Promise<ChatResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        user_id: userId,
        thread_id: threadId || null,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Mesaj iletilirken bir hata oluştu.');
    }
    return res.json();
  }

  // POST /api/chat/resume - Resume Human-in-the-Loop checkout
  async resumeCheckout(
    threadId: string,
    approved: boolean,
    userId: string = 'guest_user'
  ): Promise<ChatResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        thread_id: threadId,
        approved,
        user_id: userId,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Sipariş onayı işlenemedi.');
    }
    return res.json();
  }

  // GET /api/chat/threads - List all chat threads for sidebar
  async getThreads(userId: string = 'guest_user'): Promise<ThreadSummary[]> {
    const res = await fetch(`${this.baseUrl}/api/chat/threads?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) {
      throw new Error('Sohbet geçmişi yüklenemedi.');
    }
    return res.json();
  }

  // POST /api/chat/threads - Create new chat thread
  async createThread(userId: string = 'guest_user', title: string = 'Yeni Sohbet'): Promise<ThreadSummary> {
    const res = await fetch(`${this.baseUrl}/api/chat/threads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, title }),
    });
    if (!res.ok) {
      throw new Error('Yeni sohbet oluşturulamadı.');
    }
    return res.json();
  }

  // GET /api/chat/threads/:id/messages - Get messages of a thread
  async getThreadMessages(threadId: string): Promise<ThreadMessageItem[]> {
    const res = await fetch(`${this.baseUrl}/api/chat/threads/${encodeURIComponent(threadId)}/messages`);
    if (!res.ok) {
      throw new Error('Sohbet mesajları yüklenemedi.');
    }
    return res.json();
  }

  // DELETE /api/chat/threads/:id - Delete a thread
  async deleteThread(threadId: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${this.baseUrl}/api/chat/threads/${encodeURIComponent(threadId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error('Sohbet silinemedi.');
    }
    return res.json();
  }

  // GET /api/cart - Get active shopping cart
  async getCart(userId: string = 'guest_user'): Promise<CartViewResponse> {
    const res = await fetch(`${this.baseUrl}/api/cart?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) {
      throw new Error('Sepet bilgisi alınamadı.');
    }
    return res.json();
  }

  // POST /api/cart/remove - Remove item from cart
  async removeCartItem(userId: string = 'guest_user', itemReference: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/cart/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        item_reference: itemReference,
      }),
    });
    if (!res.ok) {
      throw new Error('Ürün sepetten silinemedi.');
    }
    return res.json();
  }

  // GET /api/search - Get latest search results for thread
  async getLatestSearchResults(threadId: string, userId: string = 'guest_user') {
    const res = await fetch(`${this.baseUrl}/api/search?thread_id=${encodeURIComponent(threadId)}&user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) {
      throw new Error('Arama sonuçları alınamadı.');
    }
    return res.json();
  }
}

export const api = new ApiService();
