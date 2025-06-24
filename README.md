# Movie & TV Show Discovery Platform

This project is a web application designed to help users discover movies and TV shows they might like. Users can vote on pairs of content items, and the application provides personalized recommendations based on their voting history and interactions. The platform uses the OMDB API to fetch detailed information about movies and TV series.

## Project Overview

The application consists of two main parts:

-   **Backend**: A Python-based FastAPI application that handles business logic, user authentication, database interactions (MongoDB), and communication with the OMDB API. It also includes a recommendation engine to generate personalized suggestions.
-   **Frontend**: A React-based single-page application (SPA) that provides the user interface for browsing content, voting, viewing recommendations, and managing user profiles.

## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

-   Node.js and npm (or Yarn) for the frontend.
-   Python 3.11 for the backend.
-   MongoDB instance (local or cloud-hosted).
-   An OMDB API Key (get one from [omdbapi.com](http://www.omdbapi.com/apikey.aspx)).

### Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\\Scripts\\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Ensure a `.env` file exists in the `backend` directory.
    If `backend/.env` is already present in your repository checkout, review its contents and update them with your specific configurations, especially the `OMDB_API_KEY` and `JWT_SECRET_KEY`.
    If you need to create it, here are the variables it should contain:
    ```env
    MONGO_URL="mongodb://localhost:27017"
    DB_NAME="movie_preferences_db"
    OMDB_API_KEY="YOUR_OMDB_API_KEY" # Replace with your actual key
    JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production" # Replace with a strong, unique secret
    JWT_ALGORITHM="HS256"
    JWT_EXPIRATION_HOURS=72
    ```
    **Important**: Replace placeholder values for `OMDB_API_KEY` and `JWT_SECRET_KEY` with your actual credentials and a secure secret.

5.  **Run the backend server:**
    The backend uses Uvicorn to run. From the `backend` directory:
    ```bash
    uvicorn server:app --reload --port 8000
    ```
    The backend API will be accessible at `http://localhost:8000`.

### Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    Using npm:
    ```bash
    npm install
    ```
    Or using Yarn:
    ```bash
    yarn install
    ```

3.  **Set up environment variables:**
    Ensure a `.env` file exists in the `frontend` directory.
    If `frontend/.env` is present from your repository checkout, review its contents.
    If you need to create it, add the following environment variable, pointing to your running backend API:
    ```env
    REACT_APP_BACKEND_URL=http://localhost:8000
    ```
    *Note: If your backend is running on a different port, update this URL accordingly.*

4.  **Run the frontend development server:**
    Using npm:
    ```bash
    npm start
    ```
    Or using Yarn:
    ```bash
    yarn start
    ```
    The frontend application will typically open automatically in your browser at `http://localhost:3000`.

## Project Structure

-   `backend/`: Contains the FastAPI application.
    -   `server.py`: The main application file with API endpoints.
    -   `recommendation_engine.py`: Houses the logic for generating content recommendations.
    -   `requirements.txt`: Python dependencies.
    -   `.env`: Environment variables for the backend. (Ensure this contains your local configuration)
-   `frontend/`: Contains the React application (bootstrapped with Create React App).
    -   `src/`: Main source code for the React components and application logic.
        -   `App.js`: The main application component.
        -   `index.js`: The entry point for the React application.
    -   `public/`: Static assets.
    -   `package.json`: Frontend dependencies and scripts.
    -   `.env`: Environment variables for the frontend. (Ensure this contains your local configuration)
-   `README.md`: This file.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the terms of the MIT license.
