import os
from datetime import datetime
from loguru import logger

LOG_DIR = "logs"

def ensure_log_dir():
    """确保日志目录存在"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logger.info(f"Created log directory: {LOG_DIR}")

def log_daily_event(event_type: str, item_id: str, user_name: str, details: str = ""):
    """记录每日的关键业务事件（如新咨询、成功销售）"""
    ensure_log_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"stats_{today}.txt")
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] [{event_type.upper()}] - 商品ID: {item_id}, 用户: {user_name}, 详情: {details}\n"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to log daily event: {e}")

def log_daily_conversation(chat_id: str, user_name: str, item_id: str, user_message: str, bot_reply: str):
    """记录完整的对话回合，用于复盘和学习"""
    ensure_log_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"conversations_{today}.txt")
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = (
        f"==================== {timestamp} | 会话ID: {chat_id} | 商品ID: {item_id} ====================\n"
        f"【用户】 {user_name}: {user_message}\n"
        f"【AI助手】: {bot_reply}\n"
        f"====================================================================================================\n\n"
    )
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to log daily conversation: {e}")
