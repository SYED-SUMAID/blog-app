PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    bio TEXT
);

CREATE TABLE IF NOT EXISTS blog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    FOREIGN KEY (author_id) REFERENCES user(id) ON DELETE CASCADE
);

-- 2. New Tables for Iteration 2
CREATE TABLE IF NOT EXISTS comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    commenter_id INTEGER NOT NULL,
    blog_id INTEGER NOT NULL,
    FOREIGN KEY (commenter_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (blog_id) REFERENCES blog(id) ON DELETE CASCADE
);

-- Composite Primary Key: Prevents duplicate likes from the same user
CREATE TABLE IF NOT EXISTS liketracker (
    liker_id INTEGER NOT NULL,
    blog_id INTEGER NOT NULL,
    PRIMARY KEY (liker_id, blog_id),
    FOREIGN KEY (liker_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (blog_id) REFERENCES blog(id) ON DELETE CASCADE
);

-- Composite Primary Key: Prevents duplicate follows
CREATE TABLE IF NOT EXISTS userfollow (
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    PRIMARY KEY (follower_id, followed_id),
    FOREIGN KEY (follower_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (followed_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Query Optimization Indexes
CREATE INDEX IF NOT EXISTS ix_comment_blog_id ON comment(blog_id);
CREATE INDEX IF NOT EXISTS ix_liketracker_blog_id ON liketracker(blog_id);
CREATE INDEX IF NOT EXISTS ix_userfollow_followed ON userfollow(followed_id);