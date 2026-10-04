"""
WeRSS 级联系统使用示例

演示如何使用Python客户端与父节点交互
"""

import asyncio
import httpx
import json
from typing import Optional


class CascadeParentClient:
    """父节点客户端示例"""
    
    def __init__(self, parent_url: str, jwt_token: str):
        self.parent_url = parent_url.rstrip('/')
        self.token = jwt_token
        self.timeout = 30.0
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送HTTP请求"""
        url = f"{self.parent_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self._get_headers())
            elif method.upper() == "POST":
                response = await client.post(url, headers=self._get_headers(), json=data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=self._get_headers(), json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=self._get_headers())
            
            return response.json()
    
    async def create_child_node(self, name: str, description: str = "", api_url: str = "") -> dict:
        """创建子节点"""
        data = {
            "node_type": 1,
            "name": name,
            "description": description,
            "api_url": api_url
        }
        return await self._request("POST", "/api/v1/cascade/nodes", data)
    
    async def generate_credentials(self, node_id: str) -> dict:
        """生成子节点凭证"""
        return await self._request("POST", f"/api/v1/cascade/nodes/{node_id}/credentials")
    
    async def list_nodes(self, node_type: Optional[int] = None) -> dict:
        """获取节点列表"""
        params = {}
        if node_type is not None:
            params["node_type"] = node_type
        return await self._request("GET", "/api/v1/cascade/nodes")
    
    async def test_connection(self, node_id: str, api_url: str, api_key: str, api_secret: str) -> dict:
        """测试子节点连接"""
        data = {
            "api_url": api_url,
            "api_key": api_key,
            "api_secret": api_secret
        }
        return await self._request("POST", f"/api/v1/cascade/nodes/{node_id}/test-connection", data)
    
    async def get_sync_logs(self, node_id: Optional[str] = None, limit: int = 50) -> dict:
        """获取同步日志"""
        params = {"limit": limit}
        if node_id:
            params["node_id"] = node_id
        return await self._request("GET", "/api/v1/cascade/sync-logs", None)


class CascadeChildClient:
    """子节点客户端示例"""
    
    def __init__(self, parent_url: str, api_key: str, api_secret: str):
        self.parent_url = parent_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = 30.0
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"AK-SK {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送HTTP请求"""
        url = f"{self.parent_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=self._get_headers())
            elif method.upper() == "POST":
                response = await client.post(url, headers=self._get_headers(), json=data)
            
            return response.json()
    
    async def pull_feeds(self) -> dict:
        """拉取公众号数据"""
        return await self._request("GET", "/api/v1/cascade/feeds")
    
    async def pull_message_tasks(self) -> dict:
        """拉取消息任务"""
        return await self._request("GET", "/api/v1/cascade/message-tasks")
    
    async def report_task_result(self, task_id: str, results: list) -> dict:
        """上报任务执行结果"""
        data = {
            "task_id": task_id,
            "results": results,
            "timestamp": "2024-01-01T00:00:00"
        }
        return await self._request("POST", "/api/v1/cascade/report-result", data)
    
    async def send_heartbeat(self) -> dict:
        """发送心跳"""
        return await self._request("POST", "/api/v1/cascade/heartbeat")


async def example_parent_operations():
    """父节点操作示例"""
    
    # 配置父节点地址和JWT Token
    PARENT_URL = "http://localhost:8001"
    JWT_TOKEN = "your-jwt-token-here"
    
    client = CascadeParentClient(PARENT_URL, JWT_TOKEN)
    
    print("=== 父节点操作示例 ===\n")
    
    # 1. 创建子节点
    print("1. 创建子节点...")
    result = await client.create_child_node(
        name="子节点示例",
        description="用于演示级联系统",
        api_url="http://child-node:8001"
    )
    print(f"   结果: {json.dumps(result, indent=2, ensure_ascii=False)}\n")
    
    if result.get("code") == 0:
        node_id = result["data"]["id"]
        
        # 2. 生成凭证
        print("2. 生成子节点凭证...")
        credentials = await client.generate_credentials(node_id)
        print(f"   凭证: {json.dumps(credentials, indent=2, ensure_ascii=False)}\n")
        
        # 保存凭证供子节点使用
        api_key = credentials["data"]["api_key"]
        api_secret = credentials["data"]["api_secret"]
        
        # 3. 查看节点列表
        print("3. 查看节点列表...")
        nodes = await client.list_nodes()
        print(f"   节点数量: {len(nodes['data'])}\n")
        
        # 4. 查看同步日志
        print("4. 查看同步日志...")
        logs = await client.get_sync_logs(limit=10)
        print(f"   日志数量: {len(logs['data']['list'])}\n")


async def example_child_operations(api_key: str, api_secret: str):
    """子节点操作示例"""
    
    # 配置父节点地址和子节点凭证
    PARENT_URL = "http://localhost:8001"
    
    client = CascadeChildClient(PARENT_URL, api_key, api_secret)
    
    print("=== 子节点操作示例 ===\n")
    
    # 1. 拉取公众号数据
    print("1. 拉取公众号数据...")
    feeds = await client.pull_feeds()
    print(f"   公众号数量: {len(feeds.get('data', []))}")
    if feeds.get('data'):
        print(f"   第一个公众号: {feeds['data'][0].get('mp_name')}\n")
    
    # 2. 拉取消息任务
    print("2. 拉取消息任务...")
    tasks = await client.pull_message_tasks()
    print(f"   任务数量: {len(tasks.get('data', []))}")
    if tasks.get('data'):
        print(f"   第一个任务: {tasks['data'][0].get('name')}\n")
    
    # 3. 发送心跳
    print("3. 发送心跳...")
    heartbeat = await client.send_heartbeat()
    print(f"   心跳结果: {heartbeat.get('message')}\n")
    
    # 4. 上报任务结果（示例）
    print("4. 上报任务结果...")
    result_data = [{
        "mp_id": "mp-uuid",
        "mp_name": "测试公众号",
        "article_count": 10,
        "success_count": 10,
        "timestamp": "2024-01-01T10:00:00"
    }]
    report = await client.report_task_result("task-uuid", result_data)
    print(f"   上报结果: {report.get('message')}\n")


async def example_complete_workflow():
    """完整工作流示例"""
    
    print("="*60)
    print("WeRSS 级联系统完整工作流示例")
    print("="*60)
    print()
    
    PARENT_URL = "http://localhost:8001"
    JWT_TOKEN = "your-jwt-token-here"
    
    # 步骤1: 父节点创建子节点
    print("【步骤1】父节点创建子节点")
    parent_client = CascadeParentClient(PARENT_URL, JWT_TOKEN)
    
    node_result = await parent_client.create_child_node(
        name="工作节点1",
        description="生产环境工作节点",
        api_url="http://worker-1:8001"
    )
    
    if node_result.get("code") == 0:
        node_id = node_result["data"]["id"]
        print(f"   子节点ID: {node_id}")
        
        # 步骤2: 生成凭证
        print("\n【步骤2】生成子节点凭证")
        credentials = await parent_client.generate_credentials(node_id)
        api_key = credentials["data"]["api_key"]
        api_secret = credentials["data"]["api_secret"]
        print(f"   API Key: {api_key}")
        print(f"   API Secret: {api_secret}")
        
        # 步骤3: 子节点连接并同步数据
        print("\n【步骤3】子节点连接父节点")
        child_client = CascadeChildClient(PARENT_URL, api_key, api_secret)
        
        # 发送心跳
        await child_client.send_heartbeat()
        print("   心跳发送成功")
        
        # 拉取公众号
        feeds = await child_client.pull_feeds()
        print(f"   拉取到 {len(feeds.get('data', []))} 个公众号")
        
        # 拉取任务
        tasks = await child_client.pull_message_tasks()
        print(f"   拉取到 {len(tasks.get('data', []))} 个任务")
        
        # 步骤4: 模拟任务执行并上报结果
        print("\n【步骤4】上报任务执行结果")
        if tasks.get('data'):
            task_id = tasks['data'][0]['id']
            result = [{
                "mp_id": "test-mp-id",
                "mp_name": "测试公众号",
                "article_count": 5,
                "success_count": 5,
                "timestamp": "2024-01-01T10:00:00"
            }]
            await child_client.report_task_result(task_id, result)
            print(f"   任务 {task_id} 结果已上报")
        
        # 步骤5: 父节点查看同步日志
        print("\n【步骤5】父节点查看同步日志")
        logs = await parent_client.get_sync_logs(node_id=node_id, limit=5)
        print(f"   最近的同步操作:")
        for log in logs['data']['list'][:3]:
            print(f"     - {log['operation']} ({log['direction']}): {log['data_count']}条数据")
        
        print("\n" + "="*60)
        print("工作流程完成!")
        print("="*60)


async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "parent":
            await example_parent_operations()
        elif mode == "child":
            if len(sys.argv) < 4:
                print("用法: python cascade_example.py child <api_key> <api_secret>")
                return
            api_key = sys.argv[2]
            api_secret = sys.argv[3]
            await example_child_operations(api_key, api_secret)
        elif mode == "workflow":
            await example_complete_workflow()
        else:
            print("用法:")
            print("  python cascade_example.py parent    - 父节点操作示例")
            print("  python cascade_example.py child <ak> <sk> - 子节点操作示例")
            print("  python cascade_example.py workflow  - 完整工作流示例")
    else:
        print("WeRSS 级联系统使用示例")
        print()
        print("用法:")
        print("  python cascade_example.py parent    - 父节点操作示例")
        print("  python cascade_example.py child <ak> <sk> - 子节点操作示例")
        print("  python cascade_example.py workflow  - 完整工作流示例")
        print()
        print("注意: 请将 JWT_TOKEN 替换为实际的认证令牌")


if __name__ == "__main__":
    asyncio.run(main())
