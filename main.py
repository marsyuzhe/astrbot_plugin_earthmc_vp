import asyncio
import json
import os
import aiohttp
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register

# 配置加载（保持你原来的逻辑）
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

CHECK_INTERVAL = CONFIG.get("check_interval", 60)
ALERT_THRESHOLD = CONFIG.get("alert_threshold", 100)

@register("earthmc_vp", "marsyuzhe", "EarthMC 综合查询插件", "1.1.0")
class EarthMCVPPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.last_alert = None
        self.last_trigger = False
        # 文档指出基础 URL 为 https://api.earthmc.net/v4/
        self.api_base = "https://api.earthmc.net/v4"
        
        asyncio.create_task(self.monitor_loop())

    async def fetch_api(self, endpoint: str, method: str = "GET", payload: dict = None):
        """通用的 API 请求工具，支持 GET 和 POST"""
        url = f"{self.api_base}/{endpoint}".strip("/")
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "POST":
                    async with session.post(url, json=payload) as resp:
                        return await resp.json() if resp.status == 200 else None
                else:
                    async with session.get(url) as resp:
                        return await resp.json() if resp.status == 200 else None
        except Exception as e:
            print(f"EarthMC API 错误: {e}")
            return None

    # --- 修复 /vp 报错 ---
    async def fetch_vp(self):
        """重新实现被删掉的 fetch_vp"""
        data = await self.fetch_api("/") # 访问根路径获取服务器概览
        if not data or "voteParty" not in data:
            return None
        
        vp = data["voteParty"]
        return {
            "target": vp["target"],
            "remaining": vp["numRemaining"],
            "current": vp["target"] - vp["numRemaining"],
            "online": data["stats"]["numOnlinePlayers"]
        }

    @filter.command("vp")
    async def vp_command(self, event):
        data = await self.fetch_vp()
        if not data:
            yield event.plain_result("❌ 获取 VoteParty 数据失败")
            return
        msg = (f"【EarthMC VoteParty】\n"
               f"进度: {data['current']} / {data['target']}\n"
               f"剩余: {data['remaining']}\n"
               f"在线: {data['online']}")
        yield event.plain_result(msg)

    # --- 实现图二内容：玩家查询 /res ---
    @filter.command("res")
    async def res_query(self, event, name: str = None):
        if not name:
            yield event.plain_result("请输入玩家名")
            return
        
        # 使用 POST 减少返回数据量
        payload = {
            "query": [name],
            "template": {
                "name": True, "town": True, "nation": True,
                "status": True, "stats": True, "rank": True
            }
        }
        res_list = await self.fetch_api("/players", method="POST", payload=payload)
        
        if not res_list or len(res_list) == 0:
            yield event.plain_result(f"🔍 未找到玩家: {name}")
            return

        p = res_list[0]
        online_status = "在线 🟢" if p['status']['isOnline'] else "离线 🔴"
        msg = (f"👤 玩家: {p['name']}\n"
               f"城镇: {p['town']['name'] if p['town'] else '无'}\n"
               f"国家: {p['nation']['name'] if p['nation'] else '无'}\n"
               f"余额: {p['stats']['balance']}G\n"
               f"状态: {online_status}")
        yield event.plain_result(msg)

    # --- 实现图二内容：城镇查询 /town ---
    @filter.command("town")
    async def town_query(self, event, name: str = None):
        if not name:
            yield event.plain_result("请输入城镇名")
            return
        
        payload = {"query": [name]} # 查城镇详细信息
        town_list = await self.fetch_api("/towns", method="POST", payload=payload)
        
        if not town_list or len(town_list) == 0:
            yield event.plain_result(f"🏘️ 未找到城镇: {name}")
            return

        t = town_list[0]
        msg = (f"🏘️ 城镇: {t['name']}\n"
               f"市长: {t['mayor']['name']}\n"
               f"国家: {t['nation']['name'] if t['nation'] else '无'}\n"
               f"居民: {t['stats']['numResidents']} 人\n"
               f"余额: {t['stats']['balance']}G")
        yield event.plain_result(msg)

    # --- 自动监控循环 ---
    async def monitor_loop(self):
        while True:
            data = await self.fetch_vp()
            if data:
                remaining = data['remaining']
                # 这里的逻辑你可以根据原有的 alert_threshold 进行提醒发送
                # ... 原有的监控代码 ...
            await asyncio.sleep(CHECK_INTERVAL)
