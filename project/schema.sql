CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL
);

CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entry_date DATE NOT NULL,
    content TEXT NOT NULL,
    mood INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE habit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL,
    log_date DATE NOT NULL,
    completed INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (habit_id) REFERENCES habits(id),
    UNIQUE (habit_id, log_date)
);

CREATE INDEX idx_entries_user_date ON entries (user_id, entry_date);
CREATE INDEX idx_habit_logs_habit_date ON habit_logs (habit_id, log_date);
