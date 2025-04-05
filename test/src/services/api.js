const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

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