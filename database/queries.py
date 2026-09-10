"""Query helpers for the profile page. No Flask imports — pure data access."""

from database.db import get_db


def _date_range_clause(date_from, date_to):
    """Build the WHERE fragment and params for an optional date range.
    Filtering only applies when both bounds are given; values are always
    returned for use as `?` parameters, never interpolated into SQL."""
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", [date_from, date_to]
    return "", []


def get_user_profile_info(user_id):
    """Return dict with name, email, member_since (formatted 'Month YYYY')."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user is None:
        return None

    created_at = user["created_at"]
    date_part = created_at.split(" ")[0]
    year, month, _ = date_part.split("-")
    month_name = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ][int(month) - 1]

    return {
        "name": user["name"],
        "email": user["email"],
        "member_since": f"{month_name} {year}",
    }


# --- Subagent 1: Transaction history ---
def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conn = get_db()
    date_clause, date_params = _date_range_clause(date_from, date_to)
    query = (
        "SELECT id, date, description, category, amount "
        "FROM expenses "
        "WHERE user_id = ?" + date_clause + " "
        "ORDER BY date DESC LIMIT ?"
    )
    params = [user_id] + date_params + [limit]
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


# --- Subagent 2: Summary stats ---
def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    date_clause, date_params = _date_range_clause(date_from, date_to)
    where = "WHERE user_id = ?" + date_clause
    params = [user_id] + date_params
    totals = conn.execute(
        "SELECT SUM(amount) AS total, COUNT(*) AS count FROM expenses " + where,
        params,
    ).fetchone()
    top = conn.execute(
        "SELECT category, SUM(amount) as total "
        "FROM expenses " + where + " "
        "GROUP BY category "
        "ORDER BY total DESC "
        "LIMIT 1",
        params,
    ).fetchone()
    conn.close()

    return {
        "total_spent": float(totals["total"]) if totals["total"] is not None else 0,
        "transaction_count": totals["count"] or 0,
        "top_category": top["category"] if top is not None else "—",
    }


# --- Subagent 3: Category breakdown ---
def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    date_clause, date_params = _date_range_clause(date_from, date_to)
    where = "WHERE user_id = ?" + date_clause
    params = [user_id] + date_params
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total "
        "FROM expenses " + where + " "
        "GROUP BY category "
        "ORDER BY total DESC",
        params,
    ).fetchall()
    conn.close()

    if not rows:
        return []

    overall_total = sum(row["total"] for row in rows)
    if overall_total == 0:
        return []

    breakdown = [
        {
            "name": row["category"],
            "total": float(row["total"]),
            "percent": round(row["total"] / overall_total * 100),
        }
        for row in rows
    ]

    remainder = 100 - sum(cat["percent"] for cat in breakdown)
    if remainder != 0:
        largest = max(breakdown, key=lambda cat: cat["total"])
        largest["percent"] += remainder

    return breakdown


def insert_expense(user_id, amount, category, date, description):
    """Insert a new expense row. description may be None."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    """Return the expense row if it exists and belongs to user_id, else None."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    conn.close()
    return row


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update an expense's editable fields. Scoped to user_id so a mismatched
    owner updates zero rows instead of another user's expense."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_expense(expense_id, user_id):
    """Delete an expense scoped to user_id so a mismatched owner deletes
    zero rows instead of another user's expense."""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()
