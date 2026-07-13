# 🩺 Deployment Health Dashboard

A lightweight Streamlit dashboard to monitor the health of your deployed applications.

The dashboard concurrently checks all configured deployments, displays their health status, response latency, and HTTP status codes, making it easy to see which services are running and which ones need attention.

---

## Features

- 🟢 Concurrent health checks for all configured URLs
- 📊 Dashboard summarizing healthy/unhealthy deployments
- ⏱️ Response latency measurement
- 🔍 HTTP status reporting (200, 404, 500, timeout, etc.)
- 🔄 Manual refresh
- ⚡ Automatic refresh every 5 minutes
- 📝 Add, edit and remove monitored deployments from the sidebar
- 🌐 One-click access to every deployment
- 🖼️ Optional embedded previews (where supported by the target application)

---

## Screenshot

> *(Add a screenshot here)*

---

## Installation

Clone the repository and install the dependencies.

```bash
git clone <repo-url>
cd DeploymentHealthDashboard

pip install -r requirements.txt
```

---

## Usage

Create a `projects.json` file containing the deployments you want to monitor.

Example:

```json
{
    "OpenBalancer": "https://openbalancer.up.railway.app",
    "Portfolio": "https://dev-on-the-web.streamlit.app",
    "RAG4ALL": "https://rag4all.streamlit.app"
}
```

Run the dashboard:

```bash
streamlit run app.py
```

---

## How it Works

Each refresh:

1. Sends HTTP requests to every configured deployment concurrently.
2. Measures response latency.
3. Reports the returned HTTP status code.
4. Marks deployments as:

- 🟢 Healthy (`200 OK`)
- 🔴 Unhealthy (`4xx` / `5xx`)
- 🟡 Timeout / No Response

---

## Roadmap

- [ ] GitHub Actions keep-alive workflow
- [ ] Uptime history
- [ ] Response time graphs
- [ ] Health endpoint support (`/health`)
- [ ] Export / Import project configuration

---

## License

MIT License
