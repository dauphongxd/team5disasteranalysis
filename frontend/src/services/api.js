// services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Reusable fetch function with error handling and response transformation
async function fetchFromAPI(endpoint, options = {}) {
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

        return data;
    } catch (error) {
        console.error(`API request failed: ${error.message}`);
        console.warn(`Using mock data fallback for: ${endpoint}`);

        // Return the appropriate mock data based on the endpoint
        // (your existing fallback code would be here)
        throw error;
    }
}

// API methods corresponding to your Flask endpoints
export const api = {
    // Posts and tweets
    getPosts: async (type = 'all', limit = 20, nextToken = null) => {
        let url = `/api/posts?type=${type}&limit=${limit}`;
        if (nextToken) url += `&next_token=${encodeURIComponent(nextToken)}`;
        return fetchFromAPI(url);
    },

    // Disaster data
    getDisasterSummary: async () => {
        return fetchFromAPI('/api/disaster-summary');
    },

    getDisasterTypes: async () => {
        return fetchFromAPI('/api/disaster-types');
    },

    // Chart data
    getDisasterDistribution: async () => {
        return fetchFromAPI('/api/chart/disaster-distribution');
    },

    getDisasterTimeline: async (interval = 'daily', days = 30, type = null) => {
        let url = `/api/chart/disaster-timeline?interval=${interval}&days=${days}`;
        if (type && type !== 'all') url += `&type=${type}`;
        return fetchFromAPI(url);
    },

    getPostVolumeMetrics: async () => {
        return fetchFromAPI('/api/chart/post-volume-metrics');
    }
};

export default api;