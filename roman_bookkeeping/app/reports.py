from collections import defaultdict


def get_profit_and_loss_rows(db, start_date=None, end_date=None):
    params = []
    invoice_filter = ""
    expense_filter = ""

    if start_date:
        invoice_filter += " AND invoice_date >= ?"
        expense_filter += " AND expense_date >= ?"
        params.append(start_date)

    if end_date:
        invoice_filter += " AND invoice_date <= ?"
        expense_filter += " AND expense_date <= ?"
        params.append(end_date)

    # Keep logic simple for v1:
    # - Revenue uses imported invoice totals.
    # - Direct costs and overhead split by expense_type.
    revenue = db.execute(
        f"""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM imported_invoices
        WHERE 1 = 1 {invoice_filter}
        """,
        params,
    ).fetchone()["total"]

    expense_params = []
    if start_date:
        expense_params.append(start_date)
    if end_date:
        expense_params.append(end_date)

    direct_cost = db.execute(
        f"""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE expense_type = 'direct_cost' {expense_filter}
        """,
        expense_params,
    ).fetchone()["total"]

    overhead = db.execute(
        f"""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE expense_type = 'overhead' {expense_filter}
        """,
        expense_params,
    ).fetchone()["total"]

    gross_profit = revenue - direct_cost
    net_profit = gross_profit - overhead

    return {
        "revenue": revenue,
        "direct_cost": direct_cost,
        "gross_profit": gross_profit,
        "overhead": overhead,
        "net_profit": net_profit,
    }


def get_job_profitability_rows(db):
    revenue_rows = db.execute(
        """
        SELECT job_id, COALESCE(SUM(total_amount), 0) AS revenue
        FROM imported_invoices
        WHERE job_id IS NOT NULL AND job_id <> ''
        GROUP BY job_id
        """
    ).fetchall()

    cost_rows = db.execute(
        """
        SELECT job_id, COALESCE(SUM(amount), 0) AS direct_cost
        FROM expenses
        WHERE expense_type = 'direct_cost'
          AND job_id IS NOT NULL
          AND job_id <> ''
        GROUP BY job_id
        """
    ).fetchall()

    revenue_map = {row["job_id"]: row["revenue"] for row in revenue_rows}
    cost_map = {row["job_id"]: row["direct_cost"] for row in cost_rows}

    all_jobs = sorted(set(revenue_map.keys()) | set(cost_map.keys()))

    output = []
    for job_id in all_jobs:
        revenue = revenue_map.get(job_id, 0)
        direct_cost = cost_map.get(job_id, 0)
        gross_profit = revenue - direct_cost
        margin_pct = (gross_profit / revenue * 100) if revenue else None
        output.append(
            {
                "job_id": job_id,
                "revenue": revenue,
                "direct_cost": direct_cost,
                "gross_profit": gross_profit,
                "margin_pct": margin_pct,
            }
        )

    return output
