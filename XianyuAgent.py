import re
from typing import List, Dict
import os
from openai import OpenAI
from loguru import logger

# =================================================================
# 1. Base Agent and Specific Agents
# =================================================================

class BaseAgent:
    """Agent基类"""
    def __init__(self, client, system_prompt, safety_filter):
        self.client = client
        self.system_prompt = system_prompt
        self.safety_filter = safety_filter

    def generate(self, user_msg: str, item_desc: str, context: str, **kwargs) -> str:
        """生成回复模板方法"""
        messages = self._build_messages(user_msg, item_desc, context, **kwargs)
        response = self._call_llm(messages)
        return self.safety_filter(response)

    def _build_messages(self, user_msg: str, item_desc: str, context: str, **kwargs) -> List[Dict]:
        """构建消息链"""
        
        # 为kwargs中的None值提供默认空字符串，避免格式化错误
        safe_kwargs = {k: (v if v is not None else "") for k, v in kwargs.items()}

        system_prompt = self.system_prompt.format(
            item_desc=item_desc,
            context=context,
            **safe_kwargs
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]

    def _call_llm(self, messages: List[Dict], temperature: float = 0.4) -> str:
        """调用大模型"""
        response = self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "qwen-max"),
            messages=messages,
            temperature=temperature,
            max_tokens=500,
            top_p=0.8
        )
        return response.choices[0].message.content

class PriceAgent(BaseAgent):
    """议价处理Agent"""
    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int = 0, **kwargs) -> str:
        """重写生成逻辑"""
        dynamic_temp = self._calc_temperature(bargain_count)
        
        # 将所有信息通过kwargs传递给_build_messages进行格式化
        messages = self._build_messages(
            user_msg, 
            item_desc, 
            context, 
            bargain_count=bargain_count,
            **kwargs
        )

        logger.info(f"向大模型发送的消息: {messages}")
        response = self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "qwen-max"),
            messages=messages,
            temperature=dynamic_temp,
            max_tokens=500,
            top_p=0.8
        )
        return self.safety_filter(response.choices[0].message.content)

    def _calc_temperature(self, bargain_count: int) -> float:
        return min(0.3 + bargain_count * 0.15, 0.9)

class TechAgent(BaseAgent):
    """技术咨询Agent"""
    def generate(self, user_msg: str, item_desc: str, context: str, **kwargs) -> str:
        messages = self._build_messages(user_msg, item_desc, context)
        response = self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "qwen-max"),
            messages=messages,
            temperature=0.4,
            max_tokens=500,
            top_p=0.8,
            extra_body={"enable_search": True}
        )
        return self.safety_filter(response.choices[0].message.content)

class ProposeDiscountAgent(BaseAgent):
    """优惠方案提议Agent"""
    def generate(self, discount_info: dict, **kwargs) -> str:
        proposal = (
            f"您好，我们看到您想购买 {discount_info['quantity']} 件商品。"
            f"商品单价是 {discount_info['unit_price']} 元，总价是 {discount_info['total_price']} 元。"
            f"根据我们的批量优惠政策，我们可以为您优惠 {discount_info['max_discount']} 元，"
            f"优惠后的总价是 {discount_info['final_price']} 元。"
            f"您看这个方案可以吗？如果可以，我将为您创建订单。"
        )
        return proposal

class ConfirmDiscountAgent(BaseAgent):
    """确认优惠并引导下单Agent"""
    def generate(self, discount_info: dict, **kwargs) -> str:
        reply = (
            f"好的，那我们就按总价 {discount_info['final_price']} 元成交。"
            f"请您直接拍下 {discount_info['quantity']} 件商品，我会在后台为您修改价格。"
            f"修改后您再付款就可以了。"
        )
        return reply

class ClassifyAgent(BaseAgent):
    """意图识别Agent"""
    pass # Inherits __init__ and generate from BaseAgent

class DefaultAgent(BaseAgent):
    """默认处理Agent"""
    def _call_llm(self, messages: List[Dict], *args) -> str:
        response = super()._call_llm(messages, temperature=0.7)
        return response

# =================================================================
# 2. Intent Router
# =================================================================

class IntentRouter:
    """意图路由决策器"""
    def __init__(self, classify_agent):
        self.rules = {
            'tech': {'keywords': ['参数', '规格', '型号', '连接', '对比'], 'patterns': [r'和.+比']},
            'price': {'keywords': ['便宜', '价', '砍价', '少点'], 'patterns': [r'\d+元', r'能少\d+']},
            'confirm_discount': {'keywords': ['可以', '好的', '行', 'ok', '嗯'], 'patterns': []},
            'propose_discount': {'keywords': ['批量', '多件', '都买了'], 'patterns': [r'买\d+件', r'要\d+个']}
        }
        self.classify_agent = classify_agent

    def detect(self, user_msg: str, item_desc: str, context: str, last_intent: str) -> str:
        text_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', user_msg).lower()

        if last_intent == 'propose_discount' and any(kw in text_clean for kw in self.rules['confirm_discount']['keywords']):
            return 'confirm_discount'

        if any(kw in text_clean for kw in self.rules['propose_discount']['keywords']) or any(re.search(p, text_clean) for p in self.rules['propose_discount']['patterns']):
             return 'propose_discount'

        if any(kw in text_clean for kw in self.rules['tech']['keywords']) or any(re.search(p, text_clean) for p in self.rules['tech']['patterns']):
            return 'tech'
        if any(kw in text_clean for kw in self.rules['price']['keywords']) or any(re.search(p, text_clean) for p in self.rules['price']['patterns']):
            return 'price'
        
        return self.classify_agent.generate(user_msg=user_msg, item_desc=item_desc, context=context)

# =================================================================
# 3. Main Bot Class
# =================================================================

class XianyuReplyBot:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        self._init_system_prompts()
        self._init_agents()
        self.router = IntentRouter(self.agents['classify'])
        self.last_intent = None
        self.last_discount_info = {}

    def _init_agents(self):
        self.agents = {
            'classify': ClassifyAgent(self.client, self.classify_prompt, self._safe_filter),
            'price': PriceAgent(self.client, self.price_prompt, self._safe_filter),
            'tech': TechAgent(self.client, self.tech_prompt, self._safe_filter),
            'default': DefaultAgent(self.client, self.default_prompt, self._safe_filter),
            'propose_discount': ProposeDiscountAgent(self.client, "", self._safe_filter),
            'confirm_discount': ConfirmDiscountAgent(self.client, "", self._safe_filter),
        }

    def _init_system_prompts(self):
        prompt_dir = "prompts"
        try:
            with open(os.path.join(prompt_dir, "classify_prompt.txt"), "r", encoding="utf-8") as f: self.classify_prompt = f.read()
            with open(os.path.join(prompt_dir, "price_prompt.txt"), "r", encoding="utf-8") as f: self.price_prompt = f.read()
            with open(os.path.join(prompt_dir, "tech_prompt.txt"), "r", encoding="utf-8") as f: self.tech_prompt = f.read()
            with open(os.path.join(prompt_dir, "default_prompt.txt"), "r", encoding="utf-8") as f: self.default_prompt = f.read()
            logger.info("成功加载所有提示词")
        except Exception as e:
            logger.error(f"加载提示词时出错: {e}")
            pass

    def _safe_filter(self, text: str) -> str:
        blocked_phrases = ["微信", "QQ", "支付宝", "银行卡", "线下"]
        return "[安全提醒]请通过平台沟通" if any(p in text for p in blocked_phrases) else text

    def format_history(self, context: List[Dict]) -> str:
        user_assistant_msgs = [msg for msg in context if msg['role'] in ['user', 'assistant']]
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_assistant_msgs])

    def _extract_bargain_count(self, context: List[Dict]) -> int:
        for msg in context:
            if msg.get('role') == 'system' and '议价次数' in msg.get('content', ''):
                try:
                    match = re.search(r'议价次数[:：]\s*(\d+)', msg['content'])
                    if match: return int(match.group(1))
                except Exception: pass
        return 0

    def _extract_user_offer(self, user_msg: str) -> float:
        """从用户消息中提取出价"""
        match = re.search(r'(\d+\.?\d*)\s*(块|元)', user_msg)
        if match:
            return float(match.group(1))
        return 0.0

    def _calculate_discount(self, user_msg: str, item_desc: str) -> dict:
        quantity_match = re.search(r'(\d+)', user_msg)
        quantity = int(quantity_match.group(1)) if quantity_match else 1
        if quantity <= 1: return None

        price_match = re.search(r'价格为:(\d+\.?\d*)', item_desc)
        unit_price = float(price_match.group(1)) if price_match else 0
        if unit_price == 0: return None

        total_price = unit_price * quantity
        max_discount = min(total_price * 0.1, 50.0)
        final_price = total_price - max_discount

        return {
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "total_price": round(total_price, 2),
            "max_discount": round(max_discount, 2),
            "final_price": round(final_price, 2),
        }

    def generate_reply(self, user_msg: str, item_info: dict, context: List[Dict]) -> str:
        item_desc = f"{item_info.get('desc', '')};当前商品售卖价格为:{str(item_info.get('soldPrice', ''))}"
        product_name = item_info.get('title', '这款商品')
        original_price = float(item_info.get('soldPrice', 0.0))

        formatted_context = self.format_history(context)
        detected_intent = self.router.detect(user_msg, item_desc, formatted_context, self.last_intent)
        logger.info(f'意图识别完成: {detected_intent}')

        agent = self.agents.get(detected_intent, self.agents['default'])
        
        agent_kwargs = {
            'user_msg': user_msg,
            'item_desc': item_desc,
            'context': formatted_context,
            'product_name': product_name
        }

        if detected_intent == 'propose_discount':
            discount_info = self._calculate_discount(user_msg, item_desc)
            if discount_info:
                self.last_discount_info = discount_info
                agent_kwargs['discount_info'] = discount_info
                reply = agent.generate(**agent_kwargs)
            else:
                agent = self.agents['price']
                bargain_count = self._extract_bargain_count(context)
                user_offer_price = self._extract_user_offer(user_msg)
                agent_kwargs['bargain_count'] = bargain_count
                agent_kwargs['user_offer_price'] = user_offer_price
                agent_kwargs['original_price'] = original_price
                reply = agent.generate(**agent_kwargs)

        elif detected_intent == 'confirm_discount':
            if self.last_intent == 'propose_discount' and self.last_discount_info:
                agent_kwargs['discount_info'] = self.last_discount_info
                reply = agent.generate(**agent_kwargs)
                self.last_discount_info = {}
            else:
                agent = self.agents['default']
                reply = agent.generate(**agent_kwargs)
        
        elif detected_intent == 'price':
            bargain_count = self._extract_bargain_count(context)
            user_offer_price = self._extract_user_offer(user_msg)
            agent_kwargs['bargain_count'] = bargain_count
            agent_kwargs['user_offer_price'] = user_offer_price
            agent_kwargs['original_price'] = original_price
            reply = agent.generate(**agent_kwargs)

        else:
            reply = agent.generate(**agent_kwargs)

        self.last_intent = detected_intent
        return reply

    def reload_prompts(self):
        logger.info("正在重新加载提示词...")
        self._init_system_prompts()
        self._init_agents()
        logger.info("提示词重新加载完成")
