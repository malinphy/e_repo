import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import type { PendingAction } from '../types';

interface CheckoutInterruptCardProps {
  pendingAction: PendingAction;
  onApprove: (approved: boolean) => Promise<void>;
}

export const CheckoutInterruptCard: React.FC<CheckoutInterruptCardProps> = ({
  pendingAction,
  onApprove,
}) => {
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState<boolean | null>(null);

  const handleAction = async (approved: boolean) => {
    try {
      setLoading(true);
      await onApprove(approved);
      setCompleted(approved);
    } finally {
      setLoading(false);
    }
  };

  if (completed !== null) {
    return (
      <div className={`checkout-result-card ${completed ? 'approved' : 'cancelled'} fade-in`}>
        {completed ? (
          <>
            <CheckCircle2 size={20} className="icon-success" />
            <span>Order approved and successfully placed!</span>
          </>
        ) : (
          <>
            <XCircle size={20} className="icon-cancel" />
            <span>Order cancelled. Your cart items are preserved.</span>
          </>
        )}
      </div>
    );
  }

  const items = pendingAction.items || [];
  const totalAmount = pendingAction.total_amount;

  return (
    <div className="checkout-interrupt-card fade-in">
      <div className="interrupt-header">
        <div className="interrupt-title-group">
          <div className="interrupt-icon-pulse">
            <AlertCircle size={20} color="#6366f1" />
          </div>
          <div>
            <h4 className="interrupt-title">Order Approval Required</h4>
            <p className="interrupt-subtitle">
              Please review your order summary below to complete your purchase.
            </p>
          </div>
        </div>
      </div>

      {/* Items preview if available */}
      {items.length > 0 && (
        <div className="interrupt-items-list">
          {items.map((item: any, idx: number) => (
            <div key={idx} className="interrupt-item-row">
              <span className="interrupt-item-title">
                {item.quantity || 1}x {item.title || item.product_id}
              </span>
              <span className="interrupt-item-price">
                ${((item.price || item.price_snapshot || 0) * (item.quantity || 1)).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Total Amount */}
      {totalAmount !== undefined && (
        <div className="interrupt-total-row">
          <span>Total Amount:</span>
          <span className="interrupt-total-price">
            ${Number(totalAmount).toFixed(2)}
          </span>
        </div>
      )}

      {/* Decision Buttons */}
      <div className="interrupt-actions">
        <button
          onClick={() => handleAction(true)}
          disabled={loading}
          className="btn-confirm-order"
        >
          {loading ? (
            <Loader2 size={16} className="spin-icon" />
          ) : (
            <CheckCircle2 size={16} />
          )}
          <span>Confirm Order</span>
        </button>

        <button
          onClick={() => handleAction(false)}
          disabled={loading}
          className="btn-cancel-order"
        >
          <XCircle size={16} />
          <span>Cancel</span>
        </button>
      </div>
    </div>
  );
};
