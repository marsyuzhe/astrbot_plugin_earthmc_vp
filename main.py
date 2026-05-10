mport json
import os
import aiohttp
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register

BASE_DIR = os.path.dirname(__file__)
with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

@register("earthmc_vp", "marsyuzhe", "EarthMC 查询插件", "2.1.0")
class EarthMCPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api = "https://api.earthmc.net/v4"

    async def get(self, path):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.api}/{path}") as r:
                return await r.json() if r.status == 200 else None

    async def post(self, path, query):
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{self.api}/{path}", json={"query": [query]}) as r:
                return await r.json() if r.status == 200 else None

    @filter.command("vp")
    async def vp(self, event):
        data = await self.get("/")
        if not data:
            yield event.plain_result("❌ 获取失败")
            return
        vp = data["voteParty"]
        cur = vp["target"] - vp["numRemaining"]
        pct = round(cur / vp["target"] * 100, 1)
        bar = "█" * int(20 * cur / vp["target"]) + "░" * (20 - int(20 * cur / vp["target"]))
        yield event.plain_result(
            f"🗳️ VoteParty\n"
            f"[{bar}] {pct}%\n"
            f"进度: {cur} / {vp['target']}\n"
            f"剩余: {vp['numRemaining']} 票\n"
            f"在线: {data['stats']['numOnlinePlayers']} 人"
        )

    @filter.command("res")
    async def res(self, event, name: str = None):
        if not name:
            yield event.plain_result("用法: /res <玩家名>")
            return
        data = await self.post("players", name)
        if not data or len(data) == 0:
            yield event.plain_result(f"❌ 未找到玩家: {name}")
            return
        p = data[0]
        st = p.get("status", {})
        yield event.plain_result(
            f"👤 {p['name']}\n"
            f"城镇: {p['town']['name'] if p.get('town') else '无'}\n"
            f"国家: {p['nation']['name'] if p.get('nation') else '无'}\n"
            f"余额: {p.get('stats', {}).get('balance', 0)} G\n"
            f"状态: {'在线 🟢' if st.get('isOnline') else '离线 🔴'}\n"
            f"身份: {'市长 ' if st.get('isMayor') else ''}{'国王' if st.get('isKing') else ''}"
        )

    @filter.command("town")
    async def town(self, event, name: str = None):
        if not name:
            yield event.plain_result("用法: /town <城镇名>")
            return
        data = await self.post("towns", name)
        if not data or len(data) == 0:
            yield event.plain_result(f"❌ 未找到城镇: {name}")
            return
        t = data[0]
        st = t.get("status", {})
        pf = t.get("perms", {}).get("flags", {})
        yield event.plain_result(
            f"🏘️ {t['name']}\n"
            f"市长: {t['mayor']['name']}\n"
            f"国家: {t['nation']['name'] if t.get('nation') else '无'}\n"
            f"居民: {t['stats']['numResidents']}  格数: {t['stats']['numTownBlocks']}\n"
            f"余额: {t['stats']['balance']} G\n"
            f"状态: {'首都 ' if st.get('isCapital') else ''}{'开放 ' if st.get('isOpen') else ''}{'中立' if st.get('isNeutral') else ''}\n"
            f"PvP: {'✅' if pf.get('pvp') else '❌'}  公告: {t.get('board') or '无'}"
        )
