DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS task;
DROP TABLE IF EXISTS category;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_blocked INTEGER NOT NULL DEFAULT 0,
    avatar TEXT
);

CREATE TABLE category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    FOREIGN KEY (created_by) REFERENCES user (id)
);

CREATE TABLE task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished TIMESTAMP,
    assigned_to INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    category_id INTEGER,
    FOREIGN KEY (assigned_to) REFERENCES user (id),
    FOREIGN KEY (created_by) REFERENCES user (id),
    FOREIGN KEY (category_id) REFERENCES category (id)
);

-- Thêm các category mặc định khi có user mới được tạo
CREATE TRIGGER create_default_categories AFTER INSERT ON user
BEGIN
    INSERT INTO category (name, color, created_by) VALUES 
    ('Loại 1', '#FF6B6B', NEW.id),
    ('Loại 2', '#4ECDC4', NEW.id),
    ('Loại 3', '#45B7D1', NEW.id);
END;