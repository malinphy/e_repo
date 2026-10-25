import React from 'react';
import type { Product } from '../types';
import { ProductCard } from './ProductCard';

interface ProductGridProps {
  products: Product[];
  onAddToCart?: (product: Product) => void;
}

export const ProductGrid: React.FC<ProductGridProps> = ({ products, onAddToCart }) => {
  if (!products || products.length === 0) return null;

  return (
    <div className="product-grid-container">
      <div className="product-grid-header">
        <span className="product-grid-count">
          Bulunan Ürünler ({products.length})
        </span>
        <span className="product-grid-hint">
          Sohbete "ikincisini sepete ekle" yazabilir veya butonu kullanabilirsiniz.
        </span>
      </div>
      <div className="product-grid">
        {products.map((product, idx) => (
          <ProductCard
            key={product.id || `${product.source}-${idx}`}
            product={product}
            index={idx}
            onAddToCart={onAddToCart}
          />
        ))}
      </div>
    </div>
  );
};
