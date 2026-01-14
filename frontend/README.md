# VibeVoice Web UI

A modern React + TypeScript web interface for the VibeVoice text-to-speech API.

## Features

- **Speech Generation**: Convert text to speech with customizable speakers and settings
- **Voice Management**: Create, list, and delete custom voices from audio files
- **Settings**: Configure API endpoint, API key, and default preferences

## Prerequisites

- Node.js 18+ and npm
- VibeVoice API server running (see main project README)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

Edit `.env` and set `VITE_API_URL` to your API server URL (default: `http://localhost:8000`)

## Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://server-ai.mrhelpmann.com:3001`.

The dev server includes a proxy to the API server, so API requests will be forwarded to `http://localhost:8000` automatically.

## Build

Build for production:
```bash
npm run build
```

The built files will be in the `dist/` directory.

## Production Deployment

### Option 1: Serve as Static Files

The built `dist/` folder can be served by any static file server:
- Copy `dist/` contents to your web server
- Configure your server to serve the files

### Option 2: Serve from FastAPI

You can serve the frontend from the FastAPI backend by adding static file serving:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

### Option 3: Deploy Separately

Deploy to services like:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

Make sure to configure the `VITE_API_URL` environment variable in your deployment platform.

## Configuration

Settings are stored in browser localStorage and can be configured through the Settings page in the UI:

- **API Endpoint**: URL of the VibeVoice API server
- **API Key**: Optional API key for authentication
- **Default Settings**: Default language, output format, and sample rate

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/          # Page components
│   ├── services/       # API client and storage
│   ├── hooks/          # Custom React hooks
│   ├── types/          # TypeScript types
│   ├── utils/          # Utility functions
│   ├── App.tsx         # Main app with routing
│   └── main.tsx        # Entry point
├── public/             # Static assets
├── index.html          # HTML template
└── package.json        # Dependencies
```

## Technologies

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **React Router**: Client-side routing
- **Tailwind CSS**: Utility-first styling
- **Axios**: HTTP client

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)