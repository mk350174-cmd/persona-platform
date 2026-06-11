import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket(personaId, apiKey) {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [visualParams, setVisualParams] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!personaId || !apiKey) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${personaId}?tier=full`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
        // Send auth token
        ws.send(JSON.stringify({
          type: 'auth',
          token: apiKey,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'visual_params':
              setVisualParams(data.data);
              break;

            case 'text_chunk':
              if (data.full) {
                setIsLoading(false);
              } else {
                setMessages((prev) => {
                  const lastMsg = prev[prev.length - 1];
                  if (lastMsg?.role === 'assistant' && !lastMsg?.complete) {
                    return [
                      ...prev.slice(0, -1),
                      {
                        ...lastMsg,
                        content: lastMsg.content + data.text,
                      },
                    ];
                  }
                  return [
                    ...prev,
                    {
                      role: 'assistant',
                      content: data.text,
                      complete: false,
                    },
                  ];
                });
              }
              break;

            case 'audio_ready':
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg?.role === 'assistant') {
                  return [
                    ...prev.slice(0, -1),
                    {
                      ...lastMsg,
                      audio_b64: data.audio_b64,
                      mime_type: data.mime_type,
                      complete: true,
                    },
                  ];
                }
                return prev;
              });
              break;

            case 'visual_update':
              setVisualParams(data.data);
              break;

            case 'error':
              setError(data.detail);
              setIsLoading(false);
              break;

            case 'backpressure':
              console.warn('WebSocket backpressure:', data.detail);
              break;

            case 'done':
              setIsLoading(false);
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg?.role === 'assistant' && !lastMsg?.complete) {
                  return [
                    ...prev.slice(0, -1),
                    { ...lastMsg, complete: true },
                  ];
                }
                return prev;
              });
              break;

            default:
              break;
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('Connection error. Please try again.');
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
      };

      wsRef.current = ws;

      return () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        }
      };
    } catch (err) {
      setError('Failed to connect to chat');
      console.error('WebSocket creation error:', err);
    }
  }, [personaId, apiKey]);

  const sendMessage = useCallback((text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected to chat');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      setMessages((prev) => [...prev, { role: 'user', content: text }]);

      wsRef.current.send(
        JSON.stringify({
          type: 'message',
          text: text,
        })
      );
    } catch (err) {
      setError('Failed to send message');
      setIsLoading(false);
      console.error('Send message error:', err);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
  }, []);

  return {
    messages,
    isConnected,
    isLoading,
    error,
    visualParams,
    sendMessage,
    disconnect,
  };
}
