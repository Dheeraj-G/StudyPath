/**
 * WebSocket Service for Real-time Communication
 * Handles WebSocket connections and message management
 */

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  type?: 'chat' | 'file_upload' | 'system';
}

export interface WebSocketMessage {
  type: 'chat' | 'file_upload' | 'response' | 'error' | 'ping' | 'agent_response' | 'parsing_progress' | 'processing_complete' | 'processing_error';
  content?: string;
  data?: any;
  timestamp: string;
}

export interface ParsingProgress {
  file_type: string;
  parsed: number;
  total: number;
  percentage: number;
}

export interface WebSocketCallbacks {
  onMessage?: (message: ChatMessage) => void;
  onError?: (error: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onAgentResponse?: (agentType: string, response: any) => void;
  onParsingProgress?: (progress: ParsingProgress) => void;
  onProcessingComplete?: (message: string, data?: any) => void;
  onProcessingError?: (message: string, error?: string) => void;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private userId: string | null = null;
  private baseUrl: string;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  setCallbacks(callbacks: WebSocketCallbacks) {
    this.callbacks = callbacks;
  }

  async connect(userId: string): Promise<void> {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;
    this.userId = userId;

    try {
      const wsUrl = `${this.baseUrl}/ws/${userId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.callbacks.onConnect?.();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          this.callbacks.onError?.('Failed to parse message');
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnecting = false;
        this.callbacks.onDisconnect?.();
        
        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        // WebSocket error events don't have useful properties, but we can log the connection attempt
        const attemptedUrl = `${this.baseUrl}/ws/${userId}`;
        console.error('WebSocket connection error:', {
          url: attemptedUrl,
          readyState: this.ws?.readyState,
          userId: userId,
          error: error
        });
        this.isConnecting = false;
        this.callbacks.onError?.('WebSocket connection failed. Please check if the backend server is running.');
      };

    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      this.isConnecting = false;
      this.callbacks.onError?.('Failed to connect to WebSocket');
    }
  }

  async connectAndWait(userId: string, timeoutMs: number = 5000): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    await this.connect(userId);
    await new Promise<void>((resolve, reject) => {
      const started = Date.now();
      const check = () => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) return resolve();
        if (Date.now() - started > timeoutMs) return reject(new Error('WebSocket connect timeout'));
        setTimeout(check, 100);
      };
      check();
    });
  }

  private scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      if (this.userId) {
        this.connect(this.userId);
      }
    }, delay);
  }

  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'response':
        if (message.content) {
          const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content)
          this.callbacks.onMessage?.({
            role: 'assistant',
            content,
            timestamp: message.timestamp,
          });
        }
        break;
      
      case 'agent_response':
        if (message.data) {
          this.callbacks.onAgentResponse?.(message.data.agent_type, message.data.response);
        }
        break;
      
      case 'error':
        this.callbacks.onError?.(typeof message.content === 'string' ? message.content : 'Unknown error');
        break;
      
      case 'ping':
        // Respond to ping with pong
        this.sendMessage('pong', {});
        break;
      
      case 'parsing_progress':
        if (message.data) {
          this.callbacks.onParsingProgress?.(message.data);
        }
        break;
      
      case 'processing_complete':
        this.callbacks.onProcessingComplete?.(
          message.content || 'Processing completed successfully',
          message.data
        );
        // Also add as a regular message
        if (message.content) {
          this.callbacks.onMessage?.({
            role: 'assistant',
            content: message.content,
            timestamp: message.timestamp,
          });
        }
        break;
      
      case 'processing_error':
        this.callbacks.onProcessingError?.(
          message.content || 'Processing failed',
          message.data?.error
        );
        // Also add as an error message
        if (message.content) {
          this.callbacks.onMessage?.({
            role: 'assistant',
            content: message.content,
            timestamp: message.timestamp,
          });
        }
        break;
      
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  sendMessage(type: string, content: string, data?: any) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return;
    }

    const message: WebSocketMessage = {
      type: type as any,
      content,
      data,
      timestamp: new Date().toISOString(),
    };

    this.ws.send(JSON.stringify(message));
  }

  sendChatMessage(content: string) {
    this.sendMessage('chat', content);
    
    // Immediately show user message
    this.callbacks.onMessage?.({
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    });
  }

  sendFileUploadNotification(fileIds: string[]) {
    this.sendMessage('file_upload', '', { file_ids: fileIds });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'User disconnected');
      this.ws = null;
    }
    this.userId = null;
    this.reconnectAttempts = 0;
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }
}

export const webSocketService = new WebSocketService();
