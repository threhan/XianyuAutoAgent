# XianyuAutoAgent 部署指南

## 1. 项目概述

XianyuAutoAgent 是一个基于 WebSocket 和大语言模型（LLM）的闲鱼（Goofish）自动化回复机器人。它能够实时接收并理解买家的消息，并根据预设的逻辑和商品信息，生成符合上下文的智能回复，从而实现7x24小时的自动化客户沟通。

核心技术栈：
- **Python**: 主要开发语言。
- **WebSockets**: 用于与闲鱼服务器进行实时消息通信。
- **LangGraph**: 构建强大的、有状态的、多角色的智能代理（Agent）。
- **Docker & Docker Compose**: 用于容器化部署和管理服务。
- **本地大语言模型 (LLM)**: 作为机器人的“大脑”，负责理解和生成文本。

---

## 2. 先决条件

在开始部署之前，请确保您的系统满足以下条件：

- **Git**: 用于克隆本项目仓库。
- **Docker 和 Docker Compose**: （推荐部署方式）用于构建和运行应用程序容器。
- **Python**: (版本 >= 3.9) （本地开发部署方式）。
- **一个正在运行的本地大语言模型服务**: 并且该服务兼容 OpenAI API 格式。详情请见 **附录A**。

---

## 3. 配置

无论使用何种方式部署，配置都是关键的第一步。

1.  **创建 `.env` 文件**:
    项目通过 `.env` 文件管理所有敏感信息和配置。请首先将示例文件复制一份：
    ```bash
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**:
    打开您刚刚创建的 `.env` 文件，并填入以下值：

    - `COOKIES_STR`: **（必需）** 您的闲鱼网页版 Cookies。
      - **如何获取**:
        1.  在浏览器中登录 [闲鱼网页版](https://www.goofish.com/)。
        2.  打开开发者工具（通常按 F12）。
        3.  切换到 “网络” (Network) 标签页。
        4.  刷新页面，找到任意一个对 `goofish.com` 的请求。
        5.  在请求头 (Request Headers) 中找到 `Cookie` 字段，并复制其完整的字符串值。

    - `API_KEY`: **（必需）** 您的语言模型 API 密钥。即使是本地模型，某些框架也需要一个非空的密钥，您可以填入任意字符串，例如 `sk-xxxxxx`。

    - `MODEL_BASE_URL`: **（必需）** 您的本地 LLM 服务地址。它必须是一个兼容 OpenAI 的 API 端点。
      - **默认值**: `http://127.0.0.1:8080/v1`
      - 如果您的模型服务运行在不同的主机或端口，请务必修改此项。

    - `MODEL_NAME`: **（必需）** 您正在使用的模型名称。此名称需要与您的模型服务所加载的名称一致。

    - `LOG_LEVEL`: (可选) 日志输出级别，例如 `INFO`, `DEBUG`。默认为 `DEBUG`。

    - `HEARTBEAT_INTERVAL`: (可选) WebSocket 心跳发送间隔（秒）。默认为 `15`。

    - `TOGGLE_KEYWORDS`: (可选) 用于在卖家端切换“人工/自动”模式的关键词。默认为 `。`（中文句号）。

### `config.json`

除了 `.env` 文件，项目还使用 `config.json` 来管理所有与闲鱼 API 和 WebSocket 相关的非敏感、结构化配置。通常情况下，您**不需要**修改此文件，除非闲鱼的 API 端点或消息格式发生变化。

---

## 4. 部署步骤

## 4. 部署步骤

### 方法一：使用 Docker (推荐)

这是最简单、最可靠的部署方式，可以确保环境的一致性。

1.  **克隆项目**:
    ```bash
    git clone https://github.com/your-username/XianyuAutoAgent.git
    cd XianyuAutoAgent
    ```

2.  **完成配置**:
    确保您已经按照 **第3节** 的说明，正确创建并填写了 `.env` 文件。

3.  **构建并启动服务**:
    运行以下命令来构建 Docker 镜像并以后台模式启动服务：
    ```bash
    docker-compose up --build -d
    ```

4.  **验证运行状态**:
    - 查看服务日志，确认是否成功连接到 WebSocket 和 LLM 服务：
      ```bash
      docker-compose logs -f
      ```
    - 当您看到类似 `连接注册完成` 和 `Token刷新成功` 的日志时，表示服务已正常启动。

5.  **停止服务**:
    ```bash
    docker-compose down
    ```

### 方法二：本地直接运行 (适用于开发)

如果您想在本地进行开发或调试，可以采用此方法。

1.  **克隆项目**:
    ```bash
    git clone https://github.com/your-username/XianyuAutoAgent.git
    cd XianyuAutoAgent
    ```

2.  **完成配置**:
    确保您已经按照 **第3节** 的说明，正确创建并填写了 `.env` 文件。

3.  **创建虚拟环境**:
    为了保持依赖隔离，强烈建议使用虚拟环境。
    ```bash
    python -m venv .venv
    ```
    激活虚拟环境：
    - Windows:
      ```bash
      .venv\Scripts\activate
      ```
    - macOS / Linux:
      ```bash
      source .venv/bin/activate
      ```

4.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **运行程序**:
    ```bash
    python main.py
    ```

6.  **验证运行状态**:
    直接在终端查看实时日志输出。按 `Ctrl+C` 停止程序。

---

## 5. 本地测试

在部署或开发过程中，您可以运行单元测试来验证核心 Agent 逻辑是否正常，这**不需要**连接到闲鱼服务器。

1.  **安装开发依赖**:
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **运行测试**:
    ```bash
    pytest tests/
    ```
    如果所有测试都通过，说明 `XianyuReplyBot` 的核心逻辑是健全的。

---

## 附录A: 搭建本地大语言模型服务

本项目的核心是 `XianyuGraph.py` 中定义的智能代理，它依赖一个兼容 OpenAI API 格式的 LLM 服务。您可以使用 `vLLM`, `Ollama`, `llama-cpp-python` 等多种框架来搭建此服务。

以下是使用 **`llama-cpp-python`** 的一个快速搭建示例：

1.  **安装 `llama-cpp-python`**:
    为了获得最佳性能，建议根据您的硬件（如NVIDIA GPU）安装特定版本。
    ```bash
    # 示例：安装支持 CUDA 12.1 的版本
    CMAKE_ARGS="-DLLAMA_CUBLAS=on" FORCE_CMAKE=1 pip install llama-cpp-python
    ```
    如果只有 CPU，可以简单地：
    ```bash
    pip install llama-cpp-python
    ```

2.  **下载模型文件**:
    从 Hugging Face 等平台下载 GGUF 格式的模型文件，例如 `Magistral-Small-2506-Q4_K_M.gguf`。

3.  **启动模型服务**:
    运行以下命令，启动一个监听在 `8080` 端口的 OpenAI 兼容服务。
    ```bash
    python -m llama_cpp.server --model /path/to/your/model.gguf --host 0.0.0.0 --port 8080 --n_ctx 4096
    ```
    - `--model`: **必须**替换为您下载的模型文件的实际路径。
    - `--host 0.0.0.0`: 允许从其他计算机（或Docker容器）访问。
    - `--port 8080`: 监听的端口，与 `.env` 文件中的 `MODEL_BASE_URL` 对应。

4.  **验证服务**:
    服务启动后，您可以在另一个终端中使用 `curl` 来验证它是否正常工作：
    ```bash
    curl http://127.0.0.1:8080/v1/models
    ```
    如果返回了模型的 JSON 信息，则表示本地 LLM 服务已准备就绪。
