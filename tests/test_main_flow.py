import pytest_asyncio
import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from main import XianyuLive
from XianyuAgent import XianyuReplyBot
from loguru import logger

# Use pytest mark to run all tests asynchronously
pytestmark = pytest.mark.asyncio

# --- Test Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked XianyuReplyBot."""
    bot = MagicMock(spec=XianyuReplyBot)
    bot.generate_reply = AsyncMock(return_value="mocked reply")
    bot.last_intent = "other"
    return bot

@pytest_asyncio.fixture
async def mock_xianyu_live(mock_bot):
    """Fixture for a mocked XianyuLive instance with its dependencies patched."""
    seller_id = "seller_123"  # Define a consistent seller ID
    cookies_str = f"unb={seller_id}"

    with patch('builtins.open', new_callable=MagicMock), \
         patch('json.load') as mock_json_load, \
         patch('main.load_dotenv'),          patch('main.XianyuApis', MagicMock),          patch('main.ChatContextManager', MagicMock):
        
        mock_json_load.return_value = {
            "api_endpoints": {"websocket_url": "ws://fake.url"},
            "behavior_tuning": {
                "delays": {
                    "reply_min_secs": 0.1,
                    "reply_max_secs": 0.2
                }
            },
            "message_templates": {
                "text_content": {"text": {"text": ""}},
                "send_message": {
                    "headers": {},
                    "body": [{"content": {"custom": {}}}, {}]
                }
            }
        }

        live = XianyuLive(cookies_str=cookies_str, bot=mock_bot, config=mock_json_load.return_value)
        live.context_manager._init_db = AsyncMock()  # Mock the async method
        await live.initialize()  # Initialize the object
        
        # Manually set up mocks post-init
        live.context_manager = MagicMock()
        live.context_manager.get_item_info = AsyncMock(return_value=None)
        live.context_manager.save_item_info = AsyncMock()
        live.context_manager.get_context_for_item = AsyncMock(return_value=[])
        live.context_manager.add_message_by_chat = AsyncMock()
        live.context_manager.update_last_item_id = AsyncMock()
        live.context_manager.get_last_item_id = AsyncMock(return_value=None)
        
        live.xianyu.get_item_info = MagicMock(return_value={
            'data': {'itemDO': {'desc': 'Test Item', 'soldPrice': '100'}}
        })
        live.send_msg = AsyncMock()
        
        # Ensure myid is correctly set from the cookie
        assert live.myid == seller_id
        
        return live



# --- Helper Functions ---

def create_test_message(sender_id="buyer_888"):
    """Creates a fake websocket message that forces the decryption path."""
    return {
        "body": {
            "syncPushPackage": {
                "data": [{"data": "this-is-not-valid-base64"}]
            }
        },
        "headers": {"mid": "fake_mid"}
    }

def get_decrypted_payload(sender_id="buyer_888"):
    """Generates the JSON payload that the mocked decrypt function will return."""
    current_timestamp = str(int(time.time() * 1000))
    return f'''
    {{
        "1": {{
            "2": "777@goofish",
            "5": "{current_timestamp}",
            "10": {{
                "reminderContent": "Hello there",
                "reminderTitle": "some_user",
                "reminderUrl": "https://www.goofish.com/item?itemId=666&userId=888",
                "senderUserId": "{sender_id}"
            }}
        }}
    }}
    '''

# --- Test Cases ---

async def test_handle_message_from_buyer_triggers_reply_and_delay(mocker, mock_xianyu_live):
    """Verify that a message from a buyer triggers the full reply logic, including the delay."""
    # Arrange
    buyer_id = "buyer_888"
    # Ensure the sender is NOT the seller
    assert buyer_id != mock_xianyu_live.myid

    mock_decrypt = mocker.patch('main.decrypt', return_value=get_decrypted_payload(sender_id=buyer_id))
    mock_sleep = mocker.patch('asyncio.sleep', new_callable=AsyncMock)
    mock_websocket = AsyncMock()
    fake_message = create_test_message(sender_id=buyer_id)

    # Act
    await mock_xianyu_live.handle_message(fake_message, mock_websocket)

    # Assert
    mock_decrypt.assert_called_once()
    mock_xianyu_live.bot.generate_reply.assert_called_once()
    mock_sleep.assert_called_once()
    mock_xianyu_live.send_msg.assert_called_once()
    logger.info("Test passed: Message from buyer correctly triggered reply and delay.")

async def test_handle_message_from_seller_is_ignored(mocker, mock_xianyu_live):
    """Verify that a message from the seller is ignored and does not trigger the reply logic."""
    # Arrange
    seller_id = mock_xianyu_live.myid # Message is from the seller

    mock_decrypt = mocker.patch('main.decrypt', return_value=get_decrypted_payload(sender_id=seller_id))
    mock_sleep = mocker.patch('asyncio.sleep', new_callable=AsyncMock)
    mock_websocket = AsyncMock()
    fake_message = create_test_message(sender_id=seller_id)

    # Act
    await mock_xianyu_live.handle_message(fake_message, mock_websocket)

    # Assert
    mock_decrypt.assert_called_once() # Decryption still happens
    mock_xianyu_live.bot.generate_reply.assert_not_called() # But the bot should not be called
    mock_sleep.assert_not_called() # And no delay should occur
    mock_xianyu_live.send_msg.assert_not_called()
    logger.info("Test passed: Message from seller was correctly ignored.")