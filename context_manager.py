import aiosqlite as sqlite3
import os
import json
from datetime import datetime
from loguru import logger


class ChatContextManager:
    """
    聊天上下文管理器

    负责存储和检索用户与商品之间的对话历史，使用SQLite数据库进行持久化存储。
    支持按会话ID检索对话历史，以及议价次数统计。
    """

    def __init__(self, max_history=100, db_path="data/chat_history.db"):
        """
        初始化聊天上下文管理器

        Args:
            max_history: 每个对话保留的最大消息数
            db_path: SQLite数据库文件路径
        """
        self.max_history = max_history
        self.db_path = db_path
        # 在异步环境中，我们不在__init__中直接连接数据库，
        # 而是在需要时异步连接，或者创建一个异步的初始化方法。

    async def _init_db(self):
        """初始化数据库表结构"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            # 创建消息表
            await cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                chat_id TEXT
            )
            """
            )

            # 检查是否需要添加chat_id字段（兼容旧数据库）
            await cursor.execute("PRAGMA table_info(messages)")
            columns = [column[1] for column in await cursor.fetchall()]
            if "chat_id" not in columns:
                await cursor.execute("ALTER TABLE messages ADD COLUMN chat_id TEXT")
                logger.info("已为messages表添加chat_id字段")

            # 创建索引以加速查询
            await cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_user_item ON messages (user_id, item_id)
            """
            )

            await cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_chat_id ON messages (chat_id)
            """
            )

            await cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)
            """
            )

            # 创建基于会话和商品的议价次数表
            await cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS chat_item_bargain_counts (
                chat_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, item_id)
            )
            """
            )

            # 创建商品信息表
            await cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS items (
                item_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                price REAL,
                description TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # 创建会话状态表，用于跟踪每个会话最后交互的商品
            await cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS chat_session_state (
                chat_id TEXT PRIMARY KEY,
                last_item_id TEXT NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # 创建网络搜索缓存表
            await cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT PRIMARY KEY,
                results TEXT NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            await conn.commit()
            logger.info(f"聊天历史数据库初始化完成: {self.db_path}")

    async def save_item_info(self, item_id, item_data):
        """
        保存商品信息到数据库

        Args:
            item_id: 商品ID
            item_data: 商品信息字典
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            try:
                # 从商品数据中提取有用信息
                price = float(item_data.get("soldPrice", 0))
                description = item_data.get("desc", "")

                # 将整个商品数据转换为JSON字符串
                data_json = json.dumps(item_data, ensure_ascii=False)

                await cursor.execute(
                    """
                    INSERT INTO items (item_id, data, price, description, last_updated) 
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(item_id) 
                    DO UPDATE SET data = ?, price = ?, description = ?, last_updated = ?
                    """,
                    (
                        item_id,
                        data_json,
                        price,
                        description,
                        datetime.now().isoformat(),
                        data_json,
                        price,
                        description,
                        datetime.now().isoformat(),
                    ),
                )

                await conn.commit()
                logger.debug(f"商品信息已保存: {item_id}")
            except Exception as e:
                logger.error(f"保存商品信息时出错: {e}")
                await conn.rollback()

    async def get_item_info(self, item_id):
        """
        从数据库获取商品信息

        Args:
            item_id: 商品ID

        Returns:
            dict: 商品信息字典，如果不存在返回None
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            try:
                await cursor.execute("SELECT data FROM items WHERE item_id = ?", (item_id,))

                result = await cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return None
            except Exception as e:
                logger.error(f"获取商品信息时出错: {e}")
                return None

    async def add_message_by_chat(self, chat_id, user_id, item_id, role, content):
        """
        基于会话ID添加新消息到对话历史

        Args:
            chat_id: 会话ID
            user_id: 用户ID (用户消息存真实user_id，助手消息存卖家ID)
            item_id: 商品ID
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            try:
                # 插入新消息，使用chat_id作为额外标识
                await cursor.execute(
                    "INSERT INTO messages (user_id, item_id, role, content, timestamp, chat_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, item_id, role, content, datetime.now().isoformat(), chat_id),
                )

                # 检查是否需要清理旧消息（基于chat_id）
                await cursor.execute(
                    """
                    SELECT id FROM messages 
                    WHERE chat_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?, 1
                    """,
                    (chat_id, self.max_history),
                )

                oldest_to_keep = await cursor.fetchone()
                if oldest_to_keep:
                    await cursor.execute(
                        "DELETE FROM messages WHERE chat_id = ? AND id < ?",
                        (chat_id, oldest_to_keep[0]),
                    )

                await conn.commit()
            except Exception as e:
                logger.error(f"添加消息到数据库时出错: {e}")
                await conn.rollback()

    async def get_context_for_item(self, chat_id, item_id):
        """
        基于会话ID获取对话历史

        Args:
            chat_id: 会话ID

        Returns:
            list: 包含对话历史的列表
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            try:
                # 注意：这里的查询逻辑可能需要根据实际需求调整
                # 例如，是否只看当前商品的对话，还是包含一些通用对话
                await cursor.execute(
                    """
                    SELECT role, content FROM messages 
                    WHERE chat_id = ? AND item_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (chat_id, item_id, self.max_history),
                )

                messages = [
                    {"role": role, "content": content}
                    for role, content in await cursor.fetchall()
                ]

                # 获取特定商品的议价次数并添加到上下文中
                bargain_count = await self.get_bargain_count_for_item(chat_id, item_id)
                if bargain_count > 0:
                    messages.append(
                        {"role": "system", "content": f"关于此商品的议价次数: {bargain_count}"}
                    )

            except Exception as e:
                logger.error(f"获取对话历史时出错: {e}")
                messages = []

        return messages

    async def increment_bargain_count_for_item(self, chat_id, item_id):
        """
        基于会话ID增加议价次数

        Args:
            chat_id: 会话ID
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            try:
                # 使用UPSERT语法直接基于(chat_id, item_id)增加议价次数
                await cursor.execute(
                    """
                    INSERT INTO chat_item_bargain_counts (chat_id, item_id, count, last_updated)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(chat_id, item_id) 
                    DO UPDATE SET count = count + 1, last_updated = ?
                    """,
                    (chat_id, item_id, datetime.now().isoformat(), datetime.now().isoformat()),
                )

                await conn.commit()
                logger.debug(f"会话 {chat_id} 对商品 {item_id} 的议价次数已增加")
            except Exception as e:
                logger.error(f"增加议价次数时出错: {e}")
                await conn.rollback()

    async def get_bargain_count_for_item(self, chat_id, item_id):
        """
        基于会话ID获取议价次数

        Args:
            chat_id: 会话ID

        Returns:
            int: 议价次数
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()

            try:
                await cursor.execute(
                    "SELECT count FROM chat_item_bargain_counts WHERE chat_id = ? AND item_id = ?", (chat_id, item_id)
                )

                result = await cursor.fetchone()
                return result[0] if result else 0
            except Exception as e:
                logger.error(f"获取议价次数时出错: {e}")
                return 0

    async def get_last_item_id(self, chat_id):
        """
        获取会话最后一次交互的商品ID

        Args:
            chat_id: 会话ID

        Returns:
            str: 商品ID，如果不存在则返回None
        """
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            try:
                await cursor.execute(
                    "SELECT last_item_id FROM chat_session_state WHERE chat_id = ?", (chat_id,)
                )
                result = await cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                logger.error(f"获取最后商品ID时出错: {e}")
                return None

    async def update_last_item_id(self, chat_id, item_id):
        """
        更新会话最后一次交互的商品ID

        Args:
            chat_id: 会话ID
            item_id: 新的商品ID
        """
        async with sqlite3.connect(self.db_path) as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO chat_session_state (chat_id, last_item_id, last_updated)
                    VALUES (?, ?, ?)
                    ON CONFLICT(chat_id) 
                    DO UPDATE SET last_item_id = ?, last_updated = ?
                    """,
                    (chat_id, item_id, datetime.now().isoformat(), item_id, datetime.now().isoformat()),
                )
                await conn.commit()
            except Exception as e:
                logger.error(f"更新最后商品ID时出错: {e}")
                await conn.rollback()

    async def get_search_cache(self, query):
        """获取网络搜索缓存"""
        async with sqlite3.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT results FROM search_cache WHERE query = ?", (query,))
            result = await cursor.fetchone()
            return result[0] if result else None

    async def save_search_cache(self, query, results):
        """保存网络搜索缓存"""
        async with sqlite3.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO search_cache (query, results, last_updated) VALUES (?, ?, ?)",
                (query, results, datetime.now().isoformat()),
            )
            await conn.commit()
