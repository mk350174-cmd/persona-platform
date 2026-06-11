import React, { useEffect, useState } from 'react';
import { notificationManager } from '../services/notifications';

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const handleNotification = (notification) => {
      setNotifications((prev) => [...prev, notification]);
    };

    const handleDismiss = ({ id }) => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    };

    const handleClear = () => {
      setNotifications([]);
    };

    notificationManager.on('notification', handleNotification);
    notificationManager.on('dismiss', handleDismiss);
    notificationManager.on('clear', handleClear);

    return () => {
      notificationManager.off('notification', handleNotification);
      notificationManager.off('dismiss', handleDismiss);
      notificationManager.off('clear', handleClear);
    };
  }, []);

  const getNotificationStyles = (type) => {
    const baseStyles = 'glass-panel rounded-lg p-4 flex gap-3 items-start backdrop-blur-xl border';
    const typeStyles = {
      success: 'border-literature-green/30 bg-literature-green/10',
      error: 'border-error/30 bg-error/10',
      warning: 'border-leadership-gold/30 bg-leadership-gold/10',
      info: 'border-science-cyan/30 bg-science-cyan/10',
    };
    return `${baseStyles} ${typeStyles[type] || typeStyles.info}`;
  };

  const getNotificationIcon = (type) => {
    const icons = {
      success: 'check_circle',
      error: 'error',
      warning: 'warning',
      info: 'info',
    };
    return icons[type] || 'notifications';
  };

  const getNotificationColor = (type) => {
    const colors = {
      success: 'text-literature-green',
      error: 'text-error',
      warning: 'text-leadership-gold',
      info: 'text-science-cyan',
    };
    return colors[type] || 'text-on-surface-variant';
  };

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-md space-y-3 max-h-96 overflow-y-auto">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={getNotificationStyles(notification.type)}
          role="alert"
        >
          <span className={`material-symbols-outlined ${getNotificationColor(notification.type)} shrink-0`}>
            {getNotificationIcon(notification.type)}
          </span>

          <div className="flex-1">
            {notification.title && (
              <h4 className="font-semibold text-on-surface mb-1">{notification.title}</h4>
            )}
            {notification.body && (
              <p className="text-sm text-on-surface-variant">{notification.body}</p>
            )}

            {notification.action && (
              <button
                onClick={() => {
                  notificationManager.emit('action', { notification, action: notification.action });
                  notificationManager.dismissNotification(notification.id);
                }}
                className="mt-2 text-xs font-semibold text-on-surface hover:underline"
              >
                {notification.actionLabel || 'Action'} →
              </button>
            )}
          </div>

          <button
            onClick={() => notificationManager.dismissNotification(notification.id)}
            className="text-on-surface-variant hover:text-on-surface transition-colors shrink-0"
            aria-label="Dismiss notification"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>
      ))}
    </div>
  );
}
