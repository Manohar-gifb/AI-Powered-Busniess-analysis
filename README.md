# AI-Powered Business Intelligence Dashboard

> A complete, professional web application for business data analysis, machine learning, and AI-powered insights.

## 🚀 Features

| Module | Description |
|--------|-------------|
| **Data Import** | Upload CSV and Excel files with automatic validation and processing |
| **Interactive Dashboard** | Real-time KPI cards, filters, and 6 interactive Plotly.js charts |
| **Descriptive Analytics** | Sales growth, profit margins, region/product/customer analysis |
| **Predictive Analytics** | Linear Regression and Random Forest for revenue prediction |
| **Anomaly Detection** | Isolation Forest algorithm to detect unusual business transactions |
| **Revenue Forecasting** | ARIMA and Holt-Winters time-series forecasting |
| **AI Recommendations** | Rule-based engine generating actionable business insights |
| **Reporting & Export** | Generate reports in CSV, Excel, and printable HTML formats |

## 📋 Prerequisites

- **Python 3.8+** — [Download](https://python.org)
- **No external database** — uses SQLite (built-in)
- **No internet required** — runs completely offline on localhost

## ⚡ Quick Start

### Windows (Recommended)
```
1. Extract the ZIP file
2. Double-click run.bat
3. Open browser to http://127.0.0.1:5000
4. Login: admin / admin123
```

### All Platforms (Manual)
```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
#    Windows:
venv\Scripts\activate
#    Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the application
python app.py

# 5. Open browser to http://127.0.0.1:5000
```

## 🔑 Default Login

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |
| Email | admin@bidashboard.com |

You can also register a new account from the login page.

## 📊 Sample Data

On first run, the application automatically creates:

| Data | Count |
|------|-------|
| Sales Records | 1,500 |
| Products | 31 |
| Customers | 80 |
| Regions | 5 |
| Categories | 6 |

This data spans January 2024 – December 2025 with realistic business patterns including seasonal trends, anomalies, and growth trajectories.

## 🏗️ Project Structure

```
AI_Business_Intelligence/
│
├── app.py                    # Main Flask application (routes & logic)
├── database.py               # Database setup and table definitions
├── models.py                 # Data models and query methods
├── data_processor.py         # CSV/Excel import processing
├── ml_models.py              # Machine learning (Linear Regression, Random Forest)
├── anomaly_detection.py      # Anomaly detection (Isolation Forest)
├── forecasting.py            # Time-series forecasting (ARIMA, Holt-Winters)
├── recommendations.py        # AI recommendation engine
├── reporting.py              # Report generation and export
├── seed_data.py              # Sample data generation
│
├── requirements.txt          # Python dependencies
├── run.bat                   # Windows launcher
├── README.md                 # This file
├── HOW_TO_USE.txt            # Step-by-step user guide
│
├── data/
│   ├── database/             # SQLite database files
│   ├── datasets/             # Reference/test datasets
│   └── uploads/              # User-uploaded files
│
├── models/                   # Saved ML models (.joblib files)
│
├── static/
│   ├── css/                    # Application stylesheets
│   │   ├── style.css           # Base application styles
│   │   ├── dashboard.css       # Dashboard page styles
│   │   ├── analytics.css       # Analytics page styles
│   │   ├── anomalies.css       # Anomaly detection styles
│   │   ├── forecast.css        # Forecast page styles
│   │   ├── recommendations.css # Recommendations styles
│   │   ├── reports.css         # Reports page styles
│   │   ├── landing.css         # Landing page styles
│   │   ├── sidebar.css         # Sidebar navigation styles
│   │   └── states.css          # Loading/error/empty state styles
│   ├── js/                   # JavaScript modules
│   │   ├── main.js
│   │   ├── dashboard.js
│   │   ├── analytics.js
│   │   ├── prediction.js
│   │   ├── anomalies.js
│   │   └── forecast.js
│   ├── icons/                # Application icons
│   └── images/               # Static images
│
└── templates/                # HTML templates
    ├── base.html             # Base layout with navigation
    ├── landing.html          # Home page
    ├── login.html            # Login page
    ├── register.html         # Registration page
    ├── dashboard.html        # Main BI dashboard
    ├── analytics.html        # Advanced analytics
    ├── prediction.html       # ML prediction
    ├── anomalies.html        # Anomaly detection
    ├── forecast.html         # Revenue forecasting
    ├── recommendations.html  # AI recommendations
    ├── reports.html          # Reporting & export
    ├── data_import.html      # Data import wizard
    ├── upload.html           # File upload
    ├── datasets.html         # Dataset list
    └── dataset_detail.html   # Dataset details
```

## 🔧 Technology Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3, Flask |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap Icons |
| Charts | Plotly.js (interactive) |
| Database | SQLite (no setup required) |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn (Random Forest, Linear Regression, Isolation Forest) |
| Time Series | Statsmodels (ARIMA, Holt-Winters) |
| Export | openpyxl (Excel), CSV, HTML |

## 📦 Dependencies

See `requirements.txt`:
- Flask
- Pandas
- NumPy
- scikit-learn
- statsmodels
- openpyxl
- Werkzeug

## 🛡️ Important Notes

- **No MySQL/PostgreSQL/MongoDB/Node.js/React required**
- **No cloud services or paid APIs**
- **No internet connection required** for core functionality
- All paths are relative — the project works when copied to any Windows/Mac/Linux computer
- Passwords are securely hashed — never stored in plain text
- Sample data is generated automatically on first run

## 📝 License

This project is for educational purposes — Final Year Academic Project.
