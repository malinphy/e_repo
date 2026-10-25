import React from 'react';
import { ExternalLink, ShoppingCart, Star, ShieldCheck } from 'lucide-react';
import type { Product } from '../types';

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
  index?: number;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onAddToCart, index }) => {
  const sourceClass = `badge-${product.source?.toLowerCase() || 'walmart'}`;
  const sourceLabel = product.source ? product.source.toUpperCase() : 'STORE';

  return (
    <div className="product-card fade-in">
      {/* Product Image */}
      <div className="product-image-container">
        {product.image ? (
          <img
            src={product.image}
            alt={product.title}
            className="product-image"
            loading="lazy"
            onError={(e) => {
              // Fallback placeholder SVG
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
        ) : (
          <div className="product-image-placeholder">
            <ShoppingCart size={32} strokeWidth={1.5} className="placeholder-icon" />
          </div>
        )}
        <div className="product-source-badge">
          <span className={`badge ${sourceClass}`}>{sourceLabel}</span>
        </div>
        {index !== undefined && (
          <span className="product-index-badge">#{index + 1}</span>
        )}
      </div>

      {/* Product Details */}
      <div className="product-body">
        <h4 className="product-title" title={product.title}>
          {product.title}
        </h4>

        {/* Rating & Delivery */}
        <div className="product-meta">
          {product.rating !== null && product.rating !== undefined ? (
            <div className="product-rating">
              <Star size={13} fill="#f59e0b" color="#f59e0b" />
              <span>{Number(product.rating).toFixed(1)}</span>
              {product.reviews_count && (
                <span className="reviews-count">({product.reviews_count})</span>
              )}
            </div>
          ) : (
            <div className="product-rating-verified">
              <ShieldCheck size={13} color="#10b981" />
              <span>Doğrulanmış Ürün</span>
            </div>
          )}
        </div>

        {/* Price & Actions */}
        <div className="product-footer">
          <div className="product-price-box">
            <span className="product-currency">{product.currency === 'USD' ? '$' : product.currency || '$'}</span>
            <span className="product-price">{Number(product.price).toFixed(2)}</span>
          </div>

          <div className="product-actions">
            {product.url && (
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-icon product-link-btn"
                title="Mağazada Görüntüle"
              >
                <ExternalLink size={15} />
              </a>
            )}
            <button
              onClick={() => onAddToCart && onAddToCart(product)}
              className="btn-add-cart"
              title="Sepete Ekle"
            >
              <ShoppingCart size={14} />
              <span>Ekle</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
