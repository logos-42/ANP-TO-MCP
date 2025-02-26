import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException, Request
import argparse

class AnpMcpService:
    """ANP和MCP协议之间的双向转换服务"""
    
    def __init__(self, host="0.0.0.0", port=8080, debug=False):
        """初始化服务"""
        self.host = host
        self.port = port
        self.debug = debug
        
        # 创建核心转换引擎
        self.bridge = AnpMcpBridge()
        
        # 创建FastAPI应用
        self.app = FastAPI(title="ANP-MCP转换服务")
        self._setup_routes()
        
        # 预注册测试DID
        self.bridge.register_did("test_did_123", "test_oauth_456")
        self.bridge.register_did("anp_user_001", "mcp_token_001")
        
        if self.debug:
            print(f"ANP-MCP服务初始化完成，准备在 {self.host}:{self.port} 上启动")
    
    def _setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/")
        async def root():
            """服务根路径，返回服务信息"""
            return {
                "service": "ANP-MCP双向转换服务",
                "version": "1.0.0",
                "endpoints": [
                    {"path": "/capabilities", "description": "获取服务能力"},
                    {"path": "/register", "description": "注册DID和OAuth映射"},
                    {"path": "/anp-to-mcp", "description": "ANP请求转换为MCP请求"},
                    {"path": "/mcp-to-anp", "description": "MCP响应转换为ANP响应"}
                ]
            }
        
        @self.app.get("/capabilities")
        async def get_capabilities():
            """获取服务支持的能力"""
            return self.bridge.initialize_protocol()
        
        @self.app.post("/register")
        async def register_did(did: str, oauth_token: str):
            """注册DID和OAuth令牌的映射"""
            success = self.bridge.register_did(did, oauth_token)
            if success:
                return {"success": True, "message": f"成功注册DID: {did}"}
            else:
                raise HTTPException(status_code=400, detail="注册失败")
        
        @self.app.post("/anp-to-mcp")
        async def convert_anp_to_mcp(request: Request):
            """将ANP请求转换为MCP请求"""
            try:
                anp_request = await request.json()
                result = self.bridge.anp_to_mcp(anp_request)
                if not result.get("success", False):
                    raise HTTPException(status_code=400, detail=result.get("error", "转换失败"))
                return result
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="无效的JSON格式")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/mcp-to-anp")
        async def convert_mcp_to_anp(request: Request):
            """将MCP响应转换为ANP响应"""
            try:
                mcp_response = await request.json()
                result = self.bridge.mcp_to_anp(mcp_response)
                if not result.get("success", False) and "error_code" in result:
                    if result["error_code"] == "SESSION_NOT_FOUND":
                        raise HTTPException(status_code=404, detail=result.get("error", "会话未找到"))
                    else:
                        raise HTTPException(status_code=400, detail=result.get("error", "转换失败"))
                return result
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="无效的JSON格式")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/sessions/{request_id}")
        async def get_session(request_id: str):
            """获取会话信息"""
            session_info = self.bridge.get_session_info(request_id)
            if not session_info:
                raise HTTPException(status_code=404, detail="会话未找到")
            return {"success": True, "session": session_info}
        
        @self.app.delete("/sessions/{request_id}")
        async def clear_session(request_id: str):
            """清除会话信息"""
            success = self.bridge.clear_session(request_id)
            if success:
                return {"success": True, "message": f"成功清除会话: {request_id}"}
            else:
                raise HTTPException(status_code=404, detail="会话未找到")
    
    def start(self):
        """启动服务"""
        print(f"启动ANP-MCP双向转换服务在 http://{self.host}:{self.port} ...")
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    def test(self):
        """运行简单的自测试"""
        print("=== 开始ANP-MCP服务自测试 ===")
        
        # 测试DID注册
        test_did = "test_self_001"
        test_oauth = "oauth_self_001"
        result = self.bridge.register_did(test_did, test_oauth)
        print(f"DID注册结果: {result}")
        
        # 测试ANP到MCP转换
        anp_request = {
            "did": test_did,
            "intent": "查询用户信息",
            "parameters": {
                "user_id": "12345",
                "fields": ["name", "age"]
            }
        }
        result = self.bridge.anp_to_mcp(anp_request)
        print(f"ANP到MCP转换结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 测试MCP到ANP转换
        mcp_response = {
            "jsonrpc": "2.0",
            "result": {
                "name": "张三",
                "age": 30
            },
            "id": result["request_id"]
        }
        result = self.bridge.mcp_to_anp(mcp_response)
        print(f"MCP到ANP转换结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        print("=== 自测试完成 ===")


class AnpMcpBridge:
    """ANP和MCP协议之间的双向转换桥接器"""
    
    def __init__(self):
        # DID到OAuth的映射
        self.did_oauth_map = {}
        # 会话管理：请求ID到原始ANP请求的映射
        self.session_map = {}
        # 意图到方法的映射
        self.intent_method_map = {
            "查询天气": "getWeather",
            "获取天气预报": "getWeatherForecast",
            "获取天气预警": "getWeatherAlert",
            "查询用户信息": "getUserInfo",
            "更新用户信息": "updateUserInfo",
            "查询订单": "getOrderInfo",
            "创建订单": "createOrder",
            "处理支付": "processPayment"
        }
        # 方法到意图的映射（反向映射）
        self.method_intent_map = {v: k for k, v in self.intent_method_map.items()}
        
    def register_did(self, did: str, oauth_token: str) -> bool:
        """注册DID和OAuth令牌的映射"""
        self.did_oauth_map[did] = oauth_token
        return True
        
    def anp_to_mcp(self, anp_request: Dict[str, Any]) -> Dict[str, Any]:
        """将ANP请求转换为MCP请求"""
        try:
            # 1. 验证ANP请求
            if not self._validate_anp_request(anp_request):
                return {
                    "success": False,
                    "error": "无效的ANP请求格式",
                    "error_code": "INVALID_ANP_FORMAT"
                }
            
            # 2. 验证DID
            did = anp_request.get("did")
            if not did or did not in self.did_oauth_map:
                return {
                    "success": False,
                    "error": "无效的DID",
                    "error_code": "INVALID_DID"
                }
            
            # 3. 获取OAuth令牌
            oauth_token = self.did_oauth_map[did]
            
            # 4. 转换意图到方法
            intent = anp_request.get("intent")
            method = self._convert_intent_to_method(intent)
            
            # 5. 转换参数
            params = self._convert_anp_params_to_mcp(anp_request.get("parameters", {}))
            
            # 6. 生成请求ID
            request_id = f"req-{uuid.uuid4().hex[:8]}"
            
            # 7. 构建MCP请求
            mcp_request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": request_id,
                "oauth_token": oauth_token  # 添加OAuth认证
            }
            
            # 8. 保存会话信息
            self.session_map[request_id] = {
                "anp_request": anp_request,
                "timestamp": datetime.now().isoformat(),
                "did": did
            }
            
            return {
                "success": True,
                "mcp_request": mcp_request,
                "request_id": request_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"转换失败: {str(e)}",
                "error_code": "CONVERSION_ERROR"
            }
    
    def mcp_to_anp(self, mcp_response: Dict[str, Any]) -> Dict[str, Any]:
        """将MCP响应转换为ANP响应"""
        try:
            # 1. 验证MCP响应
            if not self._validate_mcp_response(mcp_response):
                return {
                    "success": False,
                    "error": "无效的MCP响应格式",
                    "error_code": "INVALID_MCP_FORMAT"
                }
            
            # 2. 获取请求ID
            request_id = mcp_response.get("id")
            
            # 3. 检查会话信息
            session_info = self.session_map.get(request_id)
            if not session_info:
                return {
                    "success": False,
                    "error": "未找到对应的会话信息",
                    "error_code": "SESSION_NOT_FOUND"
                }
            
            # 4. 检查是否有错误
            if "error" in mcp_response:
                return {
                    "success": False,
                    "error": mcp_response["error"].get("message", "未知错误"),
                    "error_code": mcp_response["error"].get("code", "UNKNOWN_ERROR"),
                    "context": {
                        "request_id": request_id,
                        "original_intent": session_info["anp_request"].get("intent")
                    }
                }
            
            # 5. 获取结果
            result = mcp_response.get("result", {})
            
            # 6. 构建ANP响应
            original_intent = session_info["anp_request"].get("intent")
            anp_response = {
                "success": True,
                "data": self._convert_mcp_result_to_anp(result),
                "context": {
                    "intent": original_intent,
                    "request_id": request_id,
                    "did": session_info["did"]
                }
            }
            
            return anp_response
            
        except Exception as e:
            return {
                "success": False,
                "error": f"转换失败: {str(e)}",
                "error_code": "CONVERSION_ERROR"
            }
    
    def _validate_anp_request(self, request: Dict[str, Any]) -> bool:
        """验证ANP请求格式"""
        required_fields = ["did", "intent"]
        return all(field in request for field in required_fields)
    
    def _validate_mcp_response(self, response: Dict[str, Any]) -> bool:
        """验证MCP响应格式"""
        required_fields = ["jsonrpc", "id"]
        has_result_or_error = "result" in response or "error" in response
        return all(field in response for field in required_fields) and has_result_or_error
    
    def _convert_intent_to_method(self, intent: str) -> str:
        """将ANP意图转换为MCP方法名"""
        return self.intent_method_map.get(intent, self._default_method_conversion(intent))
    
    def _convert_method_to_intent(self, method: str) -> str:
        """将MCP方法名转换为ANP意图"""
        return self.method_intent_map.get(method, method)
    
    def _default_method_conversion(self, intent: str) -> str:
        """默认的意图到方法名转换"""
        words = intent.split()
        if not words:
            return "query"
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
    
    def _convert_anp_params_to_mcp(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """转换ANP参数到MCP参数"""
        param_key_map = {
            "user_id": "userId",
            "order_id": "orderId",
            "page_size": "pageSize",
            "page_num": "pageNum",
            "city": "cityName",
            "date": "queryDate"
        }
        
        converted = {}
        for key, value in params.items():
            new_key = param_key_map.get(key, key)
            converted[new_key] = value
        return converted
    
    def _convert_mcp_result_to_anp(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """转换MCP结果到ANP数据格式"""
        # 这里可以添加特定的转换逻辑
        # 目前简单返回原始结果
        return result
    
    def initialize_protocol(self) -> Dict[str, Any]:
        """初始化协议，返回支持的能力"""
        return {
            "protocol": "anp-mcp-bridge",
            "version": "1.0.0",
            "capabilities": {
                "anp_to_mcp": True,
                "mcp_to_anp": True,
                "did_oauth_mapping": True,
                "session_management": True
            }
        }
    
    def get_session_info(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self.session_map.get(request_id)
    
    def clear_session(self, request_id: str) -> bool:
        """清除会话信息"""
        if request_id in self.session_map:
            del self.session_map[request_id]
            return True
        return False


def run_test_client():
    """运行测试客户端"""
    import requests
    import time
    
    print("\n=== 开始测试ANP-MCP客户端 ===")
    
    # 配置
    base_url = "http://localhost:8080"
    test_did = "test_client_001"
    test_oauth = "oauth_token_client_001"
    
    try:
        # 1. 注册DID
        print("\n1. 注册DID")
        response = requests.post(f"{base_url}/register", params={
            "did": test_did,
            "oauth_token": test_oauth
        })
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        # 2. 测试ANP到MCP转换
        print("\n2. 测试ANP到MCP转换")
        anp_request = {
            "did": test_did,
            "intent": "查询用户信息",
            "parameters": {
                "user_id": "U12345",
                "fields": ["name", "email", "phone"]
            }
        }
        print(f"ANP请求: {json.dumps(anp_request, ensure_ascii=False, indent=2)}")
        
        response = requests.post(f"{base_url}/anp-to-mcp", json=anp_request)
        print(f"状态码: {response.status_code}")
        anp_to_mcp_result = response.json()
        print(f"转换结果: {json.dumps(anp_to_mcp_result, ensure_ascii=False, indent=2)}")
        
        # 保存请求ID和MCP请求，用于后续测试
        request_id = anp_to_mcp_result["request_id"]
        
        # 3. 模拟MCP服务处理并返回响应
        print("\n3. 模拟MCP服务响应")
        # 这里模拟MCP服务的处理逻辑
        time.sleep(1)  # 模拟处理时间
        
        mcp_response = {
            "jsonrpc": "2.0",
            "result": {
                "name": "李明",
                "email": "liming@example.com",
                "phone": "13800138000",
                "vip_status": "gold"
            },
            "id": request_id
        }
        print(f"MCP响应: {json.dumps(mcp_response, ensure_ascii=False, indent=2)}")
        
        # 4. 测试MCP到ANP转换
        print("\n4. 测试MCP到ANP转换")
        response = requests.post(f"{base_url}/mcp-to-anp", json=mcp_response)
        print(f"状态码: {response.status_code}")
        mcp_to_anp_result = response.json()
        print(f"转换结果: {json.dumps(mcp_to_anp_result, ensure_ascii=False, indent=2)}")
        
    except requests.exceptions.ConnectionError:
        print(f"\n连接错误: 请确保服务正在运行 (http://localhost:8080)")
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")
    
    print("\n=== 测试完成 ===")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ANP-MCP双向转换服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--test", action="store_true", help="运行自测试")
    parser.add_argument("--client", action="store_true", help="运行测试客户端")
    
    args = parser.parse_args()
    
    # 创建服务
    service = AnpMcpService(host=args.host, port=args.port, debug=args.debug)
    
    # 根据命令行参数决定操作
    if args.test:
        service.test()
    elif args.client:
        run_test_client()
    else:
        service.start()


if __name__ == "__main__":
    main() 