# ANP-MCP 双向转换服务
这个项目实现了ANP (Agent Network Protocol) 和MCP (Model Context Protocol) 之间的双向转换功能，允许ANP客户端与MCP服务进行无缝通信。

## 特点

- **单文件实现**：所有功能都集成在一个Python文件中
- **简单易用**：通过命令行参数轻松配置和启动
- **完整功能**：保留了所有核心功能，包括DID-OAuth映射、协议转换和会话管理
- **内置测试**：包含自测试和客户端测试功能

## 安装

1. 确保已安装Python 3.7+
2. 安装依赖：

```bash
pip install fastapi uvicorn requests
```

## 使用方法

### 启动服务

```bash
python simple_anp_mcp_service.py
```

服务将在 `http://localhost:8080` 上运行。

### 命令行选项

```bash
python simple_anp_mcp_service.py [选项]
```

可用选项：
- `--host HOST`：指定服务主机地址（默认：0.0.0.0）
- `--port PORT`：指定服务端口（默认：8080）
- `--debug`：启用调试模式
- `--test`：运行自测试
- `--client`：运行测试客户端

例如，在特定端口启动服务：
```bash
python simple_anp_mcp_service.py --port 9000
```

### 运行自测试

```bash
python simple_anp_mcp_service.py --test
```

### 运行测试客户端

```bash
python simple_anp_mcp_service.py --client
```

## API接口

### 1. 获取服务信息

```
GET /
```

### 2. 获取服务能力

```
GET /capabilities
```

### 3. 注册DID

```
POST /register?did={did}&oauth_token={oauth_token}
```

### 4. ANP到MCP转换

```
POST /anp-to-mcp
```

请求体示例：
```json
{
    "did": "user_did_123",
    "intent": "查询用户信息",
    "parameters": {
        "user_id": "12345",
        "fields": ["name", "age"]
    }
}
```

### 5. MCP到ANP转换

```
POST /mcp-to-anp
```

请求体示例：
```json
{
    "jsonrpc": "2.0",
    "result": {
        "name": "张三",
        "age": 30
    },
    "id": "req-abc123"
}
```

### 6. 会话管理

```
GET /sessions/{request_id}    # 获取会话信息
DELETE /sessions/{request_id} # 清除会话
```

## 示例流程

1. 注册DID和OAuth令牌的映射
2. 发送ANP请求到服务
3. 服务将ANP请求转换为MCP请求
4. 将MCP请求发送到MCP服务
5. 接收MCP服务的响应
6. 将MCP响应转换为ANP响应
7. 返回ANP响应给客户端

## 代码结构

- `AnpMcpService`：服务主类，处理HTTP请求和路由
- `AnpMcpBridge`：核心转换引擎，实现ANP和MCP之间的双向转换
- `run_test_client`：测试客户端函数
- `main`：主函数，处理命令行参数和启动服务

## 安全考虑

- 使用DID-OAuth映射确保只有授权的ANP客户端可以访问MCP服务
- 会话管理确保请求-响应的正确对应
- 错误处理提供友好的错误提示

## 扩展方向

1. 支持更多ANP意图和MCP方法的映射
2. 增强安全机制，如令牌刷新和过期管理
3. 添加更多的错误处理和日志记录
4. 实现完整的MCP协议初始化和能力协商 
