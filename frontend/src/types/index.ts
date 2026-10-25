export interface Product {
  id: string;
  title: string;
  price: number;
  currency: string;
  source: 'walmart' | 'ebay' | 'amazon' | 'google_shopping' | string;
  url: string;
  rating?: number | null;
  image?: string | null;
  reviews_count?: number | null;
  delivery_info?: string | null;
}

export interface CartItem {
  item_id: number;
  product_id: string;
  title: string;
  source: string;
  price: number;
  quantity: number;
  currency: string;
  url?: string;
  image?: string;
}

export interface CartViewResponse {
  user_id: string;
  total_items: number;
  total_amount: number;
  currency: string;
  items: CartItem[];
  formatted_message: string;
}

export interface PendingAction {
  action: string;
  summary?: string;
  total_amount?: number;
  items?: CartItem[] | any[];
  [key: string]: any;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  created_at?: string;
  products?: Product[];
  cart?: any[];
  pending_action?: PendingAction | null;
  isStreaming?: boolean;
}

export interface ChatResponse {
  reply: string;
  intent: string;
  user_id: string;
  thread_id: string;
  chat_id: string;
  products: Product[];
  cart: any[];
  pending_action?: PendingAction | null;
}

export interface ThreadSummary {
  thread_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ThreadMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  created_at: string;
  metadata?: {
    products?: Product[];
    cart?: any[];
    search_query?: any;
    pending_action?: any;
    [key: string]: any;
  } | null;
}
