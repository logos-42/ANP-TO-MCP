import requests
import json
import time

class WeatherIntegrationTest:
    def __init__(self):
        self.anp_gateway_url = "http://localhost:8080"  # ANP-MCP转换服务地址
        self.weather_service_url = "http://localhost:8002"  # weather服务默认端口
        self.test_did = "test_weather_client_001"
        self.test_oauth_token = "weather_oauth_token_001"

    def register_did(self):
        """注册DID和OAuth token的映射关系"""
        register_url = f"{self.anp_gateway_url}/register"
        try:
            response = requests.post(register_url, params={
                "did": self.test_did,
                "oauth_token": self.test_oauth_token
            })
            print(f"注册DID结果: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"注册DID失败: {str(e)}")
            return False

    def test_get_weather(self):
        """测试天气查询功能"""
        # 构造ANP格式的请求
        anp_request = {
            "version": "1.0",
            "did": self.test_did,
            "intent": "查询天气",
            "params": {
                "city": "北京",
                "date": "today"
            }
        }

        try:
            # 1. 发送ANP请求到转换服务
            print("\n1. 发送ANP请求到转换服务:")
            print(json.dumps(anp_request, indent=2, ensure_ascii=False))
            
            response = requests.post(
                f"{self.anp_gateway_url}/anp-to-mcp",
                json=anp_request
            )
            
            if response.status_code != 200:
                print(f"ANP转换失败: {response.status_code}")
                print(response.text)
                return
                
            conversion_result = response.json()
            print("\n转换结果:")
            print(json.dumps(conversion_result, indent=2, ensure_ascii=False))
            
            if not conversion_result.get("success"):
                print("转换失败")
                return
                
            # 2. 发送MCP请求到天气服务
            mcp_request = conversion_result["mcp_request"]
            print("\n2. 发送MCP请求到天气服务:")
            print(json.dumps(mcp_request, indent=2, ensure_ascii=False))
            
            weather_response = requests.post(
                self.weather_service_url,
                json=mcp_request
            )
            
            if weather_response.status_code != 200:
                print(f"天气服务请求失败: {weather_response.status_code}")
                print(weather_response.text)
                return
                
            mcp_response = weather_response.json()
            print("\n天气服务响应:")
            print(json.dumps(mcp_response, indent=2, ensure_ascii=False))
            
            # 3. 将MCP响应转换回ANP格式
            anp_conversion_response = requests.post(
                f"{self.anp_gateway_url}/mcp-to-anp",
                json=mcp_response
            )
            
            if anp_conversion_response.status_code != 200:
                print(f"MCP响应转换失败: {anp_conversion_response.status_code}")
                print(anp_conversion_response.text)
                return
                
            final_response = anp_conversion_response.json()
            print("\n3. 最终ANP响应:")
            print(json.dumps(final_response, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"测试过程出错: {str(e)}")

def main():
    test = WeatherIntegrationTest()
    
    # 1. 注册DID
    if test.register_did():
        print("DID注册成功，开始测试天气查询...")
        # 2. 测试天气查询
        test.test_get_weather()
    else:
        print("DID注册失败，测试终止")

if __name__ == "__main__":
    main() 