# Disaster Watch: Real-Time Disaster Monitoring

Disaster Watch aggregates and displays real-time natural disaster information from social media (Bluesky) and official sources (NWS). It features an interactive map, live post feed, and data visualizations.

## Table of Contents

1.  [Features](#features)
2.  [Tech Stack](#tech-stack)
3.  [Project Architecture](#project-architecture)
4.  [Directory Structure](#directory-structure)
5.  [Setup and Installation](#setup-and-installation)
6.  [Running the Application](#running-the-application)
7.  [Environment Variables](#environment-variables)
8.  [Core Functionality](#core-functionality)
9.  [Key API Endpoints](#key-api-endpoints)
10. [Notes](#notes)

## 1. Features

*   **Interactive Map:** Displays NWS alerts, simulated wildfires, and hurricanes with clustering and a dynamic legend. Includes an NWS Data Viewer.
*   **Live Tweet Feed:** Shows filtered, real-time disaster-related posts with infinite scrolling, updated via WebSockets.
*   **Data Filters:** Allows filtering by disaster categories (Fire, Storm, Earthquake, etc.).
*   **Data Visualization:** Donut chart for 6-month disaster distribution and a time-series chart for trends.
*   **3D Animated Background:** Starfield effect using Three.js.
*   **Emergency Resources:** Links to safety tips and hotlines.

## 2. Tech Stack

*   **Frontend:** React, Chart.js, Leaflet.js, Three.js, Socket.IO Client
*   **Backend:** Python, Flask, Flask-SocketIO, Boto3 (DynamoDB), Transformers (AI Model), ATProto (Bluesky SDK)
*   **Database:** AWS DynamoDB
*   **AI Model:** RoBERTa-based for disaster classification.

## 3. Project Architecture

1.  **Data Ingestion (`main.py`):**
    *   Fetches posts from Bluesky using disaster keywords.
    *   Cleans text and classifies disaster type using an AI model.
    *   Stores data in DynamoDB.
    *   Notifies the API server of new posts.
2.  **API Server (`api.py`):**
    *   Flask-based REST API serving data to the frontend.
    *   Socket.IO for real-time client updates.
    *   Implements response caching.
3.  **Frontend Application (`src/`):**
    *   React SPA displaying maps, feeds, and charts.
    *   Communicates with the backend API and WebSocket server.

## 4. Directory Structure
*(Frontend `.env` file should be at the same level as `package.json`)*
*(Backend `.env` file should be at the same folder called `backend`)*

## 5. Setup and Installation

### Prerequisites
*   Node.js & npm/yarn
*   Python & pip
*   AWS Account & CLI configured (for DynamoDB)
*   Bluesky App Password

### Backend (`main.py` & `api.py`)
1.  **Clone repository.**
2.  **Create & activate Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # Windows: venv\Scripts\activate
    ```
3.  **Install Python dependencies:**
    Create `requirements.txt` (see detailed README or infer from imports) and run:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up Backend `.env` file** (see [Environment Variables](#environment-variables)).
5.  **AI Model:** Ensure `MODEL_PATH` in `.env` points to your AI model directory (e.g., `checkpoint-1800`).

### Frontend (`src/`)
1.  **Install Node.js dependencies:** (In the directory with `package.json`)
    ```bash
    npm install # or yarn install
    ```
2.  **Set up Frontend `.env` file** (see [Environment Variables](#environment-variables)).

## 6. Running the Application

1.  **Backend - Data Ingestion (`main.py`):**
    (Activate venv)
    ```bash
    python main.py
    ```
2.  **Backend - API Server (`api.py`):**
    (Activate venv, new terminal)
    ```bash
    python api.py
    ```
    (Usually runs on `http://localhost:8000`)
3.  **Frontend:**
    (In frontend project root)
    ```bash
    npm start # or yarn start
    ```
    (Usually opens at `http://localhost:3000`)

## 7. Environment Variables

**Backend (`.env` in project root):**
*   `AWS_REGION`: Your AWS region
*   `AWS_ACCESS_KEY_ID`: Your AWS Access Key
*   `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Key
*   `API_HANDLE`: Bluesky username
*   `API_PW`: Bluesky App Password
*   `MODEL_PATH`: Path to AI model (e.g., `checkpoint-1800`)
*   `API_BASE_URL`: URL of `api.py` (e.g., `http://localhost:8000`)

**Frontend (`.env` in frontend root):**
*   `REACT_APP_API_URL`: Backend API URL (e.g., `http://localhost:8000`)
*   `REACT_APP_WEBSOCKET_URL`: WebSocket server URL (e.g., `http://localhost:8000`)

## 8. Core Functionality

*   **`main.py` (Data Ingestion):**
    *   Continuously fetches Bluesky posts using keywords.
    *   Classifies posts with an AI model for disaster type and confidence.
    *   Stores relevant data in DynamoDB (`DisasterFeed_Posts`, `DisasterFeed_Users`).
    *   Manages Bluesky API rate limits and session.
    *   Sends batched notifications of new posts to `api.py`.
*   **`api.py` (API Server):**
    *   Serves data from DynamoDB via REST endpoints.
    *   Handles WebSocket connections, allowing clients to subscribe to disaster types.
    *   Broadcasts new posts (received from `main.py`) to subscribed clients.
    *   Uses caching for GET requests.
*   **`MapSection.js` (Frontend):**
    *   Displays NWS alerts and simulated disaster data on a Leaflet map.
    *   Features layer toggles, a dynamic legend, and an NWS data inspector.
*   **`TweetFeed.js` (Frontend):**
    *   Displays a filterable, real-time feed of disaster posts.
    *   Supports infinite scroll and WebSocket updates.
*   **Charts (`Donutchart.js`, `Timechart.js`):**
    *   Visualize disaster distribution and trends.

## 9. Key API Endpoints

*   `GET /api/posts`: Fetches posts (filterable by `type`, `limit`, `next_token`).
*   `GET /api/disaster-summary`: Aggregated disaster statistics.
*   `GET /api/disaster-types`: List of unique disaster types.
*   `GET /api/chart/disaster-distribution-months`: Data for donut chart (last N `months`).
*   `GET /api/chart/disaster-timeline`: Time-series data (filterable by `interval`, `days`, `type`).
*   `POST /api/notify-new-post`: (Internal) For `main.py` to send new posts for WebSocket broadcast.

## 10. Notes

*   **Tsunami Data:** This category is explicitly filtered out in most frontend components.
*   **Rate Limiting & Caching:** Both backend and frontend implement mechanisms to manage API load and improve performance.
*   **Database Schema:** `DisasterFeed_Posts` uses `post_id` and `indexed_at` as primary keys and has GSIs for `disaster_type` and `is_disaster_str` for efficient querying.
*   **Mock Data:** The `api.js` service includes mock data as a fallback if the backend API is unavailable.
