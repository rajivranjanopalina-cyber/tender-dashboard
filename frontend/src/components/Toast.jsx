import { useState, useCallback, createContext, useContext } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), duration);
  }, []);

  return (
    <ToastContext.Provider value={addToast}>
      {children}
      <div style={{ position: 'fixed', top: '1rem', right: '1rem', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {toasts.map((toast) => (
          <div key={toast.id} style={{
            padding: '0.75rem 1.25rem', borderRadius: '8px', color: '#fff', fontSize: '0.9rem',
            background: toast.type === 'error' ? '#ff4d4f' : toast.type === 'success' ? '#52c41a' : '#1890ff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          }}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
