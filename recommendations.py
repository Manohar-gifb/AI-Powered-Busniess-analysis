"""
recommendations.py - AI Business Recommendation Engine
=======================================================
Generates dynamic business recommendations by analyzing:
- KPI values and margins
- Sales and profit trends
- Regional and category performance
- Product performance
- Anomaly detection results
- Forecast trends
- Business rules

All recommendations are derived from actual database values.
No external APIs required — works completely offline.
"""

import json
from datetime import datetime


def _get_trend(values):
    """Calculate trend direction from a list of values. Returns (direction, pct_change)."""
    if len(values) < 2:
        return 'flat', 0
    recent = values[-3:]  # Last 3 periods
    older = values[-6:-3] if len(values) >= 6 else values[:3]

    avg_recent = sum(recent) / len(recent)
    avg_older = sum(older) / len(older)

    if avg_older == 0:
        return 'flat', 0
    pct = ((avg_recent - avg_older) / avg_older) * 100

    if pct > 10:
        return 'up', pct
    elif pct < -10:
        return 'down', pct
    return 'flat', pct


def generate_recommendations():
    """
    Main recommendation engine.
    Analyzes all available business data and generates recommendations.

    Returns:
        list of recommendation dicts, each with:
        category, priority, title, explanation, metric, recommendation, icon
    """
    from models import Sale, Region, Category, Customer, Product
    from database import execute_query

    recs = []

    # ================================================================
    # 1. OVERALL BUSINESS HEALTH
    # ================================================================

    total_revenue = Sale.get_total_revenue()
    total_profit = Sale.get_total_profit()
    margin = Sale.get_profit_margin()
    total_orders = Sale.get_count()

    # Low margin warning
    if margin < 40:
        recs.append({
            'category': 'Risk Warning',
            'priority': 'high',
            'title': 'Low Overall Profit Margin',
            'explanation': f'Current profit margin is {margin:.1f}%, which is below the 40% threshold for healthy business operations.',
            'metric': f'{margin:.1f}%',
            'recommendation': 'Review pricing strategy and cost structure. Consider increasing prices on low-margin products or reducing operational costs.',
            'icon': 'bi-exclamation-triangle',
        })
    elif margin > 60:
        recs.append({
            'category': 'Growth Opportunity',
            'priority': 'info',
            'title': 'Strong Profit Margin',
            'explanation': f'Profit margin of {margin:.1f}% indicates healthy pricing. This provides room for strategic investments.',
            'metric': f'{margin:.1f}%',
            'recommendation': 'Consider reinvesting profits into marketing or expansion. The strong margin can absorb growth investments.',
            'icon': 'bi-graph-up-arrow',
        })

    # ================================================================
    # 2. REGIONAL ANALYSIS
    # ================================================================

    regions = Sale.get_revenue_by_region()
    if regions:
        # Best performing region
        best = regions[0]
        best_margin = (best['total_profit'] / best['total_revenue'] * 100) if best['total_revenue'] > 0 else 0
        recs.append({
            'category': 'Sales Recommendation',
            'priority': 'info',
            'title': f'Top Region: {best["region"]}',
            'explanation': f'{best["region"]} leads with ${best["total_revenue"]:,.0f} revenue across {best["sale_count"]} sales. Margin: {best_margin:.1f}%.',
            'metric': f'${best["total_revenue"]:,.0f}',
            'recommendation': f'Increase sales team focus on {best["region"]}. Consider dedicated marketing campaigns and inventory allocation for this high-performing market.',
            'icon': 'bi-trophy',
        })

        # Worst performing region
        worst = regions[-1]
        worst_margin = (worst['total_profit'] / worst['total_revenue'] * 100) if worst['total_revenue'] > 0 else 0
        if worst_margin < 50:
            recs.append({
                'category': 'Region Recommendation',
                'priority': 'medium',
                'title': f'Underperforming Region: {worst["region"]}',
                'explanation': f'{worst["region"]} has the lowest revenue (${worst["total_revenue"]:,.0f}) with a {worst_margin:.1f}% margin. Consider strategy adjustments.',
                'metric': f'${worst["total_revenue"]:,.0f}',
                'recommendation': f'Analyze customer behavior in {worst["region"]}. May need localized pricing, different product mix, or targeted promotions.',
                'icon': 'bi-geo-alt',
            })

        # Region margin comparison
        if len(regions) >= 2:
            high_margin_region = max(regions, key=lambda r: r['total_profit'] / r['total_revenue'] if r['total_revenue'] > 0 else 0)
            hm = high_margin_region['total_profit'] / high_margin_region['total_revenue'] * 100
            recs.append({
                'category': 'Profit Recommendation',
                'priority': 'info',
                'title': f'Highest Margin Region: {high_margin_region["region"]}',
                'explanation': f'{high_margin_region["region"]} achieves {hm:.1f}% profit margin, the best among all regions.',
                'metric': f'{hm:.1f}%',
                'recommendation': f'Apply {high_margin_region["region"]}\'s successful strategies to underperforming regions. Study pricing and cost structures.',
                'icon': 'bi-percent',
            })

    # ================================================================
    # 3. CATEGORY ANALYSIS
    # ================================================================

    categories = Sale.get_revenue_by_category()
    if categories:
        best_cat = categories[0]
        recs.append({
            'category': 'Product Recommendation',
            'priority': 'info',
            'title': f'Top Category: {best_cat["category"]}',
            'explanation': f'{best_cat["category"]} generates ${best_cat["total_revenue"]:,.0f} revenue with {best_cat["sale_count"]} sales.',
            'metric': f'${best_cat["total_revenue"]:,.0f}',
            'recommendation': f'Expand {best_cat["category"]} product line. Consider adding complementary products and increasing inventory levels.',
            'icon': 'bi-box-seam',
        })

        # Low revenue category
        low_cat = categories[-1]
        low_margin = (low_cat['total_profit'] / low_cat['total_revenue'] * 100) if low_cat['total_revenue'] > 0 else 0
        recs.append({
            'category': 'Inventory Recommendation',
            'priority': 'medium',
            'title': f'Low Revenue Category: {low_cat["category"]}',
            'explanation': f'{low_cat["category"]} generates only ${low_cat["total_revenue"]:,.0f} ({low_cat["sale_count"]} sales). Margin: {low_margin:.1f}%.',
            'metric': f'${low_cat["total_revenue"]:,.0f}',
            'recommendation': f'Review {low_cat["category"]} inventory levels. Consider reducing stock to free up capital for higher-performing categories.',
            'icon': 'bi-archive',
        })

    # ================================================================
    # 4. SALES TREND ANALYSIS
    # ================================================================

    monthly = Sale.get_monthly_revenue()
    if len(monthly) >= 6:
        revenues = [m['total_revenue'] for m in monthly]
        profits = [m['total_profit'] for m in monthly]

        rev_direction, rev_pct = _get_trend(revenues)
        prof_direction, prof_pct = _get_trend(profits)

        # Revenue trend
        if rev_direction == 'up':
            recs.append({
                'category': 'Growth Opportunity',
                'priority': 'info',
                'title': 'Revenue Trending Upward',
                'explanation': f'Revenue has grown {rev_pct:+.1f}% over recent periods. The business is on a growth trajectory.',
                'metric': f'{rev_pct:+.1f}%',
                'recommendation': 'Capitalize on growth momentum. Increase marketing spend and consider hiring additional sales staff.',
                'icon': 'bi-graph-up-arrow',
            })
        elif rev_direction == 'down':
            recs.append({
                'category': 'Risk Warning',
                'priority': 'high',
                'title': 'Revenue Declining',
                'explanation': f'Revenue has declined {rev_pct:.1f}% over recent periods. This requires immediate attention.',
                'metric': f'{rev_pct:.1f}%',
                'recommendation': 'Investigate root causes: market conditions, competition, pricing. Consider promotional campaigns to reverse the trend.',
                'icon': 'bi-graph-down-arrow',
            })

        # Profit vs Revenue divergence
        if rev_direction == 'up' and prof_direction == 'down':
            recs.append({
                'category': 'Risk Warning',
                'priority': 'high',
                'title': 'Revenue Up but Profit Down',
                'explanation': f'Revenue grew {rev_pct:+.1f}% but profit declined {prof_pct:.1f}%. Costs are rising faster than revenue.',
                'metric': f'Rev {rev_pct:+.1f}% / Prof {prof_pct:.1f}%',
                'recommendation': 'Urgently review cost structure. Identify which costs are increasing disproportionately. Consider operational efficiency improvements.',
                'icon': 'bi-exclamation-diamond',
            })

    # ================================================================
    # 5. TOP/LOW PRODUCT ANALYSIS
    # ================================================================

    top_products = Sale.get_top_products(5)
    if top_products:
        best_prod = top_products[0]
        recs.append({
            'category': 'Product Recommendation',
            'priority': 'info',
            'title': f'Best Seller: {best_prod["product_name"]}',
            'explanation': f'{best_prod["product_name"]} leads with ${best_prod["total_revenue"]:,.0f} revenue and {best_prod["total_sold"]} units sold.',
            'metric': f'${best_prod["total_revenue"]:,.0f}',
            'recommendation': f'Ensure {best_prod["product_name"]} is always in stock. Consider premium placement and bundling with complementary products.',
            'icon': 'bi-star',
        })

    # Product performance from analytics
    product_perf = Sale.get_product_performance()
    if product_perf:
        # Find products with negative margins
        neg_margin_prods = [p for p in product_perf if p['profit_margin'] < 0]
        if neg_margin_prods:
            worst_prod = neg_margin_prods[0]
            recs.append({
                'category': 'Inventory Recommendation',
                'priority': 'high',
                'title': f'Loss-Making Product: {worst_prod["product_name"]}',
                'explanation': f'{worst_prod["product_name"]} has a {worst_prod["profit_margin"]:.1f}% margin, generating losses on each sale.',
                'metric': f'{worst_prod["profit_margin"]:.1f}%',
                'recommendation': f'Immediately review pricing for {worst_prod["product_name"]}. Consider discontinuing if profitability cannot be improved.',
                'icon': 'bi-x-circle',
            })

        # Find products with high volume but low margin
        high_vol_low_margin = [p for p in product_perf if p['total_orders'] > 20 and 0 < p['profit_margin'] < 40]
        if high_vol_low_margin:
            prod = high_vol_low_margin[0]
            recs.append({
                'category': 'Sales Recommendation',
                'priority': 'medium',
                'title': f'Margin Improvement Opportunity: {prod["product_name"]}',
                'explanation': f'{prod["product_name"]} has {prod["total_orders"]} orders but only {prod["profit_margin"]:.1f}% margin. High volume, low return.',
                'metric': f'{prod["profit_margin"]:.1f}% margin',
                'recommendation': f'Consider a small price increase for {prod["product_name"]}. With high volume, even a small increase significantly improves profit.',
                'icon': 'bi-cash-stack',
            })

    # ================================================================
    # 6. CUSTOMER ANALYSIS
    # ================================================================

    segments = Sale.get_sales_by_customer_segment()
    if segments:
        # Find the most valuable segment
        top_seg = segments[0]
        recs.append({
            'category': 'Marketing Recommendation',
            'priority': 'info',
            'title': f'Top Customer Segment: {top_seg["segment"]}',
            'explanation': f'{top_seg["segment"]} customers generate ${top_seg["total_revenue"]:,.0f} across {top_seg["sale_count"]} sales.',
            'metric': f'${top_seg["total_revenue"]:,.0f}',
            'recommendation': f'Develop loyalty programs and targeted campaigns for {top_seg["segment"]} customers to increase retention and lifetime value.',
            'icon': 'bi-people',
        })

        # Customer concentration
        top_custs = Sale.get_top_customers(10)
        if top_custs:
            top10_rev = sum(c['total_revenue'] for c in top_custs)
            total_rev = Sale.get_total_revenue()
            concentration = (top10_rev / total_rev * 100) if total_rev > 0 else 0
            if concentration > 40:
                recs.append({
                    'category': 'Risk Warning',
                    'priority': 'medium',
                    'title': 'High Customer Concentration',
                    'explanation': f'Top 10 customers account for {concentration:.1f}% of total revenue. This creates dependency risk.',
                    'metric': f'{concentration:.1f}%',
                    'recommendation': 'Diversify customer base through new market acquisition. Reduce dependency on a small number of key accounts.',
                    'icon': 'bi-shield-exclamation',
                })

    # ================================================================
    # 7. SEASONAL PATTERNS
    # ================================================================

    if len(monthly) >= 12:
        # Compare Q4 to other quarters
        q4_revs = [m['total_revenue'] for m in monthly if m['month'].endswith(('10', '11', '12'))]
        other_revs = [m['total_revenue'] for m in monthly if not m['month'].endswith(('10', '11', '12'))]

        if q4_revs and other_revs:
            avg_q4 = sum(q4_revs) / len(q4_revs)
            avg_other = sum(other_revs) / len(other_revs)

            if avg_q4 > avg_other * 1.3:
                recs.append({
                    'category': 'Sales Recommendation',
                    'priority': 'info',
                    'title': 'Strong Q4 Seasonal Pattern',
                    'explanation': f'Q4 revenue averages ${avg_q4:,.0f}, which is {((avg_q4/avg_other)-1)*100:.0f}% higher than other quarters.',
                    'metric': f'${avg_q4:,.0f} avg Q4',
                    'recommendation': 'Plan inventory buildup 2 months before Q4. Prepare marketing campaigns early. Hire seasonal staff if needed.',
                    'icon': 'bi-calendar-event',
                })

    # ================================================================
    # 8. ANOMALY-BASED RECOMMENDATIONS
    # ================================================================

    try:
        from anomaly_detection import detect_anomalies
        anomaly_result = detect_anomalies(contamination=0.05)
        if anomaly_result and 'stats' in anomaly_result:
            stats = anomaly_result['stats']
            if stats['high_severity'] > 0:
                recs.append({
                    'category': 'Risk Warning',
                    'priority': 'high',
                    'title': f'{stats["high_severity"]} High-Severity Anomalies Detected',
                    'explanation': f'Isolation Forest detected {stats["high_severity"]} high-severity anomalies requiring investigation.',
                    'metric': f'{stats["high_severity"]} anomalies',
                    'recommendation': 'Review flagged transactions immediately. Check for data entry errors, fraud, or unusual market conditions.',
                    'icon': 'bi-exclamation-triangle',
                })
            if stats['anomaly_pct'] > 8:
                recs.append({
                    'category': 'Risk Warning',
                    'priority': 'medium',
                    'title': f'High Anomaly Rate ({stats["anomaly_pct"]}%)',
                    'explanation': f'{stats["anomaly_count"]} out of {stats["total_records"]} records are anomalous ({stats["anomaly_pct"]}%).',
                    'metric': f'{stats["anomaly_pct"]}%',
                    'recommendation': 'Review business processes and data quality. High anomaly rates may indicate systemic issues.',
                    'icon': 'bi-shield-check',
                })
    except Exception:
        pass  # Skip anomaly recommendations if detection fails

    # ================================================================
    # 9. DATA QUALITY RECOMMENDATIONS
    # ================================================================

    if total_orders < 100:
        recs.append({
            'category': 'Data Recommendation',
            'priority': 'medium',
            'title': 'Insufficient Data for Analysis',
            'explanation': f'Only {total_orders} records available. More data improves recommendation accuracy.',
            'metric': f'{total_orders} records',
            'recommendation': 'Upload additional historical data to improve the accuracy of predictions and recommendations.',
            'icon': 'bi-database',
        })

    # ================================================================
    # SORT BY PRIORITY
    # ================================================================

    priority_order = {'high': 0, 'medium': 1, 'info': 2}
    recs.sort(key=lambda r: priority_order.get(r['priority'], 3))

    # Add timestamps
    for rec in recs:
        rec['generated_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    return recs


def get_recommendation_summary():
    """Get a summary count of recommendations by category and priority."""
    recs = generate_recommendations()

    by_category = {}
    by_priority = {'high': 0, 'medium': 0, 'info': 0}

    for rec in recs:
        cat = rec['category']
        by_category[cat] = by_category.get(cat, 0) + 1
        by_priority[rec['priority']] = by_priority.get(rec['priority'], 0) + 1

    return {
        'total': len(recs),
        'by_category': [{'category': k, 'count': v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])],
        'by_priority': by_priority,
        'recommendations': recs,
    }
