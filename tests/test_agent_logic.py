import os
import pytest
from dotenv import load_dotenv
from loguru import logger
from unittest.mock import patch, AsyncMock
import json

from XianyuAgent import XianyuReplyBot

# 在所有测试之前加载一次环境变量
@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        logger.info("Loaded API_KEY for pytest session.")

@pytest.fixture(scope="module")
def bot():
    """Pytest fixture to initialize the XianyuReplyBot once per test module."""
    try:
        return XianyuReplyBot()
    except ValueError as e:
        pytest.fail(f"Failed to initialize XianyuReplyBot: {e}")

@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", [
    {
        "name": "议价意图测试",
        "user_msg": "老板，这台功放800块钱卖不卖？",
        "item_desc": "这是一台九成新的雅马哈功放机，音质出色，功能完好。当前商品售卖价格为:1000",
        "context": [
            {"role": "user", "content": "你好，功放还在吗？"},
            {"role": "assistant", "content": "在的，亲。"}
        ]
    },
    {
        "name": "技术问题测试",
        "user_msg": "请问这台机器的输出功率和支持的接口有哪些？给个详细参数。",
        "item_desc": "这是一台九成新的雅马哈功放机，音质出色，功能完好。当前商品售卖价格为:1000",
        "context": []
    },
    {
        "name": "默认闲聊测试",
        "user_msg": "你吃饭了吗？",
        "item_desc": "这是一台九成新的雅马ха功放机，音质出色，功能完好。当前商品售卖价格为:1000",
        "context": []
    }
])
async def test_agent_intents(bot, test_case):
    """Parameterized test for different agent intents."""
    logger.info(f"--- Running test: {test_case['name']} ---")
    
    reply = await bot.generate_reply(
        user_msg=test_case['user_msg'],
        item_desc=test_case['item_desc'],
        context=test_case['context']
    )
    
    logger.info(f"Bot reply for {test_case['name']}: {reply}")
    
    # 添加断言来验证回复
    assert reply is not None
    assert isinstance(reply, str)
    assert "系统开小差了" not in reply
    assert "The api_key client option must be set" not in reply
    assert len(reply) > 0

@pytest.mark.asyncio
async def test_tech_agent_uses_tavily_search(bot):
    """测试技术代理在需要时是否会调用Tavily搜索工具"""
    # 我们模拟第三方库TavilyClient，而不是我们自己的函数
    with patch('XianyuGraph.TavilyClient') as MockTavilyClient:
            # 模拟search方法的返回值，提供一个AI知识库里没有的、具体的“伪事实”
            mock_instance = MockTavilyClient.return_value
            mock_instance.search.return_value = {
                "results": [{"content": "根据最新评测，天龙PMA-600NE在2024年获得了What Hi-Fi的五星推荐。"}]
            }

            user_msg = "这款雅马哈功放和市面上的天龙 PMA-600NE 比起来怎么样？"
            item_desc = "这是一台九成新的雅马哈功放机，型号是 A-S501。"
            context = []

            reply = await bot.generate_reply(
                user_msg=user_msg,
                item_desc=item_desc,
                context=context
            )

            # 验证TavilyClient的search方法是否被调用了一次
            mock_instance.search.assert_called_once()

            # 验证回复内容是否基于了搜索结果
            assert "What Hi-Fi" in reply