# @title ZKFC S3 全能数据助手 (Colab版)
# @markdown 点击左侧播放键运行。支持查询：玩家、谱面、比赛(MP Link)。

import requests
import json
import time
from datetime import datetime

# === 全局变量 ===
TOKEN = None
CLIENT_ID = ""     # 如果不想每次都输，可以在这里填好
CLIENT_SECRET = "" # 如果不想每次都输，可以在这里填好

def get_token():
    global TOKEN, CLIENT_ID, CLIENT_SECRET
    if TOKEN: return TOKEN
    
    print(">>> 正在进行 osu! API 认证...")
    if not CLIENT_ID or not CLIENT_SECRET:
        CLIENT_ID = input("请输入 Client ID: ").strip()
        CLIENT_SECRET = input("请输入 Client Secret: ").strip()

    try:
        resp = requests.post('https://osu.ppy.sh/oauth/token', data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials',
            'scope': 'public'
        })
        
        if resp.status_code != 200:
            print(f"❌ 认证失败: {resp.text}")
            return None

        data = resp.json()
        TOKEN = data['access_token']
        print("✅ 认证成功！Token 已缓存。\n")
        return TOKEN
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return None

def fetch_player(user_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    print(f"🔍 正在查询玩家: {user_id}...")
    try:
        r = requests.get(f'https://osu.ppy.sh/api/v2/users/{user_id}/osu', headers=headers)
        if r.status_code != 200: return print(f"❌ 失败 ({r.status_code})")
        
        d = r.json()
        s = d.get('statistics', {})
        
        res = {
            "id": d['id'],
            "name": d['username'],
            "rank": s.get('global_rank', 0),
            "country": d['country_code'],
            "avatar": d['avatar_url'],
            "cover": d['cover_url'],
            "pp": round(s.get('pp', 0)),
            "tth": f"{s.get('total_hits', 0):,}",
            "bp1": 0, "tier": "TBD", "intro": "No intro.",
            "stats": [50, 50, 50, 50, 50]
        }
        print_json(res, "PLAYER_REGISTRY")
    except Exception as e: print(f"❌ 错误: {e}")

def fetch_map(bid, mod="NM1"):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    print(f"🔍 正在查询谱面: {bid}...")
    try:
        r = requests.get(f'https://osu.ppy.sh/api/v2/beatmaps/{bid}', headers=headers)
        if r.status_code != 200: return print(f"❌ 失败 ({r.status_code})")
        
        d = r.json()
        bs = d['beatmapset']
        
        res = {
            "mod": mod, "bid": d['id'],
            "title": bs['title'], "artist": bs['artist'], "difficulty": d['version'],
            "star": d['difficulty_rating'], "cover": bs['covers']['cover'],
            "cs": d['cs'], "ar": d['ar'], "od": d['accuracy'], "bpm": d['bpm'],
            "length": f"{d['total_length']//60}:{d['total_length']%60:02d}",
            "comment": "暂无评价",
            "stats": { "pick": 0, "ban": 0, "scores": {"max": {"val":0,"holder":"-"}, "min": {"val":0,"holder":"-"}, "avg": 0} }
        }
        print_json(res, "MAPPOOLS -> maps")
    except Exception as e: print(f"❌ 错误: {e}")

def fetch_match(mp_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    print(f"🔍 正在分析比赛 MP: {mp_id}...")
    try:
        r = requests.get(f'https://osu.ppy.sh/api/v2/matches/{mp_id}', headers=headers)
        if r.status_code != 200: return print(f"❌ 失败 ({r.status_code})")
        
        d = r.json()
        match = d['match']
        events = d['events']
        
        # 简化时间
        try: dt = datetime.strptime(match['start_time'], "%Y-%m-%dT%H:%M:%SZ"); time_str = dt.strftime("%Y/%m/%d %H:%M")
        except: time_str = match['start_time']

        s_blue, s_red = 0, 0
        picks = []
        
        for e in events:
            game = e.get('game')
            if not game or not game['end_time']: continue
            
            # 计算单图比分
            scores = game['scores']
            t_blue = sum(s['score'] for s in scores if s['match']['team'] == 'blue')
            t_red = sum(s['score'] for s in scores if s['match']['team'] == 'red')
            
            if t_blue > t_red: s_blue += 1
            else: s_red += 1
            
            picks.append({
                "bid": game['beatmap']['id'],
                "title": f"{game['beatmap']['beatmapset']['title']} [{game['beatmap']['version']}]",
                "cover": game['beatmap']['beatmapset']['covers']['cover'],
                "winner": "Blue" if t_blue > t_red else "Red",
                "score": f"{t_blue:,} - {t_red:,}",
                "mods": game['mods']
            })

        res = {
            "id": f"QF #{mp_id}", "time": time_str,
            "matchLink": f"https://osu.ppy.sh/community/matches/{mp_id}",
            "mpLink": f"https://osu.ppy.sh/community/matches/{mp_id}",
            "status": "Finished" if match['end_time'] else "Live",
            "teamA": 1, "teamB": 2, "scoreA": s_blue, "scoreB": s_red,
            "details": { "bans": [], "picks": picks }
        }
        print_json(res, "BRACKET_DATA -> matches")
    except Exception as e: print(f"❌ 错误: {e}")

def print_json(data, target):
    print(f"\n📋 === 复制下方代码到 {target} ===")
    print(json.dumps(data, ensure_ascii=False, indent=4))
    print("==================================\n")

# === 主循环 ===
if __name__ == "__main__":
    if get_token():
        print("💡 指令说明:")
        print("  - 查玩家: p <uid>      (例: p 12345)")
        print("  - 查谱面: b <bid> <mod> (例: b 99999 NM1)")
        print("  - 查比赛: m <mp_id>    (例: m 110065184)")
        print("  - 退出: q")
        
        while True:
            cmd = input("\n请输入指令: ").strip().split()
            if not cmd: continue
            if cmd[0] == 'q': break
            
            if cmd[0] == 'p' and len(cmd)>1: fetch_player(cmd[1])
            elif cmd[0] == 'b' and len(cmd)>1: fetch_map(cmd[1], cmd[2] if len(cmd)>2 else "NM1")
            elif cmd[0] == 'm' and len(cmd)>1: fetch_match(cmd[1])
            else: print("⚠️ 指令格式错误")# @title ZKFC S3 全能数据助手 (Colab版)
# @markdown 点击左侧播放键运行。支持查询：玩家、谱面、比赛(MP Link)。

import requests
import json
import time
from datetime import datetime

# === 全局变量 ===
TOKEN = None
CLIENT_ID = ""     # 如果不想每次都输，可以在这里填好
CLIENT_SECRET = "" # 如果不想每次都输，可以在这里填好

def get_token():
    global TOKEN, CLIENT_ID, CLIENT_SECRET
    if TOKEN: return TOKEN
    
    print(">>> 正在进行 osu! API 认证...")
    if not CLIENT_ID or not CLIENT_SECRET:
        CLIENT_ID = input("请输入 Client ID: ").strip()
        CLIENT_SECRET = input("请输入 Client Secret: ").strip()

    try:
        resp = requests.post('https://osu.ppy.sh/oauth/token', data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials',
            'scope': 'public'
        })
        
        if resp.status_code != 200:
            print(f"❌ 认证失败: {resp.text}")
            return None

        data = resp.json()
        TOKEN = data['access_token']
        print("✅ 认证成功！Token 已缓存。\n")
        return TOKEN
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return None

def fetch_player(user_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    print(f"🔍 正在查询玩家: {user_id}...")
    try:
        r = requests.get(f'https://osu.ppy.sh/api/v2/users/{user_id}/osu', headers=headers)
        if r.status_code != 200: return print(f"❌ 失败 ({r.status_code})")
        
        d = r.json()
        s = d.get('statistics', {})
        
        res = {
            "id": d['id'],
            "name": d['username'],
            "rank": s.get('global_rank', 0),
            "country": d['country_code'],
            "avatar": d['avatar_url'],
            "cover": d['cover_url'],
            "pp": round(s.get('pp', 0)),
            "tth": f"{s.get('total_hits', 0):,}",
            "bp1": 0, "tier": "TBD", "intro": "No intro.",
            "stats": [50, 50, 50, 50, 50]
        }
        print_json(res, "PLAYER_REGISTRY")
    except Exception as e: print(f"❌ 错误: {e}")

def fetch_map(bid, mod="NM1"):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    print(f"🔍 正在查询谱面: {bid}...")
    try:
        r = requests.get(f'https://osu.ppy.sh/api/v2/beatmaps/{bid}', headers=headers)
        if r.status_code != 200: return print(f"❌ 失败 ({r.status_code})")
        
        d = r.json()
        bs = d['beatmapset']
        
        res = {
            "mod": mod, "bid": d['id'],
            "title": bs['title'], "artist": bs['artist'], "difficulty": d['version'],
            "star": d['difficulty_rating'], "cover": bs['covers']['cover'],
            "cs": d['cs'], "ar": d['ar'], "od": d['accuracy'], "bpm": d['bpm'],
            "length": f"{d['total_length']//60}:{d['total_length']%60:02d}",
            "comment": "暂无评价",
            "stats": { "pick": 0, "ban": 0, "scores": {"max": {"val":0,"holder":"-"}, "min": {"val":0,"holder":"-"}, "avg": 0} }
        }
        print_json(res, "MAPPOOLS -> maps")
    except Exception as e: print(f"❌ 错误: {e}")

def fetch_match(mp_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    print(f"🔍 正在分析比赛 MP: {mp_id}...")
    try:
        r = requests.get(f'https://osu.ppy.sh/api/v2/matches/{mp_id}', headers=headers)
        if r.status_code != 200: return print(f"❌ 失败 ({r.status_code})")
        
        d = r.json()
        match = d['match']
        events = d['events']
        
        # 简化时间
        try: dt = datetime.strptime(match['start_time'], "%Y-%m-%dT%H:%M:%SZ"); time_str = dt.strftime("%Y/%m/%d %H:%M")
        except: time_str = match['start_time']

        s_blue, s_red = 0, 0
        picks = []
        
        for e in events:
            game = e.get('game')
            if not game or not game['end_time']: continue
            
            # 计算单图比分
            scores = game['scores']
            t_blue = sum(s['score'] for s in scores if s['match']['team'] == 'blue')
            t_red = sum(s['score'] for s in scores if s['match']['team'] == 'red')
            
            if t_blue > t_red: s_blue += 1
            else: s_red += 1
            
            picks.append({
                "bid": game['beatmap']['id'],
                "title": f"{game['beatmap']['beatmapset']['title']} [{game['beatmap']['version']}]",
                "cover": game['beatmap']['beatmapset']['covers']['cover'],
                "winner": "Blue" if t_blue > t_red else "Red",
                "score": f"{t_blue:,} - {t_red:,}",
                "mods": game['mods']
            })

        res = {
            "id": f"QF #{mp_id}", "time": time_str,
            "matchLink": f"https://osu.ppy.sh/community/matches/{mp_id}",
            "mpLink": f"https://osu.ppy.sh/community/matches/{mp_id}",
            "status": "Finished" if match['end_time'] else "Live",
            "teamA": 1, "teamB": 2, "scoreA": s_blue, "scoreB": s_red,
            "details": { "bans": [], "picks": picks }
        }
        print_json(res, "BRACKET_DATA -> matches")
    except Exception as e: print(f"❌ 错误: {e}")

def print_json(data, target):
    print(f"\n📋 === 复制下方代码到 {target} ===")
    print(json.dumps(data, ensure_ascii=False, indent=4))
    print("==================================\n")

# === 主循环 ===
if __name__ == "__main__":
    if get_token():
        print("💡 指令说明:")
        print("  - 查玩家: p <uid>      (例: p 12345)")
        print("  - 查谱面: b <bid> <mod> (例: b 99999 NM1)")
        print("  - 查比赛: m <mp_id>    (例: m 110065184)")
        print("  - 退出: q")
        
        while True:
            cmd = input("\n请输入指令: ").strip().split()
            if not cmd: continue
            if cmd[0] == 'q': break
            
            if cmd[0] == 'p' and len(cmd)>1: fetch_player(cmd[1])
            elif cmd[0] == 'b' and len(cmd)>1: fetch_map(cmd[1], cmd[2] if len(cmd)>2 else "NM1")
            elif cmd[0] == 'm' and len(cmd)>1: fetch_match(cmd[1])
            else: print("⚠️ 指令格式错误")