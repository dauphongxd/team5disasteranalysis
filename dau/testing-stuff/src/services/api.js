// services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Reusable fetch function with error handling
async function fetchFromAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API request failed: ${error.message}`);
        throw error;
    }
}

// API methods corresponding to your Flask endpoints
export const api = {
    // Posts and tweets
    getPosts: async (type = 'all', limit = 50, nextToken = null) => {
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
        if (type) url += `&type=${type}`;
        return fetchFromAPI(url);
    },

    getPostVolumeMetrics: async () => {
        return fetchFromAPI('/api/chart/post-volume-metrics');
    }
};

export default api;