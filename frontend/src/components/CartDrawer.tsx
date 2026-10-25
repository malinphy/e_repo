import React from 'react';
import { X, Trash2, ShoppingBag, ArrowRight, ExternalLink } from 'lucide-react';
import type { CartItem } from '../types';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: CartItem[];
  totalAmount: number;
  currency: string;
  onRemoveItem: (itemRef: string) => void;
  onStartCheckout: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  items,
  totalAmount,
  currency,
  onRemoveItem,
  onStartCheckout,
}) => {
  if (!isOpen) return null;

  return (
    <div className="cart-drawer-overlay" onClick={onClose}>
      <div className="cart-drawer fade-in" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="cart-drawer-header">
          <div className="cart-header-title">
            <ShoppingBag size={20} color="#6366f1" />
            <h3>Shopping Cart</h3>
            <span className="cart-badge-count">{items.length}</span>
          </div>
          <button onClick={onClose} className="btn-icon" title="Close">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="cart-drawer-body">
          {items.length === 0 ? (
            <div className="cart-empty-state">
              <div className="cart-empty-icon">
                <ShoppingBag size={48} strokeWidth={1} color="#64748b" />
              </div>
              <h4>Your Cart is Empty</h4>
              <p>Ask the assistant to search for items and add them directly to your cart.</p>
            </div>
          ) : (
            <div className="cart-items-list">
              {items.map((item, idx) => (
                <div key={item.item_id || idx} className="cart-item-card fade-in">
                  <div className="cart-item-image">
                    {item.image ? (
                      <img src={item.image} alt={item.title} />
                    ) : (
                      <div className="cart-item-placeholder">
                        <ShoppingBag size={18} color="#94a3b8" />
                      </div>
                    )}
                  </div>

                  <div className="cart-item-info">
                    <span className="cart-item-title" title={item.title}>
                      {item.title}
                    </span>
                    <div className="cart-item-sub">
                      <span className="cart-item-source">{item.source?.toUpperCase() || 'STORE'}</span>
                      <span className="cart-item-qty">x{item.quantity}</span>
                    </div>
                    <div className="cart-item-price">
                      ${Number(item.price * item.quantity).toFixed(2)}
                    </div>
                  </div>

                  <div className="cart-item-actions">
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-icon-tiny"
                        title="View in Store"
                      >
                        <ExternalLink size={13} />
                      </a>
                    )}
                    <button
                      onClick={() => onRemoveItem(String(item.item_id || item.product_id))}
                      className="btn-icon-tiny btn-remove"
                      title="Remove from Cart"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="cart-drawer-footer">
            <div className="cart-total-row">
              <span className="cart-total-label">Subtotal:</span>
              <span className="cart-total-value">
                {currency === 'USD' ? '$' : currency} {totalAmount.toFixed(2)}
              </span>
            </div>
            <button onClick={onStartCheckout} className="btn-checkout-now">
              <span>Proceed to Checkout</span>
              <ArrowRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
