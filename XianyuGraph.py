import os
import re
import functools
from typing import TypedDict, Annotated, List, Dict, Optional
import operator
import json

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from loguru import logger
from tavily import TavilyClient

#from context_manager import ChatContextManager

# 1. 工具定义
class TavilySearchArgs(BaseModel):
    query: str = Field(description="The search query to use with Tavily.")

@tool(args_schema=TavilySearchArgs)
def tavily_web_search(query: str) -> str:
    """Use Tavily to search the web for up-to-date information."""
    try:
        tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        # search_depth="advanced" 可以获取更丰富的结果
        response = tavily_client.search(query, search_depth="advanced")
        
        # 提取并格式化结果，使其更易于LLM消费
        results = response.get("results", [])
        formatted_results = "\n".join([res.get("content", "") for res in results])
        
        return f"网络搜索结果：\n{formatted_results}"
    except Exception as e:
        return f"Error during Tavily search: {e}"

# 1. 工具定义
class ItemDetailsArgs(BaseModel):
    item_id: str = Field(description="The ID of the item to get details for.")

@tool(args_schema=ItemDetailsArgs)
def get_item_details(item_id: str) -> str:
    """Call this to get detailed technical specifications of an item."""
    logger.info(f"Tool called: get_item_details for item_id: {item_id}")
    mock_db = {
        "item_123": {"power_output": "100W", "channels": "5.1", "impedance": "8 ohms"},
        "item_456": {"power_output": "150W", "channels": "7.1", "impedance": "6 ohms"},
    }
    details = mock_db.get(item_id, {"error": "Item not found"})
    return json.dumps(details, ensure_ascii=False)

class LogRequestArgs(BaseModel):
    request_details: str = Field(description="The details of the customer\'s request to be logged.")

@tool(args_schema=LogRequestArgs)
def log_customer_request(request_details: str) -> str:
    """Log a customer\'s request to a file for later review."""
    try:
        with open("customer_requests.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {request_details}\n")
        logger.info(f"Logged customer request: {request_details}")
        return "Request logged successfully."
    except Exception as e:
        logger.error(f"Failed to log customer request: {e}")
        return f"Error logging request: {e}"

# 2. 状态定义
class AgentState(TypedDict):
    user_message: str
    item_description: str
    chat_history: Annotated[list, operator.add]
    intent: str
    bargain_count: int
    final_reply: str
    # 直接使用 AIMessage 中解析好的 tool_calls 对象
    tool_calls: Optional[List[dict]] = None

# 3. 节点函数
def router_node(state: AgentState, client: ChatOpenAI) -> Dict:
    logger.info("Executing LLM-driven router")
    with open(os.path.join("prompts", "router_prompt.txt"), "r", encoding="utf-8") as f:
        system_prompt = f.read()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=state['user_message'])]
    response = client.invoke(messages)
    intent = response.content.strip().lower()
    if intent not in ['tech', 'price', 'default']:
        intent = 'default'
    logger.info(f"LLM-driven intent detected: {intent}")
    return {"intent": intent, "chat_history": [HumanMessage(content=state['user_message'])]}

def base_agent_node(state: AgentState, client: ChatOpenAI, system_prompt: str, agent_name: str) -> Dict:
    logger.info(f"Executing {agent_name} Agent (no tools)")
    messages = [SystemMessage(content=f"【商品信息】{state['item_description']}\n{system_prompt}"), *state['chat_history']]
    response = client.invoke(messages)
    return {"final_reply": response.content, "chat_history": [response]}

def price_agent_node(state: AgentState, client: ChatOpenAI) -> Dict:
    with open(os.path.join("prompts", "price_prompt.txt"), "r", encoding="utf-8") as f:
        prompt = f.read()
    return base_agent_node(state, client, prompt, "Price")

def default_agent_node(state: AgentState, client: ChatOpenAI) -> Dict:
    logger.info("Executing Default Agent (with potential tools)")
    with open(os.path.join("prompts", "default_prompt.txt"), "r", encoding="utf-8") as f:
        system_prompt = f.read()
    messages = [SystemMessage(content=f"【商品信息】{state['item_description']}\n{system_prompt}"), *state['chat_history']]
    response = client.invoke(messages)
    if not response.tool_calls:
        logger.info(f"Default agent generated a direct reply: {response.content}")
        return {"final_reply": response.content, "chat_history": [response]}
    else:
        logger.info(f"Default agent decided to call tools: {response.tool_calls}")
        return {"tool_calls": response.tool_calls, "chat_history": [response]}

def tech_agent_node(state: AgentState, client: ChatOpenAI) -> Dict:

    logger.info("Executing Tech Agent (with tools)")
    with open(os.path.join("prompts", "tech_prompt.txt"), "r", encoding="utf-8") as f:
        system_prompt = f.read()
    messages = [SystemMessage(content=f"【商品信息】{state['item_description']}\n{system_prompt}"), *state['chat_history']]
    response = client.invoke(messages)
    if not response.tool_calls:
        logger.info(f"Tech agent generated a direct reply: {response.content}")
        return {"final_reply": response.content, "chat_history": [response]}
    else:
        logger.info(f"Tech agent decided to call tools: {response.tool_calls}")
        return {"tool_calls": response.tool_calls, "chat_history": [response]}



def safety_filter_node(state: AgentState) -> Dict:
    reply = state['final_reply']
    blocked_phrases = ["微信", "QQ", "支付宝", "银行卡", "线下"]
    if any(p in reply for p in blocked_phrases):
        logger.warning(f"Blocked sensitive word in reply: {reply}")
        return {"final_reply": "[安全提醒]请通过平台沟通"}
    return {}

def should_continue(state: AgentState) -> str:
    if state.get("tool_calls"):
        return "tool_node"
    else:
        return "safety_filter"

def tool_node(state: AgentState) -> Dict:
    if not state.get("tool_calls"):
        return {}
    logger.info(f"Executing tools: {state['tool_calls']}")
    tool_map = {"get_item_details": get_item_details, "tavily_web_search": tavily_web_search, "log_customer_request": log_customer_request}
    tool_messages = []
    for tool_call in state["tool_calls"]:
        tool_name = tool_call['name']
        if tool_name in tool_map:
            try:
                result = tool_map[tool_name].invoke(tool_call['args'])
            except Exception as e:
                result = f"Error executing tool {tool_name}: {e}"
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call['id']))
    return {"chat_history": tool_messages, "tool_calls": None}

# 4. 图构建器
class XianyuGraphBuilder:
    def __init__(self):
        self.client = ChatOpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "http://127.0.0.1:8080/v1"),
            model=os.getenv("MODEL_NAME", "Magistral-Small-2506"),
            temperature=0.2
        )
        if not self.client.openai_api_key:
            raise ValueError("API_KEY not found in environment.")
        self.tool_client = self.client.bind_tools([get_item_details, tavily_web_search, log_customer_request])
       # self.context_manager = ChatContextManager()
        
        # 将 context_manager 注入到工具函数中
       # bound_tavily_web_search = functools.partial(tavily_web_search, context_manager=self.context_manager)
        
       # self.tool_client = self.client.bind_tools([get_item_details, bound_tavily_web_search])
        self.graph = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self):
        self.graph.add_node("router", functools.partial(router_node, client=self.client))
        self.graph.add_node("price_agent", functools.partial(price_agent_node, client=self.client))
        self.graph.add_node("default_agent", functools.partial(default_agent_node, client=self.tool_client))
        self.graph.add_node("tech_agent", functools.partial(tech_agent_node, client=self.tool_client))
        self.graph.add_node("tool_node", tool_node)
        self.graph.add_node("safety_filter", safety_filter_node)

        self.graph.set_entry_point("router")
        self.graph.add_conditional_edges("router", lambda s: s["intent"], {"price": "price_agent", "tech": "tech_agent", "default": "default_agent"})
        self.graph.add_conditional_edges("tech_agent", should_continue, {"tool_node": "tool_node", "safety_filter": "safety_filter"})
        self.graph.add_conditional_edges("default_agent", should_continue, {"tool_node": "tool_node", "safety_filter": "safety_filter"})
        self.graph.add_edge('tool_node', 'tech_agent')
        self.graph.add_edge('price_agent', 'safety_filter')
        self.graph.add_edge('default_agent', 'safety_filter')
        self.graph.add_edge('safety_filter', END)

    def compile(self):
        return self.graph.compile()

def get_graph():
    builder = XianyuGraphBuilder()
    return builder.compile()


