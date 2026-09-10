import os
import sqlite3
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_photo,
    remove_user_photo,
    update_theme_preference,
)
from database.queries import (
    get_user_profile_info,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
    delete_expense as delete_expense_row,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]
MAX_EXPENSE_AMOUNT = 1_000_000
ALLOWED_THEMES = {"system", "light", "dark"}

ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_PHOTO_SIZE = 2 * 1024 * 1024  # 2 MB
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "profile_photos")


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user_by_id(user_id) if user_id else None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("All fields are required.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template("register.html")

        flash("Account created successfully. Please sign in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("All fields are required.")
            return render_template("login.html")

        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.")
            return render_template("login.html")

        session["user_id"] = user["id"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def _parse_date(value):
    """Return value if it's a well-formed YYYY-MM-DD date string, else None."""
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def _months_ago(d, months):
    """Return the date `months` calendar months before `d`, clamping the day
    to the target month's length (e.g. Jan 31 - 1 month -> Dec 31)."""
    month_index = d.month - 1 - months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    next_month_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    day = min(d.day, (next_month_first - date(year, month, 1)).days)
    return date(year, month, day)


def _resolve_date_filter(args, today):
    """Read/validate date_from and date_to from query args and figure out
    which preset (if any) is active. Returns (date_from, date_to,
    active_preset, presets)."""
    date_from = _parse_date(args.get("date_from"))
    date_to = _parse_date(args.get("date_to"))

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from, date_to = None, None

    presets = {
        "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": (_months_ago(today, 3).isoformat(), today.isoformat()),
        "last_6_months": (_months_ago(today, 6).isoformat(), today.isoformat()),
    }

    active_preset = "all_time"
    for name, (preset_from, preset_to) in presets.items():
        if date_from == preset_from and date_to == preset_to:
            active_preset = name
            break
    else:
        # none of the presets matched exactly -> a custom range, if any dates were given
        if date_from or date_to:
            active_preset = "custom"

    return date_from, date_to, active_preset, presets


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    date_from, date_to, active_preset, presets = _resolve_date_filter(
        request.args, date.today()
    )

    profile_info = get_user_profile_info(user_id)
    stats = get_summary_stats(user_id, date_from, date_to)
    transactions = get_recent_transactions(
        user_id, date_from=date_from, date_to=date_to
    )
    categories = get_category_breakdown(user_id, date_from, date_to)

    return render_template(
        "profile.html",
        member_since=profile_info["member_since"],
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
        active_preset=active_preset,
        presets=presets,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


def _render_expense_form(
    template, expense_id=None, amount="", category="", date_value="", description=""
):
    return render_template(
        template,
        expense_id=expense_id,
        categories=EXPENSE_CATEGORIES,
        amount=amount,
        category=category,
        date=date_value,
        description=description,
    )


def _validate_expense_form(form):
    """Validate raw add-expense form fields.

    Returns a dict with `error` (None if valid), the parsed `amount`
    (float) and `description` (str or None) ready for insertion, and the
    raw submitted strings (`amount_raw`/`description_raw`) needed to
    redisplay exactly what the user typed if validation fails.
    """
    amount_raw = form.get("amount", "")
    category = form.get("category", "")
    date_raw = form.get("date", "")
    description_raw = form.get("description", "")

    error = None
    amount = None
    if not amount_raw:
        error = "Amount is required."
    else:
        try:
            amount = float(amount_raw)
            if amount <= 0:
                error = "Amount must be greater than zero."
            elif amount > MAX_EXPENSE_AMOUNT:
                error = f"Amount must be {MAX_EXPENSE_AMOUNT:,} or less."
        except ValueError:
            error = "Amount must be a valid number."

    if not error and category not in EXPENSE_CATEGORIES:
        error = "Please choose a valid category."

    if not error and not _parse_date(date_raw):
        error = "Please enter a valid date."

    description = description_raw.strip() or None
    if not error and description and len(description) > 200:
        error = "Description must be 200 characters or fewer."

    return {
        "error": error,
        "amount": amount,
        "category": category,
        "date": date_raw,
        "description": description,
        "amount_raw": amount_raw,
        "description_raw": description_raw,
    }


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "GET":
        return _render_expense_form(
            "add_expense.html", date_value=date.today().isoformat()
        )

    result = _validate_expense_form(request.form)
    if result["error"]:
        flash(result["error"])
        return _render_expense_form(
            "add_expense.html",
            amount=result["amount_raw"],
            category=result["category"],
            date_value=result["date"],
            description=result["description_raw"],
        )

    insert_expense(
        user_id,
        result["amount"],
        result["category"],
        result["date"],
        result["description"],
    )
    flash("Expense added.")
    return redirect(url_for("profile"))


def _render_profile_photo_form():
    return render_template("profile_photo.html")


def _validate_photo_upload(uploaded_file):
    """Validate an uploaded profile photo.

    Returns a dict with `error` (None if valid) and `extension` (the
    lowercased, whitelisted file extension, or None if invalid).
    """
    if uploaded_file is None or uploaded_file.filename == "":
        return {"error": "Please choose a photo to upload.", "extension": None}

    safe_name = secure_filename(uploaded_file.filename)
    extension = os.path.splitext(safe_name)[1].lower()
    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        return {
            "error": "Only .jpg, .jpeg, and .png files are allowed.",
            "extension": None,
        }

    # Determine the real byte size ourselves — never trust the client's
    # Content-Type or Content-Length.
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)

    if size == 0:
        return {"error": "Uploaded file is empty.", "extension": None}
    if size > MAX_PHOTO_SIZE:
        return {"error": "Photo must be 2MB or smaller.", "extension": None}

    return {"error": None, "extension": extension}


def _delete_existing_photo_file(photo_filename):
    if not photo_filename:
        return
    path = os.path.join(UPLOAD_FOLDER, photo_filename)
    if os.path.exists(path):
        os.remove(path)


@app.route("/profile/photo", methods=["GET", "POST"])
def profile_photo():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "GET":
        return _render_profile_photo_form()

    uploaded_file = request.files.get("photo")
    result = _validate_photo_upload(uploaded_file)
    if result["error"]:
        flash(result["error"])
        return _render_profile_photo_form()

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    current_user = get_user_by_id(user_id)
    old_filename = current_user["photo_filename"]
    new_filename = f"user_{user_id}{result['extension']}"

    if old_filename and old_filename != new_filename:
        _delete_existing_photo_file(old_filename)

    uploaded_file.save(os.path.join(UPLOAD_FOLDER, new_filename))
    update_user_photo(user_id, new_filename)

    flash("Profile photo updated.")
    return redirect(url_for("profile"))


@app.route("/profile/photo/remove", methods=["POST"])
def remove_profile_photo():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    current_user = get_user_by_id(user_id)
    _delete_existing_photo_file(current_user["photo_filename"])
    remove_user_photo(user_id)

    flash("Profile photo removed.")
    return redirect(url_for("profile"))


def _safe_next_path(next_path):
    """Only allow redirecting back to a same-site path, never an external URL."""
    if (
        next_path
        and next_path.startswith("/")
        and not next_path.startswith("//")
        and "\\" not in next_path
    ):
        return next_path
    return url_for("profile")


@app.route("/profile/appearance", methods=["POST"])
def update_appearance():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    next_path = _safe_next_path(request.form.get("next"))

    theme = request.form.get("theme")
    if theme not in ALLOWED_THEMES:
        flash("Please choose a valid appearance option.")
        return redirect(next_path)

    update_theme_preference(user_id, theme)
    return redirect(next_path)


def _render_edit_expense_get(expense_id, expense):
    return _render_expense_form(
        "edit_expense.html",
        expense_id=expense_id,
        amount=expense["amount"],
        category=expense["category"],
        date_value=expense["date"],
        description=expense["description"] or "",
    )


def _handle_edit_expense_post(expense_id, user_id, form):
    result = _validate_expense_form(form)
    if result["error"]:
        flash(result["error"])
        return _render_expense_form(
            "edit_expense.html",
            expense_id=expense_id,
            amount=result["amount_raw"],
            category=result["category"],
            date_value=result["date"],
            description=result["description_raw"],
        )

    update_expense(
        expense_id,
        user_id,
        result["amount"],
        result["category"],
        result["date"],
        result["description"],
    )
    flash("Expense updated.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        return _render_edit_expense_get(id, expense)

    return _handle_edit_expense_post(id, user_id, request.form)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    delete_expense_row(id, user_id)
    flash("Expense deleted.")
    return redirect(url_for("profile"))


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
