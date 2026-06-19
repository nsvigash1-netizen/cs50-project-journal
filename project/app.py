from datetime import date, timedelta

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///journal.db")

# Mood scale used throughout the app: 1 (worst) to 5 (best)
MOODS = {1: "😞 Rough", 2: "😕 Meh", 3: "🙂 Okay", 4: "😄 Good", 5: "🤩 Great"}


@app.after_request
def after_request(response):
    """Ensure responses aren't cached."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)
        if not password:
            return apology("must provide password", 400)
        if password != confirmation:
            return apology("passwords must match", 400)

        try:
            user_id = db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username,
                generate_password_hash(password),
            )
        except Exception:
            return apology("username already taken", 400)

        session["user_id"] = user_id
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("must provide username and password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password", 400)

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    today = date.today().isoformat()

    habits = db.execute("SELECT * FROM habits WHERE user_id = ? ORDER BY name", user_id)

    logs_today = db.execute(
        "SELECT habit_id FROM habit_logs WHERE log_date = ? AND habit_id IN "
        "(SELECT id FROM habits WHERE user_id = ?)",
        today,
        user_id,
    )
    done_today = {row["habit_id"] for row in logs_today}

    recent_entries = db.execute(
        "SELECT * FROM entries WHERE user_id = ? ORDER BY entry_date DESC, created_at DESC LIMIT 5",
        user_id,
    )

    return render_template(
        "index.html",
        habits=habits,
        done_today=done_today,
        today=today,
        recent_entries=recent_entries,
        moods=MOODS,
    )


@app.route("/journal")
@login_required
def journal():
    user_id = session["user_id"]
    mood_filter = request.args.get("mood")

    query = "SELECT * FROM entries WHERE user_id = ?"
    params = [user_id]

    if mood_filter and mood_filter.isdigit() and int(mood_filter) in MOODS:
        query += " AND mood = ?"
        params.append(int(mood_filter))

    query += " ORDER BY entry_date DESC, created_at DESC"
    entries = db.execute(query, *params)

    return render_template("journal.html", entries=entries, moods=MOODS, mood_filter=mood_filter)


@app.route("/journal/new", methods=["GET", "POST"])
@login_required
def new_entry():
    if request.method == "POST":
        content = request.form.get("content")
        mood = request.form.get("mood")
        entry_date = request.form.get("entry_date") or date.today().isoformat()

        if not content:
            return apology("entry can't be empty", 400)
        if not mood or not mood.isdigit() or int(mood) not in MOODS:
            return apology("must select a valid mood", 400)

        db.execute(
            "INSERT INTO entries (user_id, entry_date, content, mood) VALUES (?, ?, ?, ?)",
            session["user_id"],
            entry_date,
            content,
            int(mood),
        )
        flash("Entry saved!")
        return redirect("/journal")

    return render_template("new_entry.html", moods=MOODS, today=date.today().isoformat())


@app.route("/journal/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id):
    entry = db.execute(
        "SELECT * FROM entries WHERE id = ? AND user_id = ?", entry_id, session["user_id"]
    )
    if not entry:
        return apology("entry not found", 404)
    entry = entry[0]

    if request.method == "POST":
        content = request.form.get("content")
        mood = request.form.get("mood")
        entry_date = request.form.get("entry_date")

        if not content:
            return apology("entry can't be empty", 400)
        if not mood or not mood.isdigit() or int(mood) not in MOODS:
            return apology("must select a valid mood", 400)
        if not entry_date:
            return apology("must provide a date", 400)

        db.execute(
            "UPDATE entries SET content = ?, mood = ?, entry_date = ? WHERE id = ? AND user_id = ?",
            content,
            int(mood),
            entry_date,
            entry_id,
            session["user_id"],
        )
        flash("Entry updated!")
        return redirect("/journal")

    return render_template("edit_entry.html", entry=entry, moods=MOODS)


@app.route("/journal/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id):
    db.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", entry_id, session["user_id"])
    flash("Entry deleted.")
    return redirect("/journal")


@app.route("/habits", methods=["GET", "POST"])
@login_required
def habits():
    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            return apology("must provide a habit name", 400)
        db.execute("INSERT INTO habits (user_id, name) VALUES (?, ?)", user_id, name)
        flash("Habit added!")
        return redirect("/habits")

    habit_rows = db.execute("SELECT * FROM habits WHERE user_id = ? ORDER BY name", user_id)
    return render_template("habits.html", habits=habit_rows)


@app.route("/habits/<int:habit_id>/delete", methods=["POST"])
@login_required
def delete_habit(habit_id):
    habit = db.execute(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?", habit_id, session["user_id"]
    )
    if not habit:
        return apology("habit not found", 404)

    db.execute("DELETE FROM habit_logs WHERE habit_id = ?", habit_id)
    db.execute("DELETE FROM habits WHERE id = ?", habit_id)
    flash("Habit removed.")
    return redirect("/habits")


@app.route("/habits/<int:habit_id>/toggle", methods=["POST"])
@login_required
def toggle_habit(habit_id):
    user_id = session["user_id"]
    today = date.today().isoformat()

    habit = db.execute("SELECT * FROM habits WHERE id = ? AND user_id = ?", habit_id, user_id)
    if not habit:
        return apology("habit not found", 404)

    existing = db.execute(
        "SELECT * FROM habit_logs WHERE habit_id = ? AND log_date = ?", habit_id, today
    )
    if existing:
        db.execute("DELETE FROM habit_logs WHERE habit_id = ? AND log_date = ?", habit_id, today)
    else:
        db.execute(
            "INSERT INTO habit_logs (habit_id, log_date, completed) VALUES (?, ?, 1)",
            habit_id,
            today,
        )

    return redirect(request.referrer or "/")


@app.route("/stats")
@login_required
def stats():
    user_id = session["user_id"]

    mood_counts = db.execute(
        "SELECT mood, COUNT(*) AS count FROM entries WHERE user_id = ? GROUP BY mood", user_id
    )
    mood_summary = {row["mood"]: row["count"] for row in mood_counts}

    total_entries = db.execute(
        "SELECT COUNT(*) AS count FROM entries WHERE user_id = ?", user_id
    )[0]["count"]

    habit_rows = db.execute("SELECT * FROM habits WHERE user_id = ?", user_id)
    habit_stats = []
    since = (date.today() - timedelta(days=29)).isoformat()

    for habit in habit_rows:
        completed = db.execute(
            "SELECT COUNT(*) AS count FROM habit_logs WHERE habit_id = ? AND log_date >= ?",
            habit["id"],
            since,
        )[0]["count"]
        habit_stats.append(
            {"name": habit["name"], "completed": completed, "rate": round(completed / 30 * 100)}
        )

    return render_template(
        "stats.html",
        mood_summary=mood_summary,
        moods=MOODS,
        total_entries=total_entries,
        habit_stats=habit_stats,
    )


if __name__ == "__main__":
    app.run(debug=True)
