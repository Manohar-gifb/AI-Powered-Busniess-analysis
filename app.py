"""
app.py - Main Flask Application
================================
Entry point for the AI-Powered Business Intelligence Dashboard.
Handles routing, authentication, and serves as the application core.
"""

import os
import json
import secrets
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import init_db, get_db
from models import User, Dataset, DataRow, Sale, Region, Category, Customer, Product
from data_processor import process_upload, store_imported_data, ProcessingResult

# ---- App Configuration ----
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ---- Authentication Decorator ----
def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---- Context Processors ----
@app.context_processor
def inject_user():
    """Make current user available in all templates."""
    user = None
    if 'user_id' in session:
        user = User.find_by_id(session['user_id'])
    return dict(current_user=user)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route('/health')
def health_check():
    """Health/status endpoint to verify the application is running."""
    return jsonify({
        'status': 'healthy',
        'application': 'AI Business Intelligence Dashboard',
        'version': '1.0.0',
        'database': 'SQLite',
        'server': 'localhost:5000'
    })


# ============================================================
# PUBLIC ROUTES
# ============================================================

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in, else show landing."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')

        user = User.find_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            User.update_last_login(user['id'])
            flash(f'Welcome back, {user["full_name"] or user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and handler."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if not password or len(password) < 4:
            errors.append('Password must be at least 4 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if User.find_by_username(username):
            errors.append('Username already taken.')
        if User.find_by_email(email):
            errors.append('Email already registered.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        # Create user
        password_hash = generate_password_hash(password)
        User.create(username, email, password_hash, full_name)

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Clear session and redirect to home."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/contact')
def contact():
    """Contact page."""
    return render_template('contact.html')


# ============================================================
# DASHBOARD ROUTES
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page."""
    user_id = session['user_id']
    datasets = Dataset.get_user_datasets(user_id)
    filter_options = Sale.get_filter_options()
    return render_template('dashboard.html', datasets=datasets, filter_options=filter_options)


@app.route('/api/dashboard-data')
@login_required
def api_dashboard_data():
    """API endpoint returning all dashboard data with optional filters."""
    # Parse filters from query params
    filters = {}
    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('region'):
        filters['region'] = request.args.get('region')
    if request.args.get('category'):
        filters['category'] = request.args.get('category')
    if request.args.get('product_id'):
        filters['product_id'] = request.args.get('product_id')

    # Get all dashboard data
    kpis = Sale.get_filtered_kpis(filters)
    monthly = Sale.get_filtered_monthly(filters)
    by_region = Sale.get_filtered_by_region(filters)
    by_category = Sale.get_filtered_by_category(filters)
    top_products = Sale.get_filtered_top_products(filters)
    by_segment = Sale.get_filtered_by_segment(filters)

    # Calculate sales growth (current month vs previous month)
    if len(monthly) >= 2:
        current = monthly[-1]['total_revenue']
        previous = monthly[-2]['total_revenue']
        growth = ((current - previous) / previous * 100) if previous > 0 else 0
    elif len(monthly) == 1:
        growth = 0
    else:
        growth = 0

    return jsonify({
        'kpis': {
            'total_revenue': kpis.get('total_revenue', 0),
            'total_profit': kpis.get('total_profit', 0),
            'total_orders': kpis.get('total_orders', 0),
            'total_customers': kpis.get('total_customers', 0),
            'avg_order_value': kpis.get('avg_order_value', 0),
            'profit_margin': kpis.get('profit_margin', 0),
            'sales_growth': growth
        },
        'monthly': monthly,
        'by_region': by_region,
        'by_category': by_category,
        'top_products': top_products,
        'by_segment': by_segment
    })


@app.route('/datasets')
@login_required
def datasets_list():
    """List all uploaded datasets."""
    user_id = session['user_id']
    datasets = Dataset.get_user_datasets(user_id)
    return render_template('datasets.html', datasets=datasets)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Upload a CSV or Excel file."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        # Validate file type
        allowed_extensions = {'.csv', '.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash('Only CSV and Excel files are allowed.', 'danger')
            return redirect(request.url)

        try:
            # Save the file
            safe_filename = f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            file.save(filepath)

            # Read the file to get basic info using pandas
            import pandas as pd
            if file_ext == '.csv':
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)

            # Register dataset in database
            dataset_id = Dataset.create(
                user_id=session['user_id'],
                filename=safe_filename,
                original_filename=file.filename,
                file_size=os.path.getsize(filepath),
                row_count=len(df),
                column_count=len(df.columns),
                column_names=json.dumps(list(df.columns)),
                description=request.form.get('description', '')
            )

            # Store data rows
            df = df.fillna('')  # Replace NaN with empty string for JSON serialization
            rows = df.to_dict(orient='records')
            DataRow.bulk_insert(dataset_id, rows)

            # Update dataset stats
            Dataset.update_stats(dataset_id, len(df), len(df.columns), json.dumps(list(df.columns)))

            flash(f'Dataset "{file.filename}" uploaded successfully! ({len(df)} rows, {len(df.columns)} columns)', 'success')
            return redirect(url_for('dataset_detail', dataset_id=dataset_id))

        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('upload.html')


@app.route('/dataset/<int:dataset_id>')
@login_required
def dataset_detail(dataset_id):
    """View details of a specific dataset."""
    dataset = Dataset.find_by_id(dataset_id)
    if not dataset or dataset['user_id'] != session['user_id']:
        flash('Dataset not found.', 'danger')
        return redirect(url_for('datasets_list'))

    # Get preview data (first 20 rows)
    rows = DataRow.get_by_dataset(dataset_id, limit=20)
    preview_data = [json.loads(row['row_data']) for row in rows]
    columns = json.loads(dataset['column_names']) if dataset['column_names'] else []

    return render_template('dataset_detail.html', dataset=dataset,
                          preview_data=preview_data, columns=columns)


@app.route('/dataset/<int:dataset_id>/delete', methods=['POST'])
@login_required
def delete_dataset(dataset_id):
    """Delete a dataset and all its associated data."""
    dataset = Dataset.find_by_id(dataset_id)
    if not dataset or dataset['user_id'] != session['user_id']:
        flash('Dataset not found.', 'danger')
        return redirect(url_for('datasets_list'))

    # Delete data rows first, then dataset
    DataRow.delete_by_dataset(dataset_id)
    Dataset.delete(dataset_id)
    flash('Dataset deleted successfully.', 'success')
    return redirect(url_for('datasets_list'))# ============================================================
# DATA IMPORT (Phase 3)
# ============================================================

# Temp directory for staging processed data between preview and confirm
IMPORT_STAGING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'uploads', '_staging')
os.makedirs(IMPORT_STAGING_DIR, exist_ok=True)


def _cleanup_staging(user_id):
    """Remove any leftover staging files for a user."""
    import glob as _glob
    pattern = os.path.join(IMPORT_STAGING_DIR, f'{user_id}_*')
    for f in _glob.glob(pattern):
        try:
            os.remove(f)
        except OSError:
            pass


@app.route('/data-import', methods=['GET', 'POST'])
@login_required
def data_import():
    """
    Professional data import page.
    Step 1 (GET): Show upload form.
    Step 2 (POST, action=preview): Upload file, process, show preview.
    Step 3 (POST, action=confirm): Actually import the processed data.
    """
    if request.method == 'POST':
        action = request.form.get('action', 'preview')
        user_id = session['user_id']

        # ---- STEP 2: Preview mode ----
        if action == 'preview':
            if 'file' not in request.files:
                flash('No file selected.', 'danger')
                return redirect(url_for('data_import'))

            file = request.files['file']
            if file.filename == '':
                flash('No file selected.', 'danger')
                return redirect(url_for('data_import'))

            # Validate file extension
            allowed = {'.csv', '.xlsx', '.xls'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed:
                flash('Only CSV, XLSX, and XLS files are allowed.', 'danger')
                return redirect(url_for('data_import'))

            try:
                # Save file securely
                safe_name = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{file_ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
                file.save(filepath)

                # Validate file size
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    flash('The uploaded file is empty.', 'danger')
                    os.remove(filepath)
                    return redirect(url_for('data_import'))

                # Get optional required columns
                required_cols_raw = request.form.get('required_columns', '').strip()
                required_cols = [c.strip() for c in required_cols_raw.split(',') if c.strip()] or None

                # Get processing options
                remove_dupes = request.form.get('remove_duplicates', 'on') == 'on'
                handle_missing = request.form.get('handle_missing', 'on') == 'on'

                # Process the file
                result = process_upload(
                    filepath,
                    required_columns=required_cols,
                    remove_dupes=remove_dupes,
                    handle_missing=handle_missing
                )

                if not result.success:
                    for err in result.errors:
                        flash(err, 'danger')
                    return redirect(url_for('data_import'))

                # Store intermediate data as temp file (avoids session size limit)
                _cleanup_staging(user_id)
                staging_file = os.path.join(IMPORT_STAGING_DIR, f'{user_id}_staged.csv')
                if result.clean_dataframe is not None:
                    result.clean_dataframe.to_csv(staging_file, index=False)

                # Store only small metadata in session
                session['import_filepath'] = filepath
                session['import_original_name'] = file.filename
                session['import_staging_file'] = staging_file
                session['import_result'] = result.to_dict()

                return render_template('data_import.html',
                                       step='preview',
                                       result=result.to_dict(),
                                       filename=file.filename)

            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'danger')
                return redirect(url_for('data_import'))

        # ---- STEP 3: Confirm import ----
        elif action == 'confirm':
            filepath = session.get('import_filepath')
            original_name = session.get('import_original_name', 'unknown')
            staging_file = session.get('import_staging_file')
            result_dict = session.get('import_result')

            if not filepath or not staging_file or not result_dict:
                flash('Import session expired. Please upload again.', 'danger')
                return redirect(url_for('data_import'))

            try:
                import pandas as pd

                # Read cleaned data from staging file
                if not os.path.exists(staging_file):
                    flash('Staging file not found. Please upload again.', 'danger')
                    return redirect(url_for('data_import'))

                df = pd.read_csv(staging_file)

                if df.empty:
                    flash('No data to import.', 'danger')
                    return redirect(url_for('data_import'))

                # Create dataset record
                dataset_id = Dataset.create(
                    user_id=user_id,
                    filename=os.path.basename(filepath),
                    original_filename=original_name,
                    file_size=os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                    row_count=len(df),
                    column_count=len(df.columns),
                    column_names=json.dumps(list(df.columns)),
                    description=f'Imported via Data Import on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                )

                # Store the data
                imported_count = store_imported_data(dataset_id, df)

                # Update dataset stats
                Dataset.update_stats(dataset_id, len(df), len(df.columns), json.dumps(list(df.columns)))

                # Clean up session data and staging file
                _cleanup_staging(user_id)
                session.pop('import_filepath', None)
                session.pop('import_original_name', None)
                session.pop('import_staging_file', None)
                session.pop('import_result', None)

                flash(
                    f'Import successful! {imported_count} records imported from "{original_name}". '
                    f'({len(df.columns)} columns)',
                    'success'
                )
                return redirect(url_for('dataset_detail', dataset_id=dataset_id))

            except Exception as e:
                flash(f'Error during import: {str(e)}', 'danger')
                return redirect(url_for('data_import'))

        # ---- Cancel import ----
        elif action == 'cancel':
            # Clean up saved files
            filepath = session.pop('import_filepath', None)
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            _cleanup_staging(user_id)
            session.pop('import_original_name', None)
            session.pop('import_staging_file', None)
            session.pop('import_result', None)
            flash('Import cancelled.', 'info')
            return redirect(url_for('data_import'))

    # GET: Show import form
    return render_template('data_import.html', step='upload')


# ============================================================
# REPORTING (Phase 11)
# ============================================================

@app.route('/reports')
@login_required
def reports():
    """Reports page."""
    filter_options = Sale.get_filter_options()
    return render_template('reports.html', filter_options=filter_options)


@app.route('/api/reports-data')
@login_required
def api_reports_data():
    """Get report data with optional filters."""
    from reporting import get_report_data
    filters = {}
    if request.args.get('start_date'): filters['start_date'] = request.args['start_date']
    if request.args.get('end_date'): filters['end_date'] = request.args['end_date']
    if request.args.get('region'): filters['region'] = request.args['region']
    if request.args.get('category'): filters['category'] = request.args['category']
    data = get_report_data(filters or None)
    return jsonify(data)


@app.route('/api/reports-export')
@login_required
def api_reports_export():
    """Export report as CSV, Excel, or HTML."""
    from reporting import get_report_data, export_csv, export_excel, export_html_report
    fmt = request.args.get('format', 'csv')
    filters = {}
    if request.args.get('start_date'): filters['start_date'] = request.args['start_date']
    if request.args.get('end_date'): filters['end_date'] = request.args['end_date']
    if request.args.get('region'): filters['region'] = request.args['region']
    if request.args.get('category'): filters['category'] = request.args['category']
    data = get_report_data(filters or None)

    if fmt == 'excel':
        excel_data = export_excel(data)
        return excel_data, 200, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=business_report.xlsx'
        }
    elif fmt == 'html':
        html_data = export_html_report(data)
        return html_data, 200, {
            'Content-Type': 'text/html; charset=utf-8',
            'Content-Disposition': 'attachment; filename=business_report.html'
        }
    else:  # CSV
        csv_data = export_csv(data)
        return csv_data, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename=business_report.csv'
        }


# ============================================================
# RECOMMENDATIONS (Phase 10)
# ============================================================

@app.route('/recommendations')
@login_required
def recommendations():
    """Business Recommendations page."""
    return render_template('recommendations.html')


@app.route('/api/recommendations-data')
@login_required
def api_recommendations_data():
    """Get AI business recommendations."""
    from recommendations import get_recommendation_summary
    result = get_recommendation_summary()
    return jsonify(result)


# ============================================================
# FORECASTING (Phase 9)
# ============================================================

@app.route('/forecast')
@login_required
def forecast():
    """Forecasting page."""
    return render_template('forecast.html')


@app.route('/api/forecast-data')
@login_required
def api_forecast_data():
    """Generate forecast based on parameters."""
    from forecasting import generate_forecast
    metric = request.args.get('metric', 'revenue')
    periods = int(request.args.get('periods', 6))
    model_type = request.args.get('model', 'auto')

    periods = max(1, min(24, periods))  # Clamp to 1-24

    result = generate_forecast(metric=metric, periods=periods, model_type=model_type)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


# ============================================================
# ANOMALY DETECTION (Phase 8)
# ============================================================

@app.route('/anomalies')
@login_required
def anomalies():
    """Anomaly Detection page."""
    return render_template('anomalies.html')


@app.route('/api/anomalies-detect', methods=['POST'])
@login_required
def api_anomalies_detect():
    """Run anomaly detection and return results."""
    from anomaly_detection import detect_anomalies
    data = request.get_json() or {}
    contamination = data.get('contamination', 0.05)
    result = detect_anomalies(contamination=contamination)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/anomalies-data')
@login_required
def api_anomalies_data():
    """Get cached anomaly results with optional filters."""
    from anomaly_detection import detect_anomalies, filter_anomalies
    result = detect_anomalies()
    if 'error' in result:
        return jsonify(result), 400
    # Apply filters
    filters = {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'region': request.args.get('region'),
        'category': request.args.get('category'),
    }
    filters = {k: v for k, v in filters.items() if v}
    if filters:
        result['anomalies'] = filter_anomalies(result['anomalies'], filters)
        result['stats']['anomaly_count'] = len(result['anomalies'])
    return jsonify(result)


# ============================================================
# PREDICTION (Phase 7)
# ============================================================

@app.route('/prediction')
@login_required
def prediction():
    """Machine Learning Prediction page."""
    return render_template('prediction.html')


@app.route('/api/prediction-train', methods=['POST'])
@login_required
def api_prediction_train():
    """Train ML models and return results."""
    from ml_models import train_all
    result = train_all()
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/prediction-predict', methods=['POST'])
@login_required
def api_prediction_predict():
    """Make a prediction with a trained model."""
    from ml_models import predict_revenue
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    model_name = data.get('model', 'random_forest')
    features = data.get('features', {})

    prediction = predict_revenue(model_name, features)
    if prediction is None:
        return jsonify({'error': 'Model not found. Please train first.'}), 404

    return jsonify({'prediction': prediction})


# ============================================================
# ANALYTICS (Phase 6)
# ============================================================

@app.route('/analytics')
@login_required
def analytics():
    """Advanced Analytics page."""
    return render_template('analytics.html')


@app.route('/api/analytics-data')
@login_required
def api_analytics_data():
    """API endpoint returning all analytics data."""
    return jsonify({
        'yearly': Sale.get_yearly_comparison(),
        'monthly_growth': Sale.get_month_over_month(),
        'product_performance': Sale.get_product_performance(),
        'region_performance': Sale.get_region_performance(),
        'category_performance': Sale.get_category_performance(),
        'customer_performance': Sale.get_customer_performance()[:20],
        'contribution': Sale.get_revenue_contribution(),
        'ai_insights': Sale.get_ai_insights(),
    })


# ============================================================
# STATIC FILE SERVING
# ============================================================

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# ============================================================
# APPLICATION STARTUP
# ============================================================

if __name__ == '__main__':
    # Step 1: Initialize database tables
    init_db()

    # Step 2: Seed sample data on first run
    from seed_data import seed_all
    seed_all()

    # Step 3: Print summary of business data
    print(f"\n  Sample data loaded:")
    print(f"    Sales records: {Sale.get_count()}")
    print(f"    Products:      {Product.get_count()}")
    print(f"    Customers:     {Customer.get_count()}")
    print(f"    Regions:       {len(Region.get_all())}")
    print(f"    Categories:    {len(Category.get_all())}")

    print("\n" + "="*60)
    print("  AI-Powered Business Intelligence Dashboard")
    print("  Starting server on http://127.0.0.1:5000")
    print("="*60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)
