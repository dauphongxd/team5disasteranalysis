// api.js with caching
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Cache mechanism
const apiCache = {
    cache: new Map(),
    pendingRequests: new Map(),

    // Cache expiration in milliseconds (5 seconds)
    CACHE_EXPIRATION: 5000,

    // Get from cache
    get(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;

        // Check if cache is expired
        if (Date.now() - cached.timestamp > this.CACHE_EXPIRATION) {
            this.cache.delete(key);
            return null;
        }

        return cached.data;
    },

    // Set cache
    set(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    },

    // Get pending request
    getPendingRequest(key) {
        return this.pendingRequests.get(key);
    },

    // Set pending request
    setPendingRequest(key, promise) {
        this.pendingRequests.set(key, promise);
        promise.finally(() => {
            this.pendingRequests.delete(key);
        });
        return promise;
    }
};

// Mock data for fallback when API is unavailable
const MOCK_DATA = {
    posts: [
        {
            post_id: 'mock-1',
            original_text: 'BREAKING: Wildfire reported in California hills. Evacuations underway. Stay safe!',
            created_at: new Date().toISOString(),
            disaster_type: 'wild fire',
            confidence_score: 0.95,
            handle: 'disaster_alert',
            display_name: 'Disaster Alert',
            user_id: '12345',
            avatar_url: 'https://via.placeholder.com/150',
            location_name: 'California, USA'
        },
        {
            post_id: 'mock-2',
            original_text: 'Hurricane warning issued for coastal areas. Please secure your property and follow evacuation orders if issued.',
            created_at: new Date(Date.now() - 1200000).toISOString(),
            disaster_type: 'hurricane',
            confidence_score: 0.92,
            handle: 'storm_watch',
            display_name: 'Storm Watch',
            user_id: '54321',
            avatar_url: 'https://via.placeholder.com/150/0000FF/FFFFFF',
            location_name: 'Florida, USA'
        },
        {
            post_id: 'mock-3',
            original_text: 'Earthquake of magnitude 4.5 reported near San Francisco. No tsunami warning at this time.',
            created_at: new Date(Date.now() - 3600000).toISOString(),
            disaster_type: 'earthquake',
            confidence_score: 0.89,
            handle: 'quake_monitor',
            display_name: 'Earthquake Monitor',
            user_id: '98765',
            avatar_url: 'https://via.placeholder.com/150/FF0000/FFFFFF',
            location_name: 'San Francisco, USA'
        }
    ]
};

// Reusable fetch function with error handling, response transformation, and caching
async function fetchFromAPI(endpoint, options = {}, forceRefresh = false) {
    // Generate cache key from endpoint and options
    const cacheKey = endpoint + JSON.stringify(options);

    // If not forced refresh, check cache first
    if (!forceRefresh) {
        // Check for cached data
        const cachedData = apiCache.get(cacheKey);
        if (cachedData) {
            console.log(`Using cached data for: ${endpoint}`);
            return cachedData;
        }

        // Check for pending request
        const pendingRequest = apiCache.getPendingRequest(cacheKey);
        if (pendingRequest) {
            console.log(`Reusing pending request for: ${endpoint}`);
            return pendingRequest;
        }
    }

    // Create the fetch promise
    const fetchPromise = (async () => {
        try {
            console.log(`Fetching from: ${API_BASE_URL}${endpoint}`);
            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();

            // Special handling for posts endpoint to ensure user data is properly formatted
            if (endpoint.includes('/api/posts') && data.posts) {
                data.posts = data.posts.map(post => {
                    // Clean up the display_name if it has quotes
                    if (post.display_name && typeof post.display_name === 'string') {
                        post.display_name = post.display_name.replace(/^["'](.*)["']$/, '$1').trim();
                    }

                    // Make sure handle exists and is properly formatted
                    if (!post.handle && post.username) {
                        post.handle = post.username;
                    }

                    return post;
                });
            }

            // Cache the result
            apiCache.set(cacheKey, data);

            return data;
        } catch (error) {
            console.error(`API request failed: ${error.message}`);
            console.warn(`Using mock data fallback for: ${endpoint}`);

            // Return appropriate mock data based on the endpoint
            if (endpoint.includes('/api/posts')) {
                console.log("Returning mock posts data");
                let mockResult = { ...MOCK_DATA };

                // Filter mock data if a disaster type is specified
                const typeParam = endpoint.match(/type=([^&]+)/);
                if (typeParam && typeParam[1] && typeParam[1] !== 'all') {
                    const type = typeParam[1];
                    console.log(`Filtering mock data for disaster type: ${type}`);
                    mockResult.posts = mockResult.posts.filter(post =>
                        post.disaster_type.toLowerCase() === type.toLowerCase()
                    );
                }

                return mockResult;
            } else if (endpoint.includes('/api/disaster-types')) {
                return ['wild fire', 'hurricane', 'earthquake', 'flood', 'tornado'];
            } else if (endpoint.includes('/api/chart/disaster-distribution')) {
                return {
                    data: [
                        { type: 'wild fire', count: 35, percentage: 35.0 },
                        { type: 'hurricane', count: 25, percentage: 25.0 },
                        { type: 'earthquake', count: 20, percentage: 20.0 },
                        { type: 'flood', count: 10, percentage: 10.0 },
                        { type: 'tornado', count: 10, percentage: 10.0 }
                    ],
                    total_count: 100
                };
            } else if (endpoint.includes('/api/chart/disaster-timeline')) {
                return {
                    interval: 'daily',
                    labels: ['2023-08-01', '2023-08-02', '2023-08-03', '2023-08-04', '2023-08-05'],
                    datasets: [
                        {
                            label: 'wild fire',
                            data: [5, 8, 12, 10, 7]
                        },
                        {
                            label: 'hurricane',
                            data: [3, 5, 8, 7, 2]
                        }
                    ]
                };
            }

            // Generic fallback
            return { error: error.message };
        }
    })();

    // Register the pending request
    return apiCache.setPendingRequest(cacheKey, fetchPromise);
}

// API methods corresponding to your Flask endpoints
export const api = {
    // Posts and tweets
    getPosts: async (type = 'all', limit = 20, nextToken = null, forceRefresh = false) => {
        let url = `/api/posts?type=${type}&limit=${limit}`;

        // Ensure nextToken is properly encoded and passed
        if (nextToken) {
            try {
                // Make sure the token is a string - parse and stringify if it's not
                const tokenStr = typeof nextToken === 'string' ? nextToken : JSON.stringify(nextToken);
                url += `&next_token=${encodeURIComponent(tokenStr)}`;
            } catch (error) {
                console.error("Error encoding next_token:", error);
                // Continue without the token if there's an error
            }
        }

        console.log(`API request: ${url}, forceRefresh: ${forceRefresh}`);
        return fetchFromAPI(url, {}, forceRefresh);
    },

    // Disaster data
    getDisasterSummary: async (forceRefresh = false) => {
        return fetchFromAPI('/api/disaster-summary', {}, forceRefresh);
    },

    getDisasterTypes: async (forceRefresh = false) => {
        return fetchFromAPI('/api/disaster-types', {}, forceRefresh);
    },

    // Chart data
    getDisasterDistribution: async (forceRefresh = false) => {
        // Original endpoint - returns all-time data
        return fetchFromAPI('/api/chart/disaster-distribution', {}, forceRefresh);
    },

    // New method specifically for the donut chart to get 6-month data
    getDisasterDistributionMonths: async (months = 6, forceRefresh = false) => {
        let url = `/api/chart/disaster-distribution-months?months=${months}`;
        return fetchFromAPI(url, {}, forceRefresh);
    },

    getDisasterTimeline: async (interval = 'daily', days = 30, type = null, forceRefresh = false) => {
        let url = `/api/chart/disaster-timeline?interval=${interval}&days=${days}`;
        if (type && type !== 'all') url += `&type=${type}`;
        return fetchFromAPI(url, {}, forceRefresh);
    },

    getPostVolumeMetrics: async (forceRefresh = false) => {
        return fetchFromAPI('/api/chart/post-volume-metrics', {}, forceRefresh);
    },

    // Method to clear cache
    clearCache: () => {
        apiCache.cache.clear();
        console.log("API cache cleared");
    }
};

export default api;