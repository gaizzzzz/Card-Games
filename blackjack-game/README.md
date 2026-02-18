# Blackjack Game

This project is a simple implementation of a Blackjack game with a FastAPI backend and a Node.js frontend.

## Project Structure

```
blackjack-game
├── backend
│   ├── app
│   │   ├── main.py          # Entry point for the FastAPI application
│   │   ├── api
│   │   │   └── routes.py    # API routes for the application
│   │   ├── models
│   │   │   └── game.py      # Data models related to the game
│   │   └── utils
│   │       └── blackjack.py  # Game logic for Blackjack
│   ├── requirements.txt      # Python dependencies for the backend
│   └── README.md             # Documentation for the backend
├── frontend
│   ├── src
│   │   ├── App.js            # Main component of the frontend application
│   │   ├── components
│   │   │   └── BlackjackTable.js # Component for rendering the Blackjack table
│   │   └── utils
│   │       └── api.js        # Utility functions for API calls
│   ├── package.json          # Configuration file for npm
│   └── README.md             # Documentation for the frontend
└── README.md                 # Overall documentation for the project
```

## Getting Started

### Backend

1. Navigate to the `backend` directory.
2. Install the required Python packages using:
   ```
   pip install -r requirements.txt
   ```
3. Run the FastAPI application:
   ```
   uvicorn app.main:app --reload
   ```

### Frontend

1. Navigate to the `frontend` directory.
2. Install the required Node.js packages using:
   ```
   npm install
   ```
3. Start the frontend application:
   ```
   npm start
   ```

## Deployment (Docker)

1. Put card images in `blackjack-game/assets/` (same files as your current `assets` folder).
2. Create environment file:
   ```
   copy .env.example .env
   ```
3. Update `.env` for your public domains:
   - `VITE_API_BASE=https://<your-backend-domain>`
   - `ALLOWED_ORIGINS=https://<your-frontend-domain>`
4. Build and run:
   ```
   docker compose up --build -d
   ```

Published services:
- Frontend: `http://<server-ip>:3000`
- Backend API: `http://<server-ip>:8000`

## Usage

- Access the backend API at `http://localhost:8000`.
- Access the frontend application at `http://localhost:3000`.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.
