# 🚀 Smart Demand Signals
### Inibsa · Interhack BCN 2026 

![Hero Image - Project Banner](docs/images/hero_banner.png)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)

**Smart Demand Signals** is an advanced business intelligence and predictive analytics solution designed for **Inibsa**. It transforms five years of transactional data from 7,000 dental clinics into real-time, actionable alerts. By differentiating between high-frequency recurring purchases and technical pattern shifts, the system empowers sales teams to anticipate needs, capture missing demand, and mitigate churn risk.

---

## 🌟 Key Features

### 🧠 Dual-Track Prioritization Engine
The core analytical brain treats different product dynamics with surgical precision:

![Engine Logic Visualization](docs/images/engine_logic.png)

*   **Commodities (Recurring)**: Uses **Inter-Purchase Time (IPT)** analysis and **85th percentile peak tracking** to detect exactly when a client is overdue. Includes automated seasonality adjustments (e.g., August downturns).
*   **Technical Products (Variable)**: Focuses on **volume-drop detection** (>50% shifts) and pattern deterioration, identifying abandonment risks before they happen.

### 📊 Multi-Dimensional Scoring Framework
Alerts are not just flags; they are prioritized using a weighted model:

![Scoring Model Weighting](docs/images/scoring_model.png)

*   **Value (LTV)**: Prioritizes high-impact clients based on historical spend.
*   **Urgency**: Logarithmic scaling of overdue days to highlight critical windows.
*   **Recoverability**: A "cliff" penalty system that recognizes when a client is likely already lost.
*   **Potential Bonus**: Cross-references internal data with external potential to target "promiscuous" clients.
*   **Confidence**: Reliability score based on the length and consistency of the client's history.

### 🔌 Real-Time API & Persistence
*   **FastAPI Backend**: High-performance asynchronous API for fetching alerts.
*   **MongoDB Integration**: Persistent storage for alert statuses and historical snapshots.
*   **Auto-Sync**: Smart logic that triggers an engine recalculation if the data is stale (>20 mins).
*   **Status Management**: Track work-in-progress, completed, and discarded alerts.

![API Documentation Preview](docs/images/api_docs.png)

### 🔍 Transparent Interpretability
Every alert includes an `Interpretability_JSON` payload, allowing frontends to visualize:
*   Historical purchase timelines.
*   Dynamic "Soft Trigger" vs. "Hard Overdue" thresholds.
*   The exact formula components that led to the final score.

---

## 🏗️ Technical Architecture

```mermaid
graph TD
    subgraph Data Layer
        CSV[(Raw CSV/XLSX)]
        DB[(MongoDB)]
    end

    subgraph Analytical Engine
        PE[Prioritization Engine]
        DL[Data Loader]
        PE --> DL
        DL --> CSV
    end

    subgraph Presentation & API
        API[FastAPI Server]
        API --> DB
        API --> PE
    end

    subgraph Output
        UI[Retention Dashboard]
        API --> UI
    end
```

---

## 🛠️ Tech Stack

*   **Language**: Python 3.11+
*   **Web Framework**: FastAPI / Uvicorn
*   **Database**: MongoDB
*   **Analysis**: Pandas, NumPy, Scipy
*   **Visualization**: Matplotlib, Seaborn
*   **Ops**: Docker, Pydantic

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.11 or higher.
*   MongoDB running locally (port 27017).

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-repo/interhackBCN.git
cd interhackBCN

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Solution
To start the API and trigger the first data load:
```bash
python src/api.py
```
The server will be available at `http://localhost:8000`. You can explore the interactive documentation at `/docs`.

### 4. Docker Deployment
```bash
docker build -t demand-signals .
docker run -p 8000:8000 -e MONGO_URI="mongodb://host.docker.internal:27017/" demand-signals
```

---

## 🧪 Simulation & Testing
The project includes a suite of retroactive testing tools to validate the engine's performance on historical data:

![Visual Analytics Demo](docs/images/analytics_demo.png)

*   `src/retroactive_sim.py`: Runs a day-by-day simulation over a past period.
*   `src/large_scale_test.py`: Performance benchmarking.
*   `src/visualize_alerts.py`: Generates high-fidelity dark-themed plots for alert verification.

---

## 📂 Project Structure

*   `src/`: Main source code.
    *   `prioritization_engine.py`: Core logic for alert generation.
    *   `api.py`: FastAPI implementation.
    *   `data_loader.py`: Data ingestion and cleaning.
    *   `visualize_alerts.py`: Matplotlib visualization suite.
*   `data/`: Input datasets.
*   `docs/`: Detailed API and technical documentation.
*   `plots/`: Generated visual reports.
*   `outputs/`: Daily alert exports and CSV logs.

---

## 📄 License
This project was developed for the **Interhack BCN 2026** Hackathon. All rights reserved by Inibsa and the development team.