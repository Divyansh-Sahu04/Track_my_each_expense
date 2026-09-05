"""Query helpers for the profile page. No Flask imports — pure data access."""

from database.db import get_db


def get_user_profile_info(user_id):
    """Return dict with name, email, member_since (formatted 'Month YYYY')."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if user is None:
        return None

    created_at = user["created_at"]
    date_part = created_at.split(" ")[0]
    year, month, _ = date_part.split("-")
    month_name = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ][int(month) - 1]

    return {
        "name": user["name"],
        "email": user["email"],
        "member_since": f"{month_name} {year}",
    }


# --- Subagent 1: Transaction history ---
def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


# --- Subagent 2: Summary stats ---
def get_summary_stats(user_id):
    conn = get_db()
    totals = conn.execute(
        "SELECT SUM(amount) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    top = conn.execute(
        """
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    return {
        "total_spent": float(totals["total"]) if totals["total"] is not None else 0,
        "transaction_count": totals["count"] or 0,
        "top_category": top["category"] if top is not None else "—",
    }


# --- Subagent 3: Category breakdown ---
def get_category_breakdown(user_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (user_id,),
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
