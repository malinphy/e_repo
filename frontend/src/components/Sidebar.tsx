import React from 'react';
import { Plus, MessageSquare, Trash2, ShoppingBag, ChevronLeft, User } from 'lucide-react';
import type { ThreadSummary } from '../types';

interface SidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewChat: () => void;
  onDeleteThread: (threadId: string) => void;
  isOpen: boolean;
  onToggle: () => void;
  userId: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onNewChat,
  onDeleteThread,
  isOpen,
  onToggle,
  userId,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div className="sidebar-backdrop" onClick={onToggle} />
      )}

      <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
        {/* Brand Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="brand-icon-box">
              <ShoppingBag size={20} color="#ffffff" />
            </div>
            <div className="brand-text">
              <span className="brand-title">ShopAgent</span>
              <span className="brand-tag">LangGraph AI</span>
            </div>
          </div>
          <button
            onClick={onToggle}
            className="btn-icon sidebar-collapse-btn"
            title="Kenar çubuğunu gizle"
          >
            <ChevronLeft size={18} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="sidebar-action-container">
          <button onClick={onNewChat} className="btn-new-chat">
            <Plus size={18} />
            <span>Yeni Sohbet</span>
          </button>
        </div>

        {/* Threads History List */}
        <div className="sidebar-threads-container">
          <div className="threads-section-title">Geçmiş Sohbetler</div>
          {threads.length === 0 ? (
            <div className="threads-empty">
              <span>Henüz kayıtlı sohbet yok. Yeni bir sohbet başlatın!</span>
            </div>
          ) : (
            <div className="threads-list">
              {threads.map((t) => {
                const isActive = t.thread_id === activeThreadId;
                return (
                  <div
                    key={t.thread_id}
                    className={`thread-item ${isActive ? 'active' : ''}`}
                    onClick={() => onSelectThread(t.thread_id)}
                  >
                    <MessageSquare size={16} className="thread-icon" />
                    <span className="thread-title" title={t.title || 'Sohbet'}>
                      {t.title || 'Yeni Sohbet'}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteThread(t.thread_id);
                      }}
                      className="btn-delete-thread"
                      title="Sohbeti Sil"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer User Info */}
        <div className="sidebar-footer">
          <div className="user-profile-badge">
            <div className="user-avatar-small">
              <User size={14} />
            </div>
            <div className="user-info">
              <span className="user-name">{userId}</span>
              <span className="user-status-dot">Çevrimiçi</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
