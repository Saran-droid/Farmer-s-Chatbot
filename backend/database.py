"""
backend/database.py — Async SQLite database with users, conversations, and messages.
"""
import aiosqlite
from datetime import datetime
from config import DATABASE_URL


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Conversations table (a named chat thread per user)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        await db.commit()


# ── Users ──────────────────────────────────────────────────────────────────────

async def create_user(name: str, email: str, hashed_password: str) -> dict:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO users (name, email, hashed_password, created_at) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, now),
        )
        await db.commit()
        user_id = cursor.lastrowid
    return {"id": user_id, "name": name, "email": email}


async def get_user_by_email(email: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


# ── Conversations ──────────────────────────────────────────────────────────────

async def create_conversation(user_id: int, title: str = "New Chat") -> dict:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title, now, now),
        )
        await db.commit()
        conv_id = cur.lastrowid
    return {"id": conv_id, "title": title, "created_at": now, "updated_at": now}


async def get_conversations(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_conversation_by_id(conv_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_conversation(conv_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id)
        )
        await db.commit()


async def update_conversation_title(conv_id: int, title: str):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conv_id),
        )
        await db.commit()


async def touch_conversation(conv_id: int):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id))
        await db.commit()


# ── Messages ───────────────────────────────────────────────────────────────────

async def save_message(conv_id: int, role: str, content: str):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, now),
        )
        await db.commit()
    await touch_conversation(conv_id)


async def get_messages(conv_id: int, limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conv_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in reversed(rows)]


async def get_history_text(conv_id: int) -> str:
    rows = await get_messages(conv_id)
    return "\n".join(
        f"{'Farmer' if r['role'] == 'user' else 'Assistant'}: {r['content']}"
        for r in rows
    )


async def verify_conversation_owner(conv_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_URL) as db:
        async with db.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id)
        ) as cur:
            return await cur.fetchone() is not None
