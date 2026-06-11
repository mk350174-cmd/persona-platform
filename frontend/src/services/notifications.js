/**
 * Real-time Notifications System
 * Uses WebSocket for live updates and browser Notification API
 */

class NotificationManager {
  constructor() {
    this.listeners = [];
    this.notifications = [];
    this.wsConnection = null;
    this.maxNotifications = 50;
    this.notificationQueue = [];
    this.isProcessing = false;
  }

  /**
   * Initialize notification system
   */
  async init(apiKey, userId) {
    this.apiKey = apiKey;
    this.userId = userId;

    // Request browser notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Connect to WebSocket for real-time notifications
    this.connectWebSocket();
  }

  /**
   * Connect to WebSocket for real-time notifications
   */
  connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/notifications?token=${this.apiKey}`;

    try {
      this.wsConnection = new WebSocket(wsUrl);

      this.wsConnection.onopen = () => {
        console.log('Notifications WebSocket connected');
        this.emit('connected');
      };

      this.wsConnection.onmessage = (event) => {
        try {
          const notification = JSON.parse(event.data);
          this.handleNotification(notification);
        } catch (err) {
          console.error('Failed to parse notification:', err);
        }
      };

      this.wsConnection.onerror = (error) => {
        console.error('Notifications WebSocket error:', error);
        this.emit('error', error);
      };

      this.wsConnection.onclose = () => {
        console.log('Notifications WebSocket closed');
        this.emit('disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => this.connectWebSocket(), 5000);
      };
    } catch (error) {
      console.error('Failed to connect to notifications:', error);
    }
  }

  /**
   * Handle incoming notification
   */
  handleNotification(notification) {
    // Add to notification list (keep max 50)
    if (this.notifications.length >= this.maxNotifications) {
      this.notifications.shift();
    }
    this.notifications.push({
      ...notification,
      timestamp: new Date(),
      id: `${notification.id}-${Date.now()}`,
    });

    // Show browser notification if permitted
    if (Notification.permission === 'granted') {
      this.showBrowserNotification(notification);
    }

    // Emit event to listeners
    this.emit('notification', notification);

    // Auto-dismiss non-critical notifications after 5 seconds
    if (notification.type !== 'error' && notification.type !== 'warning') {
      setTimeout(() => this.dismissNotification(notification.id), 5000);
    }
  }

  /**
   * Show browser notification
   */
  showBrowserNotification(notification) {
    if ('Notification' in window && Notification.permission === 'granted') {
      const options = {
        icon: '/favicon.svg',
        badge: '/favicon.svg',
        tag: `persona-${notification.type}`,
        requireInteraction: notification.type === 'error',
      };

      if (notification.body) {
        options.body = notification.body;
      }

      try {
        const browserNotification = new Notification(notification.title, options);

        // Handle notification click
        browserNotification.onclick = () => {
          window.focus();
          if (notification.action) {
            this.emit('action', { notification, action: notification.action });
          }
        };

        // Auto-close after 6 seconds
        setTimeout(() => browserNotification.close(), 6000);
      } catch (error) {
        console.error('Failed to show browser notification:', error);
      }
    }
  }

  /**
   * Send notification to UI listeners
   */
  addNotification(notification) {
    this.handleNotification(notification);
  }

  /**
   * Dismiss notification
   */
  dismissNotification(id) {
    this.notifications = this.notifications.filter((n) => n.id !== id);
    this.emit('dismiss', { id });
  }

  /**
   * Clear all notifications
   */
  clearAll() {
    this.notifications = [];
    this.emit('clear');
  }

  /**
   * Register listener
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  /**
   * Unregister listener
   */
  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((cb) => cb !== callback);
    }
  }

  /**
   * Emit event to listeners
   */
  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error('Notification listener error:', error);
        }
      });
    }
  }

  /**
   * Get recent notifications
   */
  getRecent(count = 10) {
    return this.notifications.slice(-count).reverse();
  }

  /**
   * Get notifications by type
   */
  getByType(type) {
    return this.notifications.filter((n) => n.type === type);
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.wsConnection?.readyState === WebSocket.OPEN;
  }

  /**
   * Disconnect
   */
  disconnect() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }
}

// Singleton instance
export const notificationManager = new NotificationManager();

/**
 * React hook for notifications
 */
export function useNotifications() {
  const [notifications, setNotifications] = React.useState([]);
  const [isConnected, setIsConnected] = React.useState(false);

  React.useEffect(() => {
    const handleNotification = (notification) => {
      setNotifications((prev) => [...prev, notification]);
    };

    const handleConnected = () => {
      setIsConnected(true);
    };

    const handleDisconnected = () => {
      setIsConnected(false);
    };

    notificationManager.on('notification', handleNotification);
    notificationManager.on('connected', handleConnected);
    notificationManager.on('disconnected', handleDisconnected);

    return () => {
      notificationManager.off('notification', handleNotification);
      notificationManager.off('connected', handleConnected);
      notificationManager.off('disconnected', handleDisconnected);
    };
  }, []);

  return {
    notifications: notificationManager.getRecent(),
    isConnected,
    dismiss: notificationManager.dismissNotification.bind(notificationManager),
    clearAll: notificationManager.clearAll.bind(notificationManager),
  };
}

export default notificationManager;
