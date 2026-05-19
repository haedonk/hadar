# Hadar Dashboard UI

React single-page application for the Hadar anomaly monitoring dashboard. Built with Vite and served via nginx in production.

## Features

- Real-time anomaly event feed with severity indicators (critical / warning / low)
- Device list with current anomaly status
- Temperature device detail views
- Light theme designed for at-a-glance home monitoring

## Development

```bash
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` and expects the API at `http://localhost:8000` (configurable via `VITE_API_URL`).

## Production Build

```bash
npm run build
```

The output in `dist/` is served by the nginx container defined in `Dockerfile`.
