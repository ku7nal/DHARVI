# DepthWizard

DepthWizard turns aerial RGB imagery into an interactive estimated nDSM visualization.

## Local development

### Backend

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in a browser. The frontend reports whether the FastAPI health endpoint is reachable. Model inference and prediction fixtures will be added in the next ticket.
