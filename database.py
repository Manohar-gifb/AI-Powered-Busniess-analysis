"""
database.py - Database Setup and Helper Functions
=================================================
Handles all SQLite database operations for the BI Dashboard.
Creates tables, provides connection helpers, and manages DB lifecycle.
"""

import sqlite3
import os

# Database path - relative to project root (works on any Windows machine)
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'database')
DB_PATH = os.path.join(DB_DIR, 'bi_dashboard.db')


def get_db():
    """
    Get a database connection.
    Returns a connection object with row_factory set to sqlite3.Row
    so columns can be accessed by name.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
    return conn


def is_db_empty():
    """Check if the database has any tables with data (used for first-run seeding)."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='regions'")
        if not cursor.fetchone():
            return True  # Business tables don't exist yet
        cursor.execute("SELECT COUNT(*) as cnt FROM regions")
        row = cursor.fetchone()
        return row['cnt'] == 0
    except Exception:
        return True  # If anything goes wrong, treat as empty
    finally:
        conn.close()


def init_db():
    """
    Initialize the database by creating all required tables.
    This function is safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = get_db()
    cursor = conn.cursor()

    # ================================================================
    # PHASE 1 TABLES (authentication, uploads, ML, etc.)
    # ================================================================

    # ---- Users table for authentication ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # ---- Uploaded datasets metadata ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            column_names TEXT DEFAULT '',
            status TEXT DEFAULT 'uploaded',
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ---- Actual data rows stored from uploaded CSV/Excel ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            row_index INTEGER NOT NULL,
            row_data TEXT NOT NULL,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        )
    ''')

    # ---- ML models metadata ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dataset_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            model_type TEXT NOT NULL,
            target_column TEXT NOT NULL,
            feature_columns TEXT DEFAULT '',
            accuracy REAL DEFAULT 0.0,
            model_file TEXT DEFAULT '',
            parameters TEXT DEFAULT '',
            trained_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        )
    ''')

    # ---- Forecast results ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dataset_id INTEGER NOT NULL,
            forecast_type TEXT NOT NULL,
            target_column TEXT NOT NULL,
            forecast_values TEXT NOT NULL,
            forecast_dates TEXT DEFAULT '',
            confidence_lower TEXT DEFAULT '',
            confidence_upper TEXT DEFAULT '',
            metrics TEXT DEFAULT '',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        )
    ''')

    # ---- Anomaly detection results ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dataset_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            anomaly_count INTEGER DEFAULT 0,
            total_rows INTEGER DEFAULT 0,
            anomaly_indices TEXT DEFAULT '',
            threshold REAL DEFAULT 0.0,
            method TEXT DEFAULT 'iqr',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        )
    ''')

    # ---- AI Recommendations ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dataset_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            impact TEXT DEFAULT '',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        )
    ''')

    # ================================================================
    # PHASE 2 TABLES (business data for analytics)
    # ================================================================

    # ---- Regions lookup table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_name TEXT UNIQUE NOT NULL,
            country TEXT DEFAULT '',
            manager TEXT DEFAULT ''
        )
    ''')

    # ---- Product categories lookup table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT ''
        )
    ''')

    # ---- Customers table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            city TEXT DEFAULT '',
            region_id INTEGER,
            segment TEXT DEFAULT 'Regular',
            FOREIGN KEY (region_id) REFERENCES regions(id)
        )
    ''')

    # ---- Products table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category_id INTEGER,
            unit_price REAL DEFAULT 0.0,
            cost_price REAL DEFAULT 0.0,
            stock_quantity INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # ---- Sales table (main business data) ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_date TEXT NOT NULL,
            product_id INTEGER,
            customer_id INTEGER,
            region TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            unit_price REAL DEFAULT 0.0,
            revenue REAL DEFAULT 0.0,
            cost REAL DEFAULT 0.0,
            profit REAL DEFAULT 0.0,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')

    # ---- Indexes for faster queries on sales ----
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_category ON sales(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id)')

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully.")


def execute_query(query, params=None, fetch=True):
    """
    Execute a SQL query and optionally return results.
    Used as a convenience wrapper for common operations.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            results = cursor.fetchall()
            conn.close()
            return [dict(row) for row in results]
        else:
            conn.commit()
            last_id = cursor.lastrowid
            conn.close()
            return last_id
    except Exception as e:
        conn.close()
        raise e


def execute_many(query, params_list):
    """Execute a query with many parameter sets (for bulk inserts)."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.executemany(query, params_list)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == '__main__':
    # Run directly to initialize the database
    init_db()
    print(f"Database created at: {DB_PATH}")
