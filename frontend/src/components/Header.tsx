import React from 'react';
import { Menu, ShoppingBag } from 'lucide-react';

interface HeaderProps {
  onToggleSidebar: () => void;
  onOpenCart: () => void;
  cartItemCount: number;
  activeThreadTitle?: string;
  isBackendConnected?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  onOpenCart,
  cartItemCount,
  activeThreadTitle,
  isBackendConnected = true,
}) => {
  return (
    <header className="app-header">
      <div className="header-left">
        <button
          onClick={onToggleSidebar}
          className="btn-icon header-menu-btn"
          title="Toggle Sidebar"
        >
          <Menu size={20} />
        </button>

        <div className="header-title-box">
          <span className="header-thread-title">
            {activeThreadTitle || 'New Shopping Chat'}
          </span>
        </div>
      </div>

      <div className="header-center">
        <div className="system-status-indicator">
          <span className={`status-pulse ${isBackendConnected ? 'online' : 'offline'}`} />
          <span className="status-text">
            {isBackendConnected ? 'Agent Online' : 'Offline'}
          </span>
        </div>
      </div>

      <div className="header-right">
        <button onClick={onOpenCart} className="btn-cart-toggle" title="View Cart">
          <ShoppingBag size={18} />
          <span className="cart-text">Cart</span>
          {cartItemCount > 0 && (
            <span className="cart-badge-pill">{cartItemCount}</span>
          )}
        </button>
      </div>
    </header>
  );
};
