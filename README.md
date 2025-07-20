# 🚀 Xianyu AutoAgent - 智能闲鱼客服机器人系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/) [![LLM Powered](https://img.shields.io/badge/LLM-powered-FF6F61)](https://platform.openai.com/)

专为闲鱼平台打造的AI值守解决方案，实现闲鱼平台7×24小时自动化值守，支持多专家协同决策、智能议价和上下文感知对话。 


## 🌟 核心特性

### 智能对话引擎
| 功能模块   | 技术实现            | 关键特性                                                     |
| ---------- | ------------------- | ------------------------------------------------------------ |
| 上下文感知 | 会话历史存储        | 轻量级对话记忆管理，完整对话历史作为LLM上下文输入            |
| 专家路由   | LLM prompt+规则路由 | 基于提示工程的意图识别 → 专家Agent动态分发，支持议价/技术/客服多场景切换 |

### 业务功能矩阵
| 模块     | 已实现                        | 规划中                       |
| -------- | ----------------------------- | ---------------------------- |
| 核心引擎 | ✅ LLM自动回复<br>✅ 上下文管理 | 🔄 情感分析增强               |
| 议价系统 | ✅ 阶梯降价策略                | 🔄 市场比价功能               |
| 技术支持 | ✅ 网络搜索整合                | 🔄 RAG知识库增强              |
| 运维监控 | ✅ 基础日志                    | 🔄 钉钉集成<br>🔄  Web管理界面 |

## 🎨效果图
<div align="center">
  <img src="./images/demo1.png" width="600" alt="客服">
  <br>
  <em>图1: 客服随叫随到</em>
</div>


<div align="center">
  <img src="./images/demo2.png" width="600" alt="议价专家">
  <br>
  <em>图2: 阶梯式议价</em>
</div>

<div align="center">
  <img src="./images/demo3.png" width="600" alt="技术专家"> 
  <br>
  <em>图3: 技术专家上场</em>
</div>

<div align="center">
  <img src="./images/log.png" width="600" alt="后台log"> 
  <br>
  <em>图4: 后台log</em>
</div>


## 🚴 快速开始

### 环境要求
- Python 3.8+

### 安装步骤
```bash
1. 克隆仓库
git clone https://github.com/shaxiu/XianyuAutoAgent.git
cd XianyuAutoAgent

2. 安装依赖
pip install -r requirements.txt

3. 配置环境变量
创建一个 `.env` 文件，包含以下内容，也可直接重命名 `.env.example` ：
#必配配置
API_KEY=apikey通过模型平台获取
COOKIES_STR=填写网页端获取的cookie
MODEL_BASE_URL=模型地址
MODEL_NAME=模型名称
TAVILY_API_KEY=TAVILY_API_KEY（搜索用）
#可选配置
TOGGLE_KEYWORDS=接管模式切换关键词，默认为句号（输入句号切换为人工接管，再次输入则切换AI接管）

注意：默认使用的模型是通义千问，如需使用其他API，请自行修改.env文件中的模型地址和模型名称；
COOKIES_STR自行在闲鱼网页端获取cookies(网页端F12打开控制台，选择Network，点击Fetch/XHR,点击一个请求，查看cookies)

4. 创建提示词文件prompts/*_prompt.txt（也可以直接将模板名称中的_example去掉）
默认提供四个模板，可自行修改
```

### 使用方法

运行主程序：
```bash
python main.py
```

### 自定义提示词

我们鼓励您根据自己的销售风格和策略，深度自定义各个Agent的提示词。文件位于 `prompts` 目录下。

-   `classify_prompt.txt`: **意图分类专家**。负责将用户的消息准确分类到不同的意图（如议价、技术咨询等），是整个系统的“调度中心”。
-   `price_prompt.txt`: **议价专家**。这是最核心、经过反复优化的提示词。它采用了一种高度结构化的、基于规则的方法，强制AI遵循一个固定的回复公式。这确保了AI的还价在逻辑上永远是正确的（不会还一个比客户出价更低的价格），同时严格遵守字数限制和角色设定，杜绝了AI“自由发挥”可能导致的错误。
-   `tech_prompt.txt`: **技术专家**。负责回答关于商品规格、用法等技术性问题。它被配置为可以利用外部搜索来获取更准确的信息。
-   `default_prompt.txt`: **默认/闲聊专家**。当用户意图不属于任何特定类别时，由它来提供一个通用的、友好的回复。

## 🤝 参与贡献

欢迎通过 Issue 提交建议或 PR 贡献代码，请遵循 [贡献指南](https://contributing.md/)



## 🛡 注意事项

⚠️ **免责声明：**
本项目仅供学习、研究与技术交流使用，严禁用于任何商业用途或非法活动。使用本项目即表示您同意自行承担所有风险和责任。开发者不对因使用本项目而导致的任何直接或间接损失承担责任。

⚠️ 注意：**本项目仅供学习与交流，如有侵权联系作者删除。**

鉴于项目的特殊性，开发团队可能在任何时间**停止更新**或**删除项目**。

如需学习交流，请联系：[coderxiu@qq.com](https://mailto:coderxiu@qq.com/)

## 🧸特别鸣谢
本项目修改自 [shaxiu/XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent)。

本项目参考了以下开源项目：
https://github.com/cv-cat/XianYuApis




您的☕和⭐将助力项目持续更新：

<div align="center">
  <img src="./images/wechat_pay.jpg" width="400px" alt="微信赞赏码"> 
</div>


## 📈 Star 趋势
<a href="https://www.star-history.com/#threhan/XianyuAutoAgent&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=threhan/XianyuAutoAgent&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=threhan/XianyuAutoAgent&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=threhan/XianyuAutoAgent&type=Date" />
 </picture>
</a>


