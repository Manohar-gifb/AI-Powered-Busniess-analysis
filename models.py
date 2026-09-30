"""
models.py - Data Models and Helper Classes
===========================================
Provides model classes that wrap database operations.
Keeps business logic separate from route handlers.

Phase 1: User, Dataset, DataRow, MLModel, Forecast, Anomaly, Recommendation
Phase 2: Region, Category, Customer, Product, Sale
"""

import json
from datetime import datetime
from database import execute_query, execute_many


# ============================================================
# PHASE 1 MODELS (authentication, uploads, ML)
# ============================================================

class User:
    """User model for authentication and user management."""

    @staticmethod
    def create(username, email, password_hash, full_name='', role='user'):
        """Create a new user."""
        query = '''
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        '''
        return execute_query(query, (username, email, password_hash, full_name, role), fetch=False)

    @staticmethod
    def find_by_username(username):
        """Find a user by username."""
        query = "SELECT * FROM users WHERE username = ?"
        results = execute_query(query, (username,))
        return results[0] if results else None

    @staticmethod
    def find_by_id(user_id):
        """Find a user by ID."""
        query = "SELECT * FROM users WHERE id = ?"
        results = execute_query(query, (user_id,))
        return results[0] if results else None

    @staticmethod
    def update_last_login(user_id):
        """Update the last login timestamp."""
        query = "UPDATE users SET last_login = ? WHERE id = ?"
        execute_query(query, (datetime.now().isoformat(), user_id), fetch=False)

    @staticmethod
    def find_by_email(email):
        """Find a user by email."""
        query = "SELECT * FROM users WHERE email = ?"
        results = execute_query(query, (email,))
        return results[0] if results else None


class Dataset:
    """Dataset model for managing uploaded business data."""

    @staticmethod
    def create(user_id, filename, original_filename, file_size=0,
               row_count=0, column_count=0, column_names='', description=''):
        """Register a new dataset."""
        query = '''
            INSERT INTO datasets (user_id, filename, original_filename, file_size,
                                  row_count, column_count, column_names, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return execute_query(query, (user_id, filename, original_filename, file_size,
                                     row_count, column_count, column_names, description), fetch=False)

    @staticmethod
    def find_by_id(dataset_id):
        """Find a dataset by ID."""
        query = "SELECT * FROM datasets WHERE id = ?"
        results = execute_query(query, (dataset_id,))
        return results[0] if results else None

    @staticmethod
    def get_user_datasets(user_id):
        """Get all datasets for a specific user."""
        query = "SELECT * FROM datasets WHERE user_id = ? ORDER BY upload_date DESC"
        return execute_query(query, (user_id,))

    @staticmethod
    def update_status(dataset_id, status):
        """Update dataset status."""
        query = "UPDATE datasets SET status = ? WHERE id = ?"
        execute_query(query, (status, dataset_id), fetch=False)

    @staticmethod
    def update_stats(dataset_id, row_count, column_count, column_names):
        """Update dataset statistics after processing."""
        query = '''
            UPDATE datasets SET row_count = ?, column_count = ?, column_names = ?, status = 'processed'
            WHERE id = ?
        '''
        execute_query(query, (row_count, column_count, column_names, dataset_id), fetch=False)

    @staticmethod
    def delete(dataset_id):
        """Delete a dataset."""
        query = "DELETE FROM datasets WHERE id = ?"
        execute_query(query, (dataset_id,), fetch=False)

    @staticmethod
    def get_all():
        """Get all datasets."""
        query = "SELECT * FROM datasets ORDER BY upload_date DESC"
        return execute_query(query)


class DataRow:
    """Model for storing individual data rows from uploaded files."""

    @staticmethod
    def bulk_insert(dataset_id, rows):
        """Insert multiple data rows at once."""
        query = "INSERT INTO data_rows (dataset_id, row_index, row_data) VALUES (?, ?, ?)"
        conn = None
        try:
            from database import get_db
            conn = get_db()
            cursor = conn.cursor()
            data = [(dataset_id, idx, json.dumps(row)) for idx, row in enumerate(rows)]
            cursor.executemany(query, data)
            conn.commit()
            return len(data)
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_by_dataset(dataset_id, limit=None):
        """Get all rows for a dataset."""
        query = "SELECT * FROM data_rows WHERE dataset_id = ? ORDER BY row_index"
        if limit:
            query += f" LIMIT {limit}"
        return execute_query(query, (dataset_id,))

    @staticmethod
    def get_as_dicts(dataset_id):
        """Get all rows as a list of dictionaries (parsed JSON)."""
        rows = DataRow.get_by_dataset(dataset_id)
        return [json.loads(row['row_data']) for row in rows]

    @staticmethod
    def delete_by_dataset(dataset_id):
        """Delete all rows for a dataset."""
        query = "DELETE FROM data_rows WHERE dataset_id = ?"
        execute_query(query, (dataset_id,), fetch=False)


class MLModel:
    """Model for tracking trained machine learning models."""

    @staticmethod
    def create(user_id, dataset_id, model_name, model_type, target_column,
               feature_columns='', accuracy=0.0, model_file='', parameters=''):
        """Register a trained model."""
        query = '''
            INSERT INTO ml_models (user_id, dataset_id, model_name, model_type,
                                   target_column, feature_columns, accuracy, model_file, parameters)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return execute_query(query, (user_id, dataset_id, model_name, model_type,
                                     target_column, feature_columns, accuracy,
                                     model_file, parameters), fetch=False)

    @staticmethod
    def find_by_id(model_id):
        """Find a model by ID."""
        query = "SELECT * FROM ml_models WHERE id = ?"
        results = execute_query(query, (model_id,))
        return results[0] if results else None

    @staticmethod
    def get_user_models(user_id):
        """Get all models for a user."""
        query = "SELECT * FROM ml_models WHERE user_id = ? ORDER BY trained_date DESC"
        return execute_query(query, (user_id,))

    @staticmethod
    def get_dataset_models(dataset_id):
        """Get all models for a dataset."""
        query = "SELECT * FROM ml_models WHERE dataset_id = ? ORDER BY trained_date DESC"
        return execute_query(query, (dataset_id,))


class Forecast:
    """Model for storing forecast results."""

    @staticmethod
    def create(user_id, dataset_id, forecast_type, target_column,
               forecast_values, forecast_dates='', confidence_lower='',
               confidence_upper='', metrics=''):
        """Store a forecast result."""
        query = '''
            INSERT INTO forecasts (user_id, dataset_id, forecast_type, target_column,
                                   forecast_values, forecast_dates, confidence_lower,
                                   confidence_upper, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return execute_query(query, (user_id, dataset_id, forecast_type, target_column,
                                     forecast_values, forecast_dates, confidence_lower,
                                     confidence_upper, metrics), fetch=False)

    @staticmethod
    def get_user_forecasts(user_id):
        """Get all forecasts for a user."""
        query = "SELECT * FROM forecasts WHERE user_id = ? ORDER BY created_date DESC"
        return execute_query(query, (user_id,))


class Anomaly:
    """Model for storing anomaly detection results."""

    @staticmethod
    def create(user_id, dataset_id, column_name, anomaly_count, total_rows,
               anomaly_indices='', threshold=0.0, method='iqr'):
        """Store anomaly detection results."""
        query = '''
            INSERT INTO anomalies (user_id, dataset_id, column_name, anomaly_count,
                                   total_rows, anomaly_indices, threshold, method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return execute_query(query, (user_id, dataset_id, column_name, anomaly_count,
                                     total_rows, anomaly_indices, threshold, method), fetch=False)

    @staticmethod
    def get_user_anomalies(user_id):
        """Get all anomaly results for a user."""
        query = "SELECT * FROM anomalies WHERE user_id = ? ORDER BY created_date DESC"
        return execute_query(query, (user_id,))


class Recommendation:
    """Model for storing AI-generated recommendations."""

    @staticmethod
    def create(user_id, dataset_id, category, title, description,
               priority='medium', impact=''):
        """Store a recommendation."""
        query = '''
            INSERT INTO recommendations (user_id, dataset_id, category, title,
                                         description, priority, impact)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        return execute_query(query, (user_id, dataset_id, category, title,
                                     description, priority, impact), fetch=False)

    @staticmethod
    def get_user_recommendations(user_id):
        """Get all recommendations for a user."""
        query = "SELECT * FROM recommendations WHERE user_id = ? ORDER BY created_date DESC"
        return execute_query(query, (user_id,))

    @staticmethod
    def get_dataset_recommendations(dataset_id):
        """Get all recommendations for a dataset."""
        query = "SELECT * FROM recommendations WHERE dataset_id = ? ORDER BY created_date DESC"
        return execute_query(query, (dataset_id,))


# ============================================================
# PHASE 2 MODELS (business data)
# ============================================================

class Region:
    """Region lookup model."""

    @staticmethod
    def get_all():
        """Get all regions."""
        return execute_query("SELECT * FROM regions ORDER BY id")

    @staticmethod
    def find_by_id(region_id):
        """Find a region by ID."""
        results = execute_query("SELECT * FROM regions WHERE id = ?", (region_id,))
        return results[0] if results else None

    @staticmethod
    def find_by_name(region_name):
        """Find a region by name."""
        results = execute_query("SELECT * FROM regions WHERE region_name = ?", (region_name,))
        return results[0] if results else None


class Category:
    """Product category lookup model."""

    @staticmethod
    def get_all():
        """Get all categories."""
        return execute_query("SELECT * FROM categories ORDER BY id")

    @staticmethod
    def find_by_id(cat_id):
        """Find a category by ID."""
        results = execute_query("SELECT * FROM categories WHERE id = ?", (cat_id,))
        return results[0] if results else None

    @staticmethod
    def find_by_name(cat_name):
        """Find a category by name."""
        results = execute_query("SELECT * FROM categories WHERE category_name = ?", (cat_name,))
        return results[0] if results else None


class Customer:
    """Customer model."""

    @staticmethod
    def get_all():
        """Get all customers."""
        return execute_query("SELECT * FROM customers ORDER BY id")

    @staticmethod
    def find_by_id(customer_id):
        """Find a customer by ID."""
        results = execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
        return results[0] if results else None

    @staticmethod
    def get_count():
        """Get total number of customers."""
        results = execute_query("SELECT COUNT(*) as cnt FROM customers")
        return results[0]['cnt'] if results else 0

    @staticmethod
    def get_by_segment():
        """Get customer count grouped by segment."""
        return execute_query(
            "SELECT segment, COUNT(*) as count FROM customers GROUP BY segment ORDER BY count DESC"
        )


class Product:
    """Product model."""

    @staticmethod
    def get_all():
        """Get all products with category name."""
        return execute_query('''
            SELECT p.*, c.category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.id
        ''')

    @staticmethod
    def find_by_id(product_id):
        """Find a product by ID."""
        results = execute_query("SELECT * FROM products WHERE id = ?", (product_id,))
        return results[0] if results else None

    @staticmethod
    def get_count():
        """Get total number of products."""
        results = execute_query("SELECT COUNT(*) as cnt FROM products")
        return results[0]['cnt'] if results else 0

    @staticmethod
    def get_by_category():
        """Get product count grouped by category."""
        return execute_query('''
            SELECT c.category_name, COUNT(p.id) as count
            FROM products p
            JOIN categories c ON p.category_id = c.id
            GROUP BY c.category_name
            ORDER BY count DESC
        ''')


class Sale:
    """Sales data model - main business data for analytics."""

    @staticmethod
    def get_all(limit=None, offset=0):
        """Get all sales records with optional pagination."""
        query = "SELECT * FROM sales ORDER BY sale_date DESC"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        return execute_query(query)

    @staticmethod
    def get_count():
        """Get total number of sales records."""
        results = execute_query("SELECT COUNT(*) as cnt FROM sales")
        return results[0]['cnt'] if results else 0

    # ---- KPI Queries ----

    @staticmethod
    def get_total_revenue():
        """Get total revenue across all sales."""
        results = execute_query("SELECT COALESCE(SUM(revenue), 0) as total FROM sales")
        return results[0]['total'] if results else 0

    @staticmethod
    def get_total_profit():
        """Get total profit across all sales."""
        results = execute_query("SELECT COALESCE(SUM(profit), 0) as total FROM sales")
        return results[0]['total'] if results else 0

    @staticmethod
    def get_total_quantity():
        """Get total units sold."""
        results = execute_query("SELECT COALESCE(SUM(quantity), 0) as total FROM sales")
        return results[0]['total'] if results else 0

    @staticmethod
    def get_avg_order_value():
        """Get average order value (revenue per sale)."""
        results = execute_query("SELECT COALESCE(AVG(revenue), 0) as avg_val FROM sales")
        return results[0]['avg_val'] if results else 0

    @staticmethod
    def get_profit_margin():
        """Get overall profit margin percentage."""
        results = execute_query(
            "SELECT CASE WHEN SUM(revenue) > 0 THEN (SUM(profit) / SUM(revenue)) * 100 ELSE 0 END as margin FROM sales"
        )
        return results[0]['margin'] if results else 0

    # ---- Aggregation Queries (for charts) ----

    @staticmethod
    def get_revenue_by_region():
        """Get revenue grouped by region."""
        return execute_query('''
            SELECT region, SUM(revenue) as total_revenue, SUM(profit) as total_profit, COUNT(*) as sale_count
            FROM sales GROUP BY region ORDER BY total_revenue DESC
        ''')

    @staticmethod
    def get_revenue_by_category():
        """Get revenue grouped by category."""
        return execute_query('''
            SELECT category, SUM(revenue) as total_revenue, SUM(profit) as total_profit, COUNT(*) as sale_count
            FROM sales GROUP BY category ORDER BY total_revenue DESC
        ''')

    @staticmethod
    def get_monthly_revenue():
        """Get monthly revenue aggregation (for time-series charts)."""
        return execute_query('''
            SELECT strftime('%Y-%m', sale_date) as month,
                   SUM(revenue) as total_revenue,
                   SUM(profit) as total_profit,
                   SUM(quantity) as total_quantity,
                   COUNT(*) as sale_count
            FROM sales
            GROUP BY strftime('%Y-%m', sale_date)
            ORDER BY month ASC
        ''')

    @staticmethod
    def get_top_products(limit=10):
        """Get top N products by revenue."""
        return execute_query('''
            SELECT p.product_name, SUM(s.revenue) as total_revenue,
                   SUM(s.quantity) as total_sold, SUM(s.profit) as total_profit
            FROM sales s
            JOIN products p ON s.product_id = p.id
            GROUP BY s.product_id
            ORDER BY total_revenue DESC
            LIMIT ?
        ''', (limit,))

    @staticmethod
    def get_top_customers(limit=10):
        """Get top N customers by revenue."""
        return execute_query('''
            SELECT c.customer_name, c.segment, SUM(s.revenue) as total_revenue,
                   COUNT(*) as order_count
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
            GROUP BY s.customer_id
            ORDER BY total_revenue DESC
            LIMIT ?
        ''', (limit,))

    @staticmethod
    def get_daily_revenue(start_date=None, end_date=None):
        """Get daily revenue for charting."""
        query = "SELECT sale_date, SUM(revenue) as daily_revenue FROM sales"
        params = []
        conditions = []
        if start_date:
            conditions.append("sale_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("sale_date <= ?")
            params.append(end_date)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY sale_date ORDER BY sale_date ASC"
        return execute_query(query, tuple(params) if params else None)

    @staticmethod
    def get_sales_by_customer_segment():
        """Get sales grouped by customer segment."""
        return execute_query('''
            SELECT c.segment, SUM(s.revenue) as total_revenue,
                   COUNT(*) as sale_count, AVG(s.revenue) as avg_sale
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
            GROUP BY c.segment
            ORDER BY total_revenue DESC
        ''')

    # ---- Statistics for Analytics ----

    @staticmethod
    def get_numeric_stats(column):
        """Get basic statistics for a numeric column (revenue, profit, quantity, unit_price)."""
        allowed = {'revenue', 'profit', 'quantity', 'unit_price', 'cost'}
        if column not in allowed:
            return None
        results = execute_query(f'''
            SELECT
                MIN({column}) as min_val,
                MAX({column}) as max_val,
                AVG({column}) as mean_val,
                SUM({column}) as sum_val,
                COUNT({column}) as count_val
            FROM sales
        ''')
        return results[0] if results else None

    @staticmethod
    def get_date_range():
        """Get the date range of sales data."""
        results = execute_query(
            "SELECT MIN(sale_date) as start_date, MAX(sale_date) as end_date FROM sales"
        )
        return results[0] if results else None

    @staticmethod
    def get_sale_count_by_region():
        """Get count of sales by region."""
        return execute_query('''
            SELECT region, COUNT(*) as count FROM sales GROUP BY region ORDER BY count DESC
        ''')

    @staticmethod
    def get_sale_count_by_category():
        """Get count of sales by category."""
        return execute_query('''
            SELECT category, COUNT(*) as count FROM sales GROUP BY category ORDER BY count DESC
        ''')

    # ---- Filtered Queries (for dashboard filtering) ----

    @staticmethod
    def _build_where(filters):
        """Build WHERE clause from filter dict. Returns (where_str, params)."""
        conditions = []
        params = []
        if filters:
            if filters.get('start_date'):
                conditions.append('sale_date >= ?')
                params.append(filters['start_date'])
            if filters.get('end_date'):
                conditions.append('sale_date <= ?')
                params.append(filters['end_date'])
            if filters.get('region'):
                conditions.append('region = ?')
                params.append(filters['region'])
            if filters.get('category'):
                conditions.append('category = ?')
                params.append(filters['category'])
            if filters.get('product_id'):
                conditions.append('product_id = ?')
                params.append(int(filters['product_id']))
        where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
        return where, tuple(params)

    @staticmethod
    def get_filtered_kpis(filters=None):
        """Get KPI values with optional filters."""
        where, params = Sale._build_where(filters)
        results = execute_query(f'''SELECT
            COUNT(*) as total_orders,
            COUNT(DISTINCT customer_id) as total_customers,
            COALESCE(SUM(revenue), 0) as total_revenue,
            COALESCE(SUM(profit), 0) as total_profit,
            COALESCE(AVG(revenue), 0) as avg_order_value,
            CASE WHEN SUM(revenue) > 0 THEN (SUM(profit) / SUM(revenue)) * 100 ELSE 0 END as profit_margin
        FROM sales{where}''', params if params else None)
        return results[0] if results else {}

    @staticmethod
    def get_filtered_monthly(filters=None):
        """Get monthly aggregates with optional filters."""
        where, params = Sale._build_where(filters)
        return execute_query(f"""SELECT
            strftime('%Y-%m', sale_date) as month,
            SUM(revenue) as total_revenue,
            SUM(profit) as total_profit,
            COUNT(*) as sale_count
        FROM sales{where}
        GROUP BY strftime('%Y-%m', sale_date)
        ORDER BY month ASC""", params if params else None)

    @staticmethod
    def get_filtered_by_region(filters=None):
        """Get revenue by region with optional filters."""
        where, params = Sale._build_where(filters)
        return execute_query(f"""SELECT region,
            SUM(revenue) as total_revenue,
            SUM(profit) as total_profit,
            COUNT(*) as sale_count
        FROM sales{where}
        GROUP BY region ORDER BY total_revenue DESC""", params if params else None)

    @staticmethod
    def get_filtered_by_category(filters=None):
        """Get revenue by category with optional filters."""
        where, params = Sale._build_where(filters)
        return execute_query(f"""SELECT category,
            SUM(revenue) as total_revenue,
            SUM(profit) as total_profit,
            COUNT(*) as sale_count
        FROM sales{where}
        GROUP BY category ORDER BY total_revenue DESC""", params if params else None)

    @staticmethod
    def get_filtered_top_products(filters=None, limit=10):
        """Get top products with optional filters."""
        where, params = Sale._build_where(filters)
        # Remove product_id filter for top products view
        if filters and filters.get('product_id'):
            where = where.replace(' AND product_id = ?', '').replace('product_id = ? AND ', '')
            params = tuple(p for p in params if p != int(filters['product_id']))
        return execute_query(f"""SELECT p.product_name, p.id as product_id,
            SUM(s.revenue) as total_revenue,
            SUM(s.quantity) as total_sold,
            SUM(s.profit) as total_profit
        FROM sales s JOIN products p ON s.product_id = p.id
        {where}
        GROUP BY s.product_id ORDER BY total_revenue DESC LIMIT ?""",
        tuple(list(params) + [limit]) if params else (limit,))

    @staticmethod
    def get_filtered_by_segment(filters=None):
        """Get revenue by customer segment with optional filters."""
        where, params = Sale._build_where(filters)
        return execute_query(f"""SELECT c.segment,
            SUM(s.revenue) as total_revenue,
            COUNT(*) as sale_count
        FROM sales s JOIN customers c ON s.customer_id = c.id
        {where}
        GROUP BY c.segment ORDER BY total_revenue DESC""", params if params else None)

    @staticmethod
    def get_filter_options():
        """Get unique values for filter dropdowns."""
        return {
            'regions': [r['region'] for r in execute_query('SELECT DISTINCT region FROM sales ORDER BY region')],
            'categories': [c['category'] for c in execute_query('SELECT DISTINCT category FROM sales ORDER BY category')],
            'date_range': dict(execute_query('SELECT MIN(sale_date) as min_date, MAX(sale_date) as max_date FROM sales')[0])
        }

    # ================================================================
    # ANALYTICS QUERIES (Phase 6)
    # ================================================================

    @staticmethod
    def get_yearly_comparison():
        """Compare revenue and profit by year."""
        return execute_query('''
            SELECT strftime('%Y', sale_date) as year,
                   SUM(revenue) as total_revenue,
                   SUM(profit) as total_profit,
                   COUNT(*) as total_orders,
                   AVG(revenue) as avg_order
            FROM sales
            GROUP BY strftime('%Y', sale_date)
            ORDER BY year ASC
        ''')

    @staticmethod
    def get_month_over_month():
        """Month-over-month revenue growth rate."""
        rows = execute_query('''
            SELECT strftime('%Y-%m', sale_date) as month,
                   SUM(revenue) as revenue
            FROM sales
            GROUP BY strftime('%Y-%m', sale_date)
            ORDER BY month ASC
        ''')
        for i in range(1, len(rows)):
            prev = rows[i-1]['revenue']
            curr = rows[i]['revenue']
            rows[i]['growth_rate'] = ((curr - prev) / prev * 100) if prev > 0 else 0
            rows[i]['prev_revenue'] = prev
        if rows:
            rows[0]['growth_rate'] = 0
            rows[0]['prev_revenue'] = 0
        return rows

    @staticmethod
    def get_product_performance():
        """Detailed product performance with margin and trend."""
        return execute_query('''
            SELECT p.product_name, p.id as product_id, p.unit_price as list_price,
                   c.category_name,
                   COUNT(s.id) as total_orders,
                   SUM(s.quantity) as total_units,
                   SUM(s.revenue) as total_revenue,
                   SUM(s.cost) as total_cost,
                   SUM(s.profit) as total_profit,
                   CASE WHEN SUM(s.revenue) > 0
                        THEN (SUM(s.profit) / SUM(s.revenue)) * 100
                        ELSE 0 END as profit_margin,
                   AVG(s.revenue) as avg_order_value
            FROM sales s
            JOIN products p ON s.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            GROUP BY s.product_id
            ORDER BY total_revenue DESC
        ''')

    @staticmethod
    def get_region_performance():
        """Detailed region performance."""
        return execute_query('''
            SELECT region,
                   COUNT(*) as total_orders,
                   COUNT(DISTINCT customer_id) as unique_customers,
                   SUM(revenue) as total_revenue,
                   SUM(profit) as total_profit,
                   AVG(revenue) as avg_order_value,
                   CASE WHEN SUM(revenue) > 0
                        THEN (SUM(profit) / SUM(revenue)) * 100
                        ELSE 0 END as profit_margin
            FROM sales
            GROUP BY region
            ORDER BY total_revenue DESC
        ''')

    @staticmethod
    def get_category_performance():
        """Detailed category performance."""
        return execute_query('''
            SELECT category,
                   COUNT(*) as total_orders,
                   SUM(quantity) as total_units,
                   SUM(revenue) as total_revenue,
                   SUM(profit) as total_profit,
                   AVG(revenue) as avg_order_value,
                   CASE WHEN SUM(revenue) > 0
                        THEN (SUM(profit) / SUM(revenue)) * 100
                        ELSE 0 END as profit_margin
            FROM sales
            GROUP BY category
            ORDER BY total_revenue DESC
        ''')

    @staticmethod
    def get_customer_performance():
        """Top customer performance."""
        return execute_query('''
            SELECT c.customer_name, c.segment, c.city,
                   COUNT(s.id) as total_orders,
                   SUM(s.revenue) as total_revenue,
                   SUM(s.profit) as total_profit,
                   AVG(s.revenue) as avg_order_value
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
            GROUP BY s.customer_id
            ORDER BY total_revenue DESC
        ''')

    @staticmethod
    def get_revenue_contribution():
        """Revenue contribution percentages by region and category."""
        total = execute_query('SELECT SUM(revenue) as t FROM sales')[0]['t'] or 1
        by_region = execute_query('''
            SELECT region as label, SUM(revenue) as revenue,
                   (SUM(revenue) / ?) * 100 as contribution_pct
            FROM sales GROUP BY region ORDER BY revenue DESC
        ''', (total,))
        by_category = execute_query('''
            SELECT category as label, SUM(revenue) as revenue,
                   (SUM(revenue) / ?) * 100 as contribution_pct
            FROM sales GROUP BY category ORDER BY revenue DESC
        ''', (total,))
        return {'by_region': by_region, 'by_category': by_category, 'total_revenue': total}

    @staticmethod
    def get_ai_insights():
        """
        Generate deterministic AI insights based on calculated database values.
        Every insight is backed by actual query results.
        """
        insights = []

        # 1. Highest performing region
        top_region = execute_query('''
            SELECT region, SUM(revenue) as rev, 
                   (SUM(revenue) / (SELECT SUM(revenue) FROM sales)) * 100 as pct
            FROM sales GROUP BY region ORDER BY rev DESC LIMIT 1
        ''')
        if top_region:
            r = top_region[0]
            insights.append({
                'type': 'success', 'icon': 'bi-trophy',
                'title': f'Highest Performing Region',
                'description': f'{r["region"]} leads with ${r["rev"]:,.0f} revenue ({r["pct"]:.1f}% of total).',
                'metric': f'${r["rev"]:,.0f}'
            })

        # 2. Lowest performing category
        low_cat = execute_query('''
            SELECT category, SUM(revenue) as rev,
                   CASE WHEN SUM(revenue) > 0 THEN (SUM(profit)/SUM(revenue))*100 ELSE 0 END as margin
            FROM sales GROUP BY category ORDER BY rev ASC LIMIT 1
        ''')
        if low_cat:
            c = low_cat[0]
            insights.append({
                'type': 'warning', 'icon': 'bi-exclamation-triangle',
                'title': f'Lowest Revenue Category',
                'description': f'{c["category"]} generates only ${c["rev"]:,.0f} with {c["margin"]:.1f}% margin.',
                'metric': f'${c["rev"]:,.0f}'
            })

        # 3. Highest profit product
        high_profit = execute_query('''
            SELECT p.product_name, SUM(s.profit) as profit,
                   CASE WHEN SUM(s.revenue) > 0 THEN (SUM(s.profit)/SUM(s.revenue))*100 ELSE 0 END as margin
            FROM sales s JOIN products p ON s.product_id = p.id
            GROUP BY s.product_id ORDER BY profit DESC LIMIT 1
        ''')
        if high_profit:
            p = high_profit[0]
            insights.append({
                'type': 'success', 'icon': 'bi-star',
                'title': 'Most Profitable Product',
                'description': f'{p["product_name"]} generates ${p["profit"]:,.0f} profit ({p["margin"]:.1f}% margin).',
                'metric': f'${p["profit"]:,.0f}'
            })

        # 4. Fastest growing month
        monthly = execute_query('''
            SELECT strftime('%Y-%m', sale_date) as month, SUM(revenue) as rev
            FROM sales GROUP BY month ORDER BY month ASC
        ''')
        if len(monthly) >= 2:
            best_growth = None
            best_pct = 0
            for i in range(1, len(monthly)):
                prev = monthly[i-1]['rev']
                curr = monthly[i]['rev']
                if prev > 0:
                    pct = (curr - prev) / prev * 100
                    if pct > best_pct:
                        best_pct = pct
                        best_growth = monthly[i]['month']
            if best_growth:
                insights.append({
                    'type': 'info', 'icon': 'bi-graph-up-arrow',
                    'title': 'Fastest Growing Month',
                    'description': f'{best_growth} saw the highest month-over-month growth at {best_pct:.1f}%.',
                    'metric': f'+{best_pct:.1f}%'
                })

        # 5. Customer concentration (top 10 customers revenue %)
        concentration = execute_query('''
            WITH ranked AS (
                SELECT customer_id, SUM(revenue) as cust_rev
                FROM sales GROUP BY customer_id ORDER BY cust_rev DESC LIMIT 10
            )
            SELECT SUM(cust_rev) as top10_rev FROM ranked
        ''')
        total_rev = execute_query('SELECT SUM(revenue) as t FROM sales')[0]['t'] or 1
        if concentration and concentration[0]['top10_rev']:
            pct = (concentration[0]['top10_rev'] / total_rev) * 100
            insights.append({
                'type': 'info', 'icon': 'bi-people',
                'title': 'Customer Revenue Concentration',
                'description': f'Top 10 customers account for {pct:.1f}% of total revenue (${concentration[0]["top10_rev"]:,.0f}).',
                'metric': f'{pct:.1f}%'
            })

        # 6. Best margin category
        best_margin = execute_query('''
            SELECT category, 
                   CASE WHEN SUM(revenue) > 0 THEN (SUM(profit)/SUM(revenue))*100 ELSE 0 END as margin,
                   SUM(profit) as profit
            FROM sales GROUP BY category ORDER BY margin DESC LIMIT 1
        ''')
        if best_margin:
            b = best_margin[0]
            insights.append({
                'type': 'success', 'icon': 'bi-percent',
                'title': 'Highest Profit Margin Category',
                'description': f'{b["category"]} leads with {b["margin"]:.1f}% profit margin (${b["profit"]:,.0f} profit).',
                'metric': f'{b["margin"]:.1f}%'
            })

        # 7. Revenue trend (last 6 months direction)
        recent = execute_query('''
            SELECT strftime('%Y-%m', sale_date) as month, SUM(revenue) as rev
            FROM sales
            GROUP BY month ORDER BY month DESC LIMIT 6
        ''')
        if len(recent) >= 3:
            recent.reverse()
            trend_vals = [r['rev'] for r in recent]
            is_up = trend_vals[-1] > trend_vals[0]
            change_pct = ((trend_vals[-1] - trend_vals[0]) / trend_vals[0] * 100) if trend_vals[0] > 0 else 0
            insights.append({
                'type': 'success' if is_up else 'warning',
                'icon': 'bi-arrow-up-right' if is_up else 'bi-arrow-down-right',
                'title': '6-Month Revenue Trend',
                'description': f'Revenue is {"trending up" if is_up else "trending down"} — {change_pct:+.1f}% over the last 6 months.',
                'metric': f'{change_pct:+.1f}%'
            })

        return insights
