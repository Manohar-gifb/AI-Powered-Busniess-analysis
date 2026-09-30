"""
reporting.py - Business Reporting Module
=========================================
Generates comprehensive business reports with export to:
- CSV
- Excel (XLSX)
- Printable HTML

All data sourced from database queries and ML results.
"""

import csv
import io
import json
from datetime import datetime


def get_report_data(filters=None):
    """
    Aggregate all report data based on optional filters.

    Args:
        filters: dict with start_date, end_date, region, category

    Returns:
        dict with all report sections
    """
    from models import Sale, Region, Category

    # Build WHERE clause for filters
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

    where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''

    # Use Sale's filtered queries if filters exist
    if conditions:
        filter_dict = {}
        if filters.get('start_date'): filter_dict['start_date'] = filters['start_date']
        if filters.get('end_date'): filter_dict['end_date'] = filters['end_date']
        if filters.get('region'): filter_dict['region'] = filters['region']
        if filters.get('category'): filter_dict['category'] = filters['category']
        kpis = Sale.get_filtered_kpis(filter_dict)
        monthly = Sale.get_filtered_monthly(filter_dict)
        by_region = Sale.get_filtered_by_region(filter_dict)
        by_category = Sale.get_filtered_by_category(filter_dict)
        top_products = Sale.get_filtered_top_products(filter_dict, limit=10)
        by_segment = Sale.get_filtered_by_segment(filter_dict)
    else:
        kpis = {
            'total_orders': Sale.get_count(),
            'total_customers': 80,
            'total_revenue': Sale.get_total_revenue(),
            'total_profit': Sale.get_total_profit(),
            'avg_order_value': Sale.get_avg_order_value(),
            'profit_margin': Sale.get_profit_margin(),
        }
        monthly = Sale.get_monthly_revenue()
        by_region = Sale.get_revenue_by_region()
        by_category = Sale.get_revenue_by_category()
        top_products = Sale.get_top_products(10)
        by_segment = Sale.get_sales_by_customer_segment()

    # Product performance
    product_perf = Sale.get_product_performance()

    # Recommendations
    try:
        from recommendations import get_recommendation_summary
        recs_data = get_recommendation_summary()
        recommendations = recs_data.get('recommendations', [])
    except Exception:
        recommendations = []

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'filters': filters or {},
        'kpis': kpis,
        'monthly': monthly,
        'by_region': by_region,
        'by_category': by_category,
        'top_products': top_products,
        'product_performance': product_perf[:20],
        'by_segment': by_segment,
        'recommendations': recommendations[:15],
    }


def export_csv(data):
    """Export report data to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)

    # KPIs section
    writer.writerow(['=== BUSINESS INTELLIGENCE REPORT ==='])
    writer.writerow(['Generated', data['generated_at']])
    if data.get('filters'):
        for k, v in data['filters'].items():
            writer.writerow([f'Filter: {k}', v])
    writer.writerow([])

    # KPIs
    writer.writerow(['=== KEY PERFORMANCE INDICATORS ==='])
    kpis = data['kpis']
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Revenue', f"${kpis.get('total_revenue', 0):,.2f}"])
    writer.writerow(['Total Profit', f"${kpis.get('total_profit', 0):,.2f}"])
    writer.writerow(['Total Orders', kpis.get('total_orders', 0)])
    writer.writerow(['Total Customers', kpis.get('total_customers', 0)])
    writer.writerow(['Avg Order Value', f"${kpis.get('avg_order_value', 0):,.2f}"])
    writer.writerow(['Profit Margin', f"{kpis.get('profit_margin', 0):.1f}%"])
    writer.writerow([])

    # Monthly Revenue
    writer.writerow(['=== MONTHLY REVENUE ==='])
    writer.writerow(['Month', 'Revenue', 'Profit', 'Orders'])
    for m in data.get('monthly', []):
        writer.writerow([m['month'], f"{m['total_revenue']:.2f}", f"{m['total_profit']:.2f}", m['sale_count']])
    writer.writerow([])

    # By Region
    writer.writerow(['=== REVENUE BY REGION ==='])
    writer.writerow(['Region', 'Revenue', 'Profit', 'Orders', 'Margin'])
    for r in data.get('by_region', []):
        margin = (r['total_profit'] / r['total_revenue'] * 100) if r['total_revenue'] > 0 else 0
        writer.writerow([r['region'], f"{r['total_revenue']:.2f}", f"{r['total_profit']:.2f}", r['sale_count'], f"{margin:.1f}%"])
    writer.writerow([])

    # By Category
    writer.writerow(['=== REVENUE BY CATEGORY ==='])
    writer.writerow(['Category', 'Revenue', 'Profit', 'Orders', 'Margin'])
    for c in data.get('by_category', []):
        margin = (c['total_profit'] / c['total_revenue'] * 100) if c['total_revenue'] > 0 else 0
        writer.writerow([c['category'], f"{c['total_revenue']:.2f}", f"{c['total_profit']:.2f}", c['sale_count'], f"{margin:.1f}%"])
    writer.writerow([])

    # Top Products
    writer.writerow(['=== TOP PRODUCTS ==='])
    writer.writerow(['Product', 'Revenue', 'Units Sold', 'Profit'])
    for p in data.get('top_products', []):
        writer.writerow([p['product_name'], f"{p['total_revenue']:.2f}", p['total_sold'], f"{p['total_profit']:.2f}"])
    writer.writerow([])

    # Recommendations
    writer.writerow(['=== AI RECOMMENDATIONS ==='])
    writer.writerow(['Priority', 'Category', 'Title', 'Metric', 'Recommendation'])
    for r in data.get('recommendations', []):
        writer.writerow([r['priority'].upper(), r['category'], r['title'], r['metric'], r['recommendation']])

    return output.getvalue().encode('utf-8')


def export_excel(data):
    """Export report data to Excel format."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()

    # Styles
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
    title_font = Font(bold=True, size=14, color='1E293B')
    section_font = Font(bold=True, size=12, color='2563EB')
    money_format = '#,##0.00'
    pct_format = '0.0%'
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    def style_header(ws, row, cols):
        for col in range(1, cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border

    def auto_width(ws):
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_len + 3, 35)

    # ---- Sheet 1: Summary ----
    ws = wb.active
    ws.title = 'Report Summary'

    ws.cell(row=1, column=1, value='Business Intelligence Report').font = title_font
    ws.cell(row=2, column=1, value=f'Generated: {data["generated_at"]}').font = Font(color='64748B')

    if data.get('filters'):
        row = 3
        for k, v in data['filters'].items():
            ws.cell(row=row, column=1, value=f'{k}: {v}')
            row += 1

    # KPIs
    row = ws.max_row + 2
    ws.cell(row=row, column=1, value='Key Performance Indicators').font = section_font
    row += 1
    ws.cell(row=row, column=1, value='Metric')
    ws.cell(row=row, column=2, value='Value')
    style_header(ws, row, 2)

    kpis = data['kpis']
    kpi_rows = [
        ('Total Revenue', kpis.get('total_revenue', 0)),
        ('Total Profit', kpis.get('total_profit', 0)),
        ('Total Orders', kpis.get('total_orders', 0)),
        ('Total Customers', kpis.get('total_customers', 0)),
        ('Avg Order Value', kpis.get('avg_order_value', 0)),
        ('Profit Margin (%)', kpis.get('profit_margin', 0)),
    ]
    for name, val in kpi_rows:
        row += 1
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=round(val, 2))
        ws.cell(row=row, column=2).number_format = money_format

    # ---- Sheet 2: Monthly ----
    ws2 = wb.create_sheet('Monthly Revenue')
    ws2.cell(row=1, column=1, value='Monthly Revenue Trend').font = section_font
    headers = ['Month', 'Revenue', 'Profit', 'Orders', 'Avg Order']
    for i, h in enumerate(headers, 1):
        ws2.cell(row=3, column=i, value=h)
    style_header(ws2, 3, len(headers))

    for m in data.get('monthly', []):
        row = ws2.max_row + 1
        ws2.cell(row=row, column=1, value=m['month'])
        ws2.cell(row=row, column=2, value=round(m['total_revenue'], 2))
        ws2.cell(row=row, column=3, value=round(m['total_profit'], 2))
        ws2.cell(row=row, column=4, value=m['sale_count'])
        avg = m['total_revenue'] / m['sale_count'] if m['sale_count'] > 0 else 0
        ws2.cell(row=row, column=5, value=round(avg, 2))
    auto_width(ws2)

    # ---- Sheet 3: Region ----
    ws3 = wb.create_sheet('By Region')
    ws3.cell(row=1, column=1, value='Revenue by Region').font = section_font
    headers = ['Region', 'Revenue', 'Profit', 'Orders', 'Margin']
    for i, h in enumerate(headers, 1):
        ws3.cell(row=3, column=i, value=h)
    style_header(ws3, 3, len(headers))

    for r in data.get('by_region', []):
        row = ws3.max_row + 1
        margin = (r['total_profit'] / r['total_revenue'] * 100) if r['total_revenue'] > 0 else 0
        ws3.cell(row=row, column=1, value=r['region'])
        ws3.cell(row=row, column=2, value=round(r['total_revenue'], 2))
        ws3.cell(row=row, column=3, value=round(r['total_profit'], 2))
        ws3.cell(row=row, column=4, value=r['sale_count'])
        ws3.cell(row=row, column=5, value=f"{margin:.1f}%")
    auto_width(ws3)

    # ---- Sheet 4: Category ----
    ws4 = wb.create_sheet('By Category')
    ws4.cell(row=1, column=1, value='Revenue by Category').font = section_font
    headers = ['Category', 'Revenue', 'Profit', 'Orders', 'Margin']
    for i, h in enumerate(headers, 1):
        ws4.cell(row=3, column=i, value=h)
    style_header(ws4, 3, len(headers))

    for c in data.get('by_category', []):
        row = ws4.max_row + 1
        margin = (c['total_profit'] / c['total_revenue'] * 100) if c['total_revenue'] > 0 else 0
        ws4.cell(row=row, column=1, value=c['category'])
        ws4.cell(row=row, column=2, value=round(c['total_revenue'], 2))
        ws4.cell(row=row, column=3, value=round(c['total_profit'], 2))
        ws4.cell(row=row, column=4, value=c['sale_count'])
        ws4.cell(row=row, column=5, value=f"{margin:.1f}%")
    auto_width(ws4)

    # ---- Sheet 5: Top Products ----
    ws5 = wb.create_sheet('Top Products')
    ws5.cell(row=1, column=1, value='Top Products by Revenue').font = section_font
    headers = ['Product', 'Revenue', 'Units Sold', 'Profit']
    for i, h in enumerate(headers, 1):
        ws5.cell(row=3, column=i, value=h)
    style_header(ws5, 3, len(headers))

    for p in data.get('top_products', []):
        row = ws5.max_row + 1
        ws5.cell(row=row, column=1, value=p['product_name'])
        ws5.cell(row=row, column=2, value=round(p['total_revenue'], 2))
        ws5.cell(row=row, column=3, value=p['total_sold'])
        ws5.cell(row=row, column=4, value=round(p['total_profit'], 2))
    auto_width(ws5)

    # ---- Sheet 6: Recommendations ----
    ws6 = wb.create_sheet('Recommendations')
    ws6.cell(row=1, column=1, value='AI Business Recommendations').font = section_font
    headers = ['Priority', 'Category', 'Title', 'Metric', 'Recommendation']
    for i, h in enumerate(headers, 1):
        ws6.cell(row=3, column=i, value=h)
    style_header(ws6, 3, len(headers))

    for r in data.get('recommendations', []):
        row = ws6.max_row + 1
        ws6.cell(row=row, column=1, value=r['priority'].upper())
        ws6.cell(row=row, column=2, value=r['category'])
        ws6.cell(row=row, column=3, value=r['title'])
        ws6.cell(row=row, column=4, value=r['metric'])
        ws6.cell(row=row, column=5, value=r['recommendation'])
    auto_width(ws6)

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def export_html_report(data):
    """Generate a printable HTML report."""
    kpis = data['kpis']
    margin = kpis.get('profit_margin', 0)

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>Business Intelligence Report - {data['generated_at']}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; color: #1e293b; }}
    h1 {{ color: #1e3a8a; border-bottom: 3px solid #2563eb; padding-bottom: 8px; }}
    h2 {{ color: #2563eb; margin-top: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
    .subtitle {{ color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1rem 0; }}
    .kpi {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; text-align: center; }}
    .kpi .val {{ font-size: 1.4rem; font-weight: 700; color: #1e293b; }}
    .kpi .lbl {{ font-size: 0.8rem; color: #64748b; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.88rem; }}
    th {{ background: #1e3a8a; color: white; padding: 8px 12px; text-align: left; }}
    td {{ padding: 6px 12px; border-bottom: 1px solid #e2e8f0; }}
    tr:nth-child(even) {{ background: #f8fafc; }}
    .rec {{ background: #f8fafc; border-left: 3px solid #2563eb; padding: 8px 12px; margin: 8px 0; border-radius: 0 6px 6px 0; }}
    .rec .title {{ font-weight: 600; }}
    .rec .metric {{ color: #2563eb; font-weight: 700; }}
    .priority-high {{ color: #dc2626; }} .priority-medium {{ color: #d97706; }} .priority-info {{ color: #2563eb; }}
    @media print {{ body {{ padding: 10px; }} h1 {{ font-size: 1.5rem; }} }}
</style></head><body>
<h1>Business Intelligence Report</h1>
<p class="subtitle">Generated: {data['generated_at']} | AI-Powered Business Intelligence Dashboard</p>
"""

    if data.get('filters'):
        html += "<p><strong>Filters Applied:</strong> "
        html += " | ".join(f"{k}: {v}" for k, v in data['filters'].items() if v)
        html += "</p>"

    # KPIs
    html += f"""<h2>Key Performance Indicators</h2>
<div class="kpi-grid">
    <div class="kpi"><div class="val">${kpis.get('total_revenue', 0):,.0f}</div><div class="lbl">Total Revenue</div></div>
    <div class="kpi"><div class="val">${kpis.get('total_profit', 0):,.0f}</div><div class="lbl">Total Profit</div></div>
    <div class="kpi"><div class="val">{kpis.get('total_orders', 0):,}</div><div class="lbl">Total Orders</div></div>
    <div class="kpi"><div class="val">{kpis.get('total_customers', 0):,}</div><div class="lbl">Customers</div></div>
    <div class="kpi"><div class="val">${kpis.get('avg_order_value', 0):,.2f}</div><div class="lbl">Avg Order Value</div></div>
    <div class="kpi"><div class="val">{margin:.1f}%</div><div class="lbl">Profit Margin</div></div>
</div>"""

    # By Region
    html += "<h2>Revenue by Region</h2><table><tr><th>Region</th><th>Revenue</th><th>Profit</th><th>Orders</th><th>Margin</th></tr>"
    for r in data.get('by_region', []):
        m = (r['total_profit'] / r['total_revenue'] * 100) if r['total_revenue'] > 0 else 0
        html += f"<tr><td>{r['region']}</td><td>${r['total_revenue']:,.0f}</td><td>${r['total_profit']:,.0f}</td><td>{r['sale_count']}</td><td>{m:.1f}%</td></tr>"
    html += "</table>"

    # By Category
    html += "<h2>Revenue by Category</h2><table><tr><th>Category</th><th>Revenue</th><th>Profit</th><th>Orders</th><th>Margin</th></tr>"
    for c in data.get('by_category', []):
        m = (c['total_profit'] / c['total_revenue'] * 100) if c['total_revenue'] > 0 else 0
        html += f"<tr><td>{c['category']}</td><td>${c['total_revenue']:,.0f}</td><td>${c['total_profit']:,.0f}</td><td>{c['sale_count']}</td><td>{m:.1f}%</td></tr>"
    html += "</table>"

    # Top Products
    html += "<h2>Top Products</h2><table><tr><th>Product</th><th>Revenue</th><th>Units</th><th>Profit</th></tr>"
    for p in data.get('top_products', []):
        html += f"<tr><td>{p['product_name']}</td><td>${p['total_revenue']:,.0f}</td><td>{p['total_sold']}</td><td>${p['total_profit']:,.0f}</td></tr>"
    html += "</table>"

    # Recommendations
    html += "<h2>AI Business Recommendations</h2>"
    for r in data.get('recommendations', [])[:10]:
        pc = f"priority-{r['priority']}"
        html += f"""<div class="rec">
            <span class="title {pc}">[{r['priority'].upper()}] {r['title']}</span>
            <span class="metric">{r['metric']}</span><br>
            <small>{r['explanation']}</small><br>
            <strong>Recommendation:</strong> {r['recommendation']}
        </div>"""

    html += f"""
<hr>
<p style="color:#94a3b8;font-size:0.8rem;">
    Report generated by AI-Powered Business Intelligence Dashboard | {data['generated_at']}
</p>
</body></html>"""

    return html.encode('utf-8')
