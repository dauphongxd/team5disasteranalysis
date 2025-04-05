import { io } from 'socket.io-client';

const URL = process.env.REACT_APP_WEBSOCKET_URL || 'http://localhost:5000';
let socket;

export const connectWebSocket = () => {
    console.log('Attempting to connect WebSocket to:', URL);
    // Disconnect previous socket if exists
    if (socket) {
        socket.disconnect();
    }
    // Connect to the explicit URL
    socket = io(URL, {
        // Optional: Add transports for robustness if needed
        // transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('WebSocket connected:', socket.id);
        // You might want to call a callback here to update connection status in UI
    });

    socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        // Update UI status
    });

    socket.on('connect_error', (err) => {
        console.error('WebSocket connection error:', err);
        // Update UI status
    });
};


class WebSocketService {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.listeners = new Map();
    }

    connect(url) {
        return new Promise((resolve, reject) => {
            try {
                // Close existing socket if any
                if (this.socket) {
                    this.socket.disconnect();
                }

                console.log('Connecting to Socket.IO server:', url);

                // Create Socket.IO client
                this.socket = io(url, {
                    transports: ['websocket'],
                    reconnection: true,
                    reconnectionAttempts: 5,
                    reconnectionDelay: 1000
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
                });

                this.socket.on('connect_error', (error) => {
                    console.error('Socket.IO connection error:', error);
                    reject(error);
                });

                // Listen for new post events
                this.socket.on('new_post', (data) => {
                    console.log('Received new post from server:', data);
                    this.handleMessage(data);
                });

            } catch (error) {
                console.error('Error creating Socket.IO connection:', error);
                reject(error);
            }
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        console.log('Socket.IO disconnected by client');
    }

    handleMessage(data) {
        // Notify all listeners registered for 'new_post' event
        if (this.listeners.has('new_post')) {
            this.listeners.get('new_post').forEach(callback => callback(data.post));
        }
    }

    // Subscribe to specific disaster type
    subscribeToDisasterType(disasterType) {
        if (!this.isConnected) {
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
}

export const onNewPost = (callback) => {
    socket?.on('new_post', callback);
};

export const subscribeToDisaster = (disasterType) => {
    console.log(`Emitting subscribe for: ${disasterType}`);
    socket?.emit('subscribe', { disasterType });
}

// Create and export a singleton instance
const websocketService = new WebSocketService();
export default websocketService;