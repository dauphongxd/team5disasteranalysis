import { io } from 'socket.io-client';

// Singleton pattern to ensure only one socket instance
let socketInstance = null;
let connectionPromise = null;

class WebSocketService {
    constructor() {
        // Don't create a new instance if one already exists
        if (socketInstance) {
            return socketInstance;
        }

        this.socket = null;
        this.isConnected = false;
        this.listeners = new Map();
        socketInstance = this;
    }

    connect(url) {
        // Only attempt to connect if we're not already connecting or connected
        if (connectionPromise) {
            return connectionPromise;
        }

        if (this.isConnected && this.socket) {
            console.log('WebSocket already connected');
            return Promise.resolve();
        }

        console.log('Connecting to Socket.IO server:', url);

        connectionPromise = new Promise((resolve, reject) => {
            try {
                // Close existing socket if any
                if (this.socket) {
                    this.socket.disconnect();
                }

                // Create Socket.IO client
                this.socket = io(url, {
                    transports: ['websocket'],
                    reconnection: true,
                    reconnectionAttempts: 5,
                    reconnectionDelay: 1000,
                    // Add connection timeout
                    timeout: 10000
                });

                // Handle connection events
                this.socket.on('connect', () => {
                    console.log('Socket.IO connected!');
                    this.isConnected = true;
                    resolve();
                });

                this.socket.on('disconnect', () => {
                    console.log('Socket.IO disconnected');
                    this.isConnected = false;
                    connectionPromise = null;
                });

                this.socket.on('connect_error', (error) => {
                    console.error('Socket.IO connection error:', error);
                    this.isConnected = false;
                    connectionPromise = null;
                    reject(error);
                });

                // Listen for new post events
                this.socket.on('new_post', (data) => {
                    console.log('Received new post from server:', data);
                    this.handleMessage(data);
                });

            } catch (error) {
                console.error('Error creating Socket.IO connection:', error);
                this.isConnected = false;
                connectionPromise = null;
                reject(error);
            }
        });

        return connectionPromise;
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        connectionPromise = null;
        console.log('Socket.IO disconnected by client');
    }

    handleMessage(data) {
        // Notify all listeners registered for 'new_post' event
        if (this.listeners.has('new_post')) {
            this.listeners.get('new_post').forEach(callback => callback(data.post));
        }
    }

    // Subscribe to specific disaster type - only if connected
    subscribeToDisasterType(disasterType) {
        if (!this.isConnected || !this.socket) {
            console.warn('Cannot subscribe: Socket.IO not connected');
            return;
        }

        // Send subscription message
        this.socket.emit('subscribe', { disasterType: disasterType || 'all' });
        console.log("Subscribed to disaster type:", disasterType || 'all');
    }

    // Add event listener
    addEventListener(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);

        return () => {
            // Return function to remove this specific listener
            if (this.listeners.has(event)) {
                this.listeners.get(event).delete(callback);
            }
        };
    }

    // Remove event listener
    removeEventListener(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

    // Check connection status
    isSocketConnected() {
        return this.isConnected && this.socket !== null;
    }
}

// Create and export a singleton instance
const websocketService = new WebSocketService();
export default websocketService;