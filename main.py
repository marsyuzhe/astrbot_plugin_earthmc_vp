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
