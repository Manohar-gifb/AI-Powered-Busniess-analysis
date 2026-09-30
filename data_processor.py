"""
data_processor.py - Data Processing Module
===========================================
Reusable Pandas-based module for importing, validating, cleaning,
and storing business data from CSV/Excel files.

Handles:
- File reading (CSV, XLSX, XLS)
- Column detection and type inference
- Missing value handling
- Duplicate detection and removal
- Date and numeric conversion
- Validation against configurable required columns
- Import summary generation
- Storage in SQLite
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime


# ============================================================
# CONFIGURABLE BUSINESS COLUMN PROFILES
# ============================================================

# Common business column names and their expected types.
# The processor uses these to auto-detect and validate columns.
BUSINESS_COLUMN_PROFILES = {
    # Sales-related
    'sale_date':     {'type': 'date',      'required': False},
    'date':          {'type': 'date',      'required': False},
    'order_date':    {'type': 'date',      'required': False},
    'revenue':       {'type': 'numeric',   'required': False},
    'sales':         {'type': 'numeric',   'required': False},
    'amount':        {'type': 'numeric',   'required': False},
    'quantity':      {'type': 'numeric',   'required': False},
    'qty':           {'type': 'numeric',   'required': False},
    'unit_price':    {'type': 'numeric',   'required': False},
    'price':         {'type': 'numeric',   'required': False},
    'cost':          {'type': 'numeric',   'required': False},
    'profit':        {'type': 'numeric',   'required': False},
    'margin':        {'type': 'numeric',   'required': False},
    'discount':      {'type': 'numeric',   'required': False},
    'total':         {'type': 'numeric',   'required': False},
    # Category / classification
    'category':      {'type': 'text',      'required': False},
    'region':        {'type': 'text',      'required': False},
    'product':       {'type': 'text',      'required': False},
    'product_name':  {'type': 'text',      'required': False},
    'customer':      {'type': 'text',      'required': False},
    'customer_name': {'type': 'text',      'required': False},
}


class ProcessingResult:
    """Container for the result of a data processing operation."""

    def __init__(self):
        self.success = False
        self.original_rows = 0
        self.processed_rows = 0
        self.imported_rows = 0
        self.columns = []
        self.detected_types = {}
        self.business_columns_found = []
        self.missing_values_filled = 0
        self.duplicates_removed = 0
        self.date_columns_converted = []
        self.numeric_columns_converted = []
        self.errors = []
        self.warnings = []
        self.preview_data = []       # First 10 rows for preview
        self.summary = {}            # Stats summary
        self.raw_dataframe = None    # Original dataframe
        self.clean_dataframe = None  # Cleaned dataframe ready for import

    def to_dict(self):
        """Convert to dictionary for JSON serialization and template passing."""
        return {
            'success': self.success,
            'original_rows': self.original_rows,
            'processed_rows': self.processed_rows,
            'imported_rows': self.imported_rows,
            'columns': self.columns,
            'detected_types': self.detected_types,
            'business_columns_found': self.business_columns_found,
            'missing_values_filled': self.missing_values_filled,
            'duplicates_removed': self.duplicates_removed,
            'date_columns_converted': self.date_columns_converted,
            'numeric_columns_converted': self.numeric_columns_converted,
            'errors': self.errors,
            'warnings': self.warnings,
            'preview_data': self.preview_data,
            'summary': self.summary,
        }


def read_file(filepath):
    """
    Read a CSV or Excel file into a Pandas DataFrame.
    Returns the DataFrame or raises an error.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.csv':
        # Try common encodings and error handling
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                return pd.read_csv(filepath, encoding=encoding)
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError:
                # Try with error_bad_lines handling
                try:
                    return pd.read_csv(filepath, encoding=encoding, on_bad_lines='skip')
                except TypeError:
                    # Older pandas versions
                    try:
                        return pd.read_csv(filepath, encoding=encoding, error_bad_lines=False)
                    except Exception:
                        continue
        raise ValueError("Could not read CSV file. Unsupported encoding or format.")
    elif ext in ('.xlsx', '.xls'):
        return pd.read_excel(filepath, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def detect_column_type(series, col_name):
    """
    Detect the semantic type of a Pandas Series.
    Returns one of: 'date', 'numeric', 'text', 'id'
    """
    col_lower = col_name.lower().strip()

    # Check against known business column profiles
    if col_lower in BUSINESS_COLUMN_PROFILES:
        profile_type = BUSINESS_COLUMN_PROFILES[col_lower]['type']
        # Verify the data actually matches the expected type
        if profile_type == 'date':
            return 'date'
        elif profile_type == 'numeric':
            # Check if values are actually numeric
            numeric_count = pd.to_numeric(series, errors='coerce').notna().sum()
            if numeric_count / max(len(series), 1) > 0.7:
                return 'numeric'

    # Auto-detect: try numeric first
    numeric_count = pd.to_numeric(series, errors='coerce').notna().sum()
    if numeric_count / max(len(series), 1) > 0.8:
        return 'numeric'

    # Try date detection
    try:
        date_count = pd.to_datetime(series, errors='coerce').notna().sum()
        if date_count / max(len(series), 1) > 0.8:
            return 'date'
    except Exception:
        pass

    # Check for ID-like columns (unique integers)
    if numeric_count / max(len(series), 1) > 0.9:
        if series.nunique() == len(series.dropna()):
            return 'id'

    return 'text'


def convert_dates(df, columns=None):
    """
    Convert date columns to standard YYYY-MM-DD format.
    Returns (modified_df, list_of_converted_columns).
    """
    converted = []
    if columns is None:
        columns = df.columns.tolist()

    for col in columns:
        if detect_column_type(df[col], col) == 'date':
            try:
                parsed = pd.to_datetime(df[col], errors='coerce')
                # Only convert if most values parsed successfully
                if parsed.notna().sum() / max(len(parsed), 1) > 0.5:
                    df[col] = parsed.dt.strftime('%Y-%m-%d')
                    converted.append(col)
            except Exception:
                pass

    return df, converted


def convert_numerics(df, columns=None):
    """
    Convert numeric columns to proper numeric types.
    Returns (modified_df, list_of_converted_columns).
    """
    converted = []
    if columns is None:
        columns = df.columns.tolist()

    for col in columns:
        if detect_column_type(df[col], col) == 'numeric':
            original = df[col].copy()
            converted_col = pd.to_numeric(df[col], errors='coerce')
            # Only convert if most values are numeric
            if converted_col.notna().sum() / max(len(converted_col), 1) > 0.7:
                df[col] = converted_col
                converted.append(col)

    return df, converted


def handle_missing_values(df):
    """
    Handle missing values intelligently based on column type.
    Returns (modified_df, count_of_filled_values).
    """
    total_filled = 0

    for col in df.columns:
        null_count = df[col].isna().sum()
        if null_count == 0:
            continue

        col_type = detect_column_type(df[col], col)

        if col_type == 'numeric':
            # Fill with median (robust to outliers)
            median_val = df[col].median()
            if pd.notna(median_val):
                df[col] = df[col].fillna(median_val)
                total_filled += int(null_count)
            else:
                df[col] = df[col].fillna(0)
                total_filled += int(null_count)

        elif col_type == 'date':
            # Leave dates as NaT (will be handled during import)
            pass

        else:
            # Text: fill with a placeholder
            df[col] = df[col].fillna('Unknown')
            total_filled += int(null_count)

    return df, total_filled


def remove_duplicates(df):
    """
    Remove duplicate records from the DataFrame.
    Returns (modified_df, count_of_removed_duplicates).
    """
    original_count = len(df)
    df_clean = df.drop_duplicates()
    removed = original_count - len(df_clean)
    return df_clean, removed


def detect_business_columns(columns):
    """
    Detect which columns match known business column profiles.
    Returns list of detected business column names.
    """
    detected = []
    for col in columns:
        col_lower = col.lower().strip()
        if col_lower in BUSINESS_COLUMN_PROFILES:
            detected.append(col)
    return detected


def compute_summary(df):
    """
    Compute a statistical summary of the DataFrame.
    Returns a dictionary with summary statistics.
    """
    summary = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'numeric_columns': [],
        'text_columns': [],
        'date_columns': [],
        'memory_usage_kb': round(df.memory_usage(deep=True).sum() / 1024, 1),
    }

    for col in df.columns:
        col_type = detect_column_type(df[col], col)
        if col_type == 'numeric':
            summary['numeric_columns'].append({
                'name': col,
                'mean': round(float(df[col].mean()), 2) if pd.notna(df[col].mean()) else 0,
                'min': round(float(df[col].min()), 2) if pd.notna(df[col].min()) else 0,
                'max': round(float(df[col].max()), 2) if pd.notna(df[col].max()) else 0,
                'std': round(float(df[col].std()), 2) if pd.notna(df[col].std()) else 0,
            })
        elif col_type == 'date':
            non_null = df[col].dropna()
            summary['date_columns'].append({
                'name': col,
                'min': str(non_null.min()) if len(non_null) > 0 else '',
                'max': str(non_null.max()) if len(non_null) > 0 else '',
            })
        else:
            unique_count = df[col].nunique()
            summary['text_columns'].append({
                'name': col,
                'unique_values': int(unique_count),
            })

    return summary


def process_upload(filepath, required_columns=None, remove_dupes=True, handle_missing=True):
    """
    Main processing pipeline for an uploaded file.

    Steps:
    1. Read file
    2. Detect columns and types
    3. Convert dates and numerics
    4. Handle missing values
    5. Remove duplicates
    6. Compute summary
    7. Generate preview

    Args:
        filepath: Path to the uploaded file
        required_columns: Optional list of column names that must be present
        remove_dupes: Whether to remove duplicate rows (default True)
        handle_missing: Whether to fill missing values (default True)

    Returns:
        ProcessingResult with all metadata and the cleaned DataFrame
    """
    result = ProcessingResult()

    # ---- Step 1: Read file ----
    try:
        df = read_file(filepath)
    except Exception as e:
        result.errors.append(f"Failed to read file: {str(e)}")
        return result

    if df.empty:
        result.errors.append("The file is empty or contains no data rows.")
        return result

    result.original_rows = len(df)
    result.raw_dataframe = df.copy()

    # ---- Step 2: Basic validation ----
    if len(df.columns) < 2:
        result.errors.append("File must have at least 2 columns.")
        return result

    # Clean column names (strip whitespace, replace spaces with underscores)
    df.columns = [col.strip().replace(' ', '_').replace('-', '_') for col in df.columns]
    result.columns = df.columns.tolist()

    # ---- Step 3: Check required columns ----
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            result.errors.append(
                f"Missing required columns: {', '.join(missing_cols)}. "
                f"Found columns: {', '.join(df.columns.tolist())}"
            )
            return result

    # ---- Step 4: Detect column types ----
    for col in df.columns:
        result.detected_types[col] = detect_column_type(df[col], col)

    # ---- Step 5: Detect business columns ----
    result.business_columns_found = detect_business_columns(df.columns)

    # ---- Step 6: Convert dates ----
    df, date_converted = convert_dates(df)
    result.date_columns_converted = date_converted

    # ---- Step 7: Convert numerics ----
    df, num_converted = convert_numerics(df)
    result.numeric_columns_converted = num_converted

    # ---- Step 8: Handle missing values ----
    if handle_missing:
        df, filled_count = handle_missing_values(df)
        result.missing_values_filled = filled_count
    else:
        # Still count what's missing
        result.missing_values_filled = int(df.isna().sum().sum())

    # ---- Step 9: Remove duplicates ----
    if remove_dupes:
        df, dup_count = remove_duplicates(df)
        result.duplicates_removed = dup_count

    # ---- Step 10: Final validation ----
    if df.empty:
        result.warnings.append("All rows were removed during cleaning. No data to import.")
        result.processed_rows = 0
        return result

    # ---- Step 11: Compute summary ----
    result.summary = compute_summary(df)

    # ---- Step 12: Generate preview (first 10 rows) ----
    preview_df = df.head(10)
    result.preview_data = preview_df.fillna('').to_dict(orient='records')

    # ---- Store cleaned dataframe ----
    result.clean_dataframe = df
    result.processed_rows = len(df)
    result.success = True

    return result


def store_imported_data(dataset_id, df):
    """
    Store a processed DataFrame into the data_rows table.
    Each row is stored as JSON for flexible querying.

    Args:
        dataset_id: The dataset ID to associate rows with
        df: Pandas DataFrame to store

    Returns:
        Number of rows inserted
    """
    from database import get_db

    if df is None or df.empty:
        return 0

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Replace NaN with empty string for JSON serialization
        df_clean = df.fillna('')
        rows = df_clean.to_dict(orient='records')

        query = "INSERT INTO data_rows (dataset_id, row_index, row_data) VALUES (?, ?, ?)"
        data = [(dataset_id, idx, json.dumps(row)) for idx, row in enumerate(rows)]
        cursor.executemany(query, data)
        conn.commit()
        return len(data)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def export_as_csv(df, filepath):
    """Export a DataFrame to CSV."""
    df.to_csv(filepath, index=False)
    return filepath


def export_as_json(df, filepath):
    """Export a DataFrame to JSON."""
    df.to_json(filepath, orient='records', indent=2)
    return filepath
