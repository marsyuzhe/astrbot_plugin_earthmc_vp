import asyncio
import json
import os

import aiohttp

from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register

BASE_DIR = os.path.dirname(__file__)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

CHECK_INTERVAL = CONFIG["check_interval"]
ALERT_THRESHOLD = CONFIG["alert_threshold"]

API_URL = "https://api.earthmc.net/v4/"


@register(
    "earthmc_vp",
    "YourName",
    "EarthMC VoteParty Monitor",
    "1.0.0"
)
class EarthMCVPPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)

        self.last_alert = None
        self.last_trigger = False

        asyncio.create_task(
            self.monitor_loop()
        )

    async def fetch_vp(self):

        try:
            async with aiohttp.ClientSession() as session:

                async with session.get(API_URL) as resp:

                    if resp.status != 200:
                        return None

                    data = await resp.json()

                    vp = data["voteParty"]

                    target = vp["target"]
                    remaining = vp["numRemaining"]

                    current = target - remaining

                    online = data["stats"]["numOnlinePlayers"]

                    return {
                        "target": target,
                        "remaining": remaining,
                        "current": current,
                        "online": online
                    }

        except Exception as e:
            print("EarthMC API Error:", e)
            return None

    async def monitor_loop(self):

        await asyncio.sleep(10)

        while True:

            data = await self.fetch_vp()

            if data:

                remaining = data["remaining"]

                # 接近提醒
                if remaining <= ALERT_THRESHOLD:

                    if self.last_alert != remaining:

                        self.last_alert = remaining

                        message = (
                            f"【EarthMC VoteParty】\n"
                            f"当前票数: {data['current']} / {data['target']}\n"
                            f"剩余票数: {remaining}\n"
                            f"在线人数: {data['online']}"
                        )

                        print(message)

                # VoteParty 触发
                if remaining == 0:

                    if not self.last_trigger:

                        self.last_trigger = True

                        message = (
                            "【EarthMC】\n"
                            "VoteParty 已触发！\n"
                            "快上线领取奖励！"
                        )

                        print(message)

                else:
                    self.last_trigger = False

            await asyncio.sleep(CHECK_INTERVAL)

    # =========================
    # /vp
    # =========================
    @filter.command("vp")
    async def vp(self, event):

        data = await self.fetch_vp()

        if not data:

            yield event.plain_result(
                "获取 VoteParty 数据失败"
            )

            return

        msg = (
            f"【EarthMC VoteParty】\n"
            f"当前票数: {data['current']} / {data['target']}\n"
            f"剩余票数: {data['remaining']}\n"
            f"在线人数: {data['online']}"
        )

        yield event.plain_result(msg)
# ... 保留原有的 import 和 CONFIG 加载代码 ...

class EarthMCVPPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_base = "https://api.earthmc.net/v4/aurora" # 建议指定服务器，如 aurora
        # ... 保留原有的 monitor_loop 启动 ...

    async def fetch_data(self, endpoint: str):
        """通用数据获取函数"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/{endpoint}") as resp:
                    if resp.status != 200: return None
                    return await resp.json()
        except Exception as e:
            print(f"EarthMC API Error ({endpoint}):", e)
            return None

    # 1. 城镇查询 (/town [名称])
    @filter.command("town")
    async def town_query(self, event, town_name: str = None):
        if not town_name:
            yield event.plain_result("请输入城镇名称，例如: /town London")
            return
        
        data = await self.fetch_data(f"towns/{town_name}")
        if not data:
            yield event.plain_result(f"未找到城镇: {town_name}")
            return

        msg = (
            f"🏘️ 城镇: {data['name']}\n"
            f"市长: {data['mayor']}\n"
            f"国家: {data['nation'] if data['nation'] else '无'}\n"
            f"居民数: {len(data['residents'])}\n"
            f"余额: {data['stats']['balance']}G"
        )
        yield event.plain_result(msg)

    # 2. 玩家查询 (/player [名称])
    @filter.command("player")
    async def player_query(self, event, player_name: str = None):
        if not player_name:
            yield event.plain_result("请输入玩家名称")
            return
            
        data = await self.fetch_data(f"residents/{player_name}")
        if not data:
            yield event.plain_result(f"未找到玩家: {player_name}")
            return

        msg = (
            f"👤 玩家: {data['name']}\n"
            f"城镇: {data['town']}\n"
            f"等级: {data['rank'] if data['rank'] else '居民'}\n"
            f"余额: {data['stats']['balance']}G\n"
            f"状态: {'在线' if data['status']['isOnline'] else '离线'}"
        )
        yield event.plain_result(msg)

    # 3. 在线人数 (/online)
    @filter.command("online")
    async def online_list(self, event):
        data = await self.fetch_data("") # 获取概览
        if not data: return
        
        msg = f"📊 EarthMC 当前在线: {data['stats']['numOnlinePlayers']} 人"
        yield event.plain_result(msg)

# =========================
    # /res [玩家名]
    # =========================
    @filter.command("res")
    async def res_query(self, event, player_name: str = None):
        """查询玩家(Resident)详细信息"""
        if not player_name:
            yield event.plain_result("💡 请输入玩家名，例如：/res marsyuzhe")
            return

        # 这里的 API 路径通常需要加上服务器名，EarthMC 目前主服是 aurora
        # 如果你想更通用，可以把 aurora 写进 config.json
        RES_API = f"https://api.earthmc.net/v4/aurora/residents/{player_name}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RES_API) as resp:
                    if resp.status == 404:
                        yield event.plain_result(f"❌ 未找到玩家: {player_name}")
                        return
                    if resp.status != 200:
                        yield event.plain_result("🛑 API 服务暂时不可用")
                        return

                    data = await resp.json()

                    # 解析数据
                    town = data.get('town', '无')
                    nation = data.get('nation', '无')
                    rank = data.get('rank', '居民')
                    balance = data.get('stats', {}).get('balance', 0)
                    is_online = "在线 🟢" if data.get('status', {}).get('isOnline') else "离线 🔴"
                    
                    # 格式化输出
                    msg = (
                        f"👤 【EarthMC 玩家查询】\n"
                        f"ID: {data['name']}\n"
                        f"城镇: {town}\n"
                        f"国家: {nation}\n"
                        f"等级: {rank}\n"
                        f"余额: {balance}G\n"
                        f"状态: {is_online}"
                    )
                    
                    yield event.plain_result(msg)

        except Exception as e:
            print(f"EarthMC Res API Error: {e}")
            yield event.plain_result("⚠️ 查询出错，请稍后再试")
