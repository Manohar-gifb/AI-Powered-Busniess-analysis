"""
seed_data.py - Sample Business Data Generator
=============================================
Generates realistic sample data for the BI Dashboard.
Runs automatically on first startup when the database is empty.

Data generated:
- 5 regions
- 6 product categories
- 80 customers
- 40 products
- 1500 sales records over 2 years (2024-2025)
"""

import random
from datetime import datetime, timedelta
from database import get_db, execute_query

# Fixed seed for reproducible data across runs
random.seed(42)

# ============================================================
# REFERENCE DATA
# ============================================================

REGIONS = [
    ("North America", "United States", "Alice Johnson"),
    ("Europe", "United Kingdom", "Bob Smith"),
    ("Asia Pacific", "Japan", "Charlie Tanaka"),
    ("Latin America", "Brazil", "Diana Santos"),
    ("Middle East", "UAE", "Omar Al-Rashid"),
]

CATEGORIES = [
    ("Electronics", "Computers, phones, and electronic gadgets"),
    ("Furniture", "Office and home furniture"),
    ("Clothing", "Apparel and fashion accessories"),
    ("Food & Beverage", "Packaged food and drinks"),
    ("Sports & Outdoors", "Fitness equipment and outdoor gear"),
    ("Office Supplies", "Stationery and office consumables"),
]

# Products with realistic pricing per category
PRODUCTS_BY_CATEGORY = {
    "Electronics": [
        ("Wireless Mouse", 29.99, 12.50),
        ("Mechanical Keyboard", 79.99, 35.00),
        ("27-inch Monitor", 299.99, 150.00),
        ("USB-C Hub", 49.99, 18.00),
        ("Webcam HD", 59.99, 22.00),
        ("Bluetooth Speaker", 39.99, 15.00),
    ],
    "Furniture": [
        ("Office Chair", 199.99, 85.00),
        ("Standing Desk", 349.99, 145.00),
        ("Bookshelf", 129.99, 55.00),
        ("Filing Cabinet", 89.99, 38.00),
        ("Coffee Table", 149.99, 62.00),
    ],
    "Clothing": [
        ("Polo Shirt", 34.99, 12.00),
        ("Chinos", 44.99, 15.00),
        ("Winter Jacket", 89.99, 35.00),
        ("Running Shoes", 69.99, 28.00),
        ("Backpack", 54.99, 20.00),
    ],
    "Food & Beverage": [
        ("Coffee Beans 1kg", 18.99, 7.50),
        ("Protein Bars (12pk)", 24.99, 10.00),
        ("Green Tea (50 bags)", 9.99, 3.50),
        ("Energy Drink (24pk)", 29.99, 12.00),
        ("Trail Mix 500g", 12.99, 5.00),
    ],
    "Sports & Outdoors": [
        ("Yoga Mat", 29.99, 10.00),
        ("Dumbbell Set", 79.99, 32.00),
        ("Camping Tent", 149.99, 60.00),
        ("Hiking Backpack", 99.99, 38.00),
        ("Water Bottle", 14.99, 4.50),
    ],
    "Office Supplies": [
        ("Notebook (3-pack)", 8.99, 2.50),
        ("Printer Paper (500 sheets)", 7.99, 3.00),
        ("Whiteboard Markers (12)", 11.99, 3.50),
        ("Desk Organizer", 19.99, 7.00),
        ("Stapler Heavy-Duty", 15.99, 5.50),
    ],
}

# Customer first/last names for generating realistic names
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Daniel", "Lisa", "Matthew", "Nancy",
    "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley",
    "Andrew", "Dorothy", "Paul", "Kimberly", "Joshua", "Emily", "Kenneth", "Donna",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
]

CITIES_BY_REGION = {
    "North America": ["New York", "Los Angeles", "Chicago", "Houston", "Toronto", "Vancouver"],
    "Europe": ["London", "Paris", "Berlin", "Amsterdam", "Madrid", "Milan"],
    "Asia Pacific": ["Tokyo", "Seoul", "Singapore", "Sydney", "Mumbai", "Shanghai"],
    "Latin America": ["São Paulo", "Mexico City", "Buenos Aires", "Lima", "Bogotá"],
    "Middle East": ["Dubai", "Abu Dhabi", "Riyadh", "Doha", "Istanbul"],
}

SEGMENTS = ["Regular", "Premium", "VIP", "New", "Returning"]


def seed_regions(cursor):
    """Insert region data. Returns dict of region_name -> id."""
    print("  Seeding regions...")
    for name, country, manager in REGIONS:
        cursor.execute(
            "INSERT OR IGNORE INTO regions (region_name, country, manager) VALUES (?, ?, ?)",
            (name, country, manager)
        )
    rows = cursor.execute("SELECT id, region_name FROM regions").fetchall()
    return {row['region_name']: row['id'] for row in rows}


def seed_categories(cursor):
    """Insert category data. Returns dict of category_name -> id."""
    print("  Seeding categories...")
    for name, desc in CATEGORIES:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (category_name, description) VALUES (?, ?)",
            (name, desc)
        )
    rows = cursor.execute("SELECT id, category_name FROM categories").fetchall()
    return {row['category_name']: row['id'] for row in rows}


def seed_customers(cursor, region_map):
    """Insert 80 customers. Returns list of customer IDs."""
    print("  Seeding customers...")
    customers = []
    used_emails = set()

    for i in range(80):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        region_name = random.choice(list(region_map.keys()))
        region_id = region_map[region_name]
        city = random.choice(CITIES_BY_REGION[region_name])
        segment = random.choices(SEGMENTS, weights=[40, 25, 10, 15, 10])[0]

        # Generate unique email
        base_email = f"{first.lower()}.{last.lower()}"
        email = f"{base_email}@example.com"
        counter = 1
        while email in used_emails:
            email = f"{base_email}{counter}@example.com"
            counter += 1
        used_emails.add(email)

        phone = f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"

        cursor.execute(
            "INSERT INTO customers (customer_name, email, phone, city, region_id, segment) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, phone, city, region_id, segment)
        )
        customers.append(cursor.lastrowid)

    return customers


def seed_products(cursor, category_map):
    """Insert products from predefined list. Returns dict of product_name -> (id, unit_price)."""
    print("  Seeding products...")
    products = {}
    for cat_name, items in PRODUCTS_BY_CATEGORY.items():
        cat_id = category_map[cat_name]
        for prod_name, price, cost in items:
            stock = random.randint(20, 500)
            cursor.execute(
                "INSERT INTO products (product_name, category_id, unit_price, cost_price, stock_quantity) "
                "VALUES (?, ?, ?, ?, ?)",
                (prod_name, cat_id, price, cost, stock)
            )
            products[prod_name] = (cursor.lastrowid, price, cost)
    return products


def seed_sales(cursor, customer_ids, products_dict):
    """
    Generate 1500 sales records over 2 years (2024-2025).
    Includes realistic patterns: seasonal variation, weekend dips,
    occasional high-value orders, and a few anomalous records.
    """
    print("  Seeding sales records (this may take a moment)...")

    # Build product lookup: category -> list of (product_id, price, cost)
    cat_products = {}
    for prod_name, (pid, price, cost) in products_dict.items():
        # Determine category from product name
        for cat_name, items in PRODUCTS_BY_CATEGORY.items():
            for item_name, _, _ in items:
                if item_name == prod_name:
                    cat_products.setdefault(cat_name, []).append((pid, price, cost))
                    break

    # Build region list
    region_names = [r[0] for r in REGIONS]

    # Date range: Jan 2024 - Dec 2025 (2 years)
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    total_days = (end_date - start_date).days

    sales_records = []
    anomaly_indices = []  # Track which records are anomalies

    for i in range(1500):
        # Pick a random date with slight seasonal weighting
        day_offset = random.randint(0, total_days)
        sale_date = start_date + timedelta(days=day_offset)

        # Seasonal effect: more sales in Nov-Dec (holiday), fewer in Jan-Feb
        month = sale_date.month
        if month in (11, 12):
            qty_multiplier = random.uniform(1.2, 2.0)
        elif month in (1, 2):
            qty_multiplier = random.uniform(0.5, 0.9)
        else:
            qty_multiplier = random.uniform(0.7, 1.3)

        # Weekend dip
        if sale_date.weekday() >= 5:  # Saturday or Sunday
            qty_multiplier *= 0.6

        # Pick random product category and product
        cat_name = random.choice(list(cat_products.keys()))
        pid, base_price, base_cost = random.choice(cat_products[cat_name])

        # Pick region and customer
        region = random.choice(region_names)
        cust_id = random.choice(customer_ids)

        # Calculate quantity with multiplier
        quantity = max(1, int(random.randint(1, 8) * qty_multiplier))

        # Unit price with small random variation (+/- 5%)
        unit_price = round(base_price * random.uniform(0.95, 1.05), 2)

        # Revenue and cost
        revenue = round(quantity * unit_price, 2)
        cost = round(quantity * base_cost * random.uniform(0.95, 1.05), 2)
        profit = round(revenue - cost, 2)

        # ---- Inject anomalies (~3% of records) ----
        if random.random() < 0.03:
            anomaly_type = random.choice(['high_revenue', 'high_quantity', 'negative_profit'])
            if anomaly_type == 'high_revenue':
                revenue = round(revenue * random.uniform(5, 15), 2)
                profit = round(revenue - cost, 2)
                quantity = max(1, quantity * random.randint(5, 15))
            elif anomaly_type == 'high_quantity':
                quantity = random.randint(200, 500)
                revenue = round(quantity * unit_price, 2)
                cost = round(quantity * base_cost, 2)
                profit = round(revenue - cost, 2)
            elif anomaly_type == 'negative_profit':
                cost = round(revenue * random.uniform(1.2, 2.5), 2)
                profit = round(revenue - cost, 2)
            anomaly_indices.append(i)

        sales_records.append((
            sale_date.strftime('%Y-%m-%d'),
            pid,
            cust_id,
            region,
            cat_name,
            quantity,
            unit_price,
            revenue,
            cost,
            profit
        ))

    # Bulk insert for performance
    cursor.executemany(
        "INSERT INTO sales (sale_date, product_id, customer_id, region, category, "
        "quantity, unit_price, revenue, cost, profit) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        sales_records
    )

    return len(sales_records), len(anomaly_indices)


def seed_users(cursor):
    """Create a default demo administrator account."""
    print("  Seeding demo admin user...")
    from werkzeug.security import generate_password_hash

    # Check if admin already exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone():
        print("  Admin user already exists, skipping.")
        return

    admin_hash = generate_password_hash('admin123')
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
        ('admin', 'admin@bidashboard.com', admin_hash, 'Administrator', 'admin')
    )
    print("  Demo admin created: username=admin  password=admin123")


def seed_all():
    """
    Main seeding function. Creates all sample data in the database.
    Safe to call multiple times - skips if data already exists.
    """
    from database import is_db_empty

    # Always ensure demo user exists (even if business data was already seeded)
    conn = get_db()
    cursor = conn.cursor()
    try:
        seed_users(cursor)
        conn.commit()
    finally:
        conn.close()

    if not is_db_empty():
        print("[SKIP] Database already contains sample data. Skipping seed.")
        return False

    print("[SEED] Generating sample business data...")
    conn = get_db()
    cursor = conn.cursor()

    try:
        region_map = seed_regions(cursor)
        category_map = seed_categories(cursor)
        customer_ids = seed_customers(cursor, region_map)
        products_dict = seed_products(cursor, category_map)
        sales_count, anomaly_count = seed_sales(cursor, customer_ids, products_dict)

        conn.commit()

        # Print summary
        print(f"  Regions:       {len(region_map)}")
        print(f"  Categories:    {len(category_map)}")
        print(f"  Customers:     {len(customer_ids)}")
        print(f"  Products:      {len(products_dict)}")
        print(f"  Sales records: {sales_count}")
        print(f"  Anomalies:     {anomaly_count} (injected for detection testing)")
        print("[SEED] Sample data generation complete!")

        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    # Can be run directly to re-seed
    from database import init_db
    init_db()
    seed_all()
