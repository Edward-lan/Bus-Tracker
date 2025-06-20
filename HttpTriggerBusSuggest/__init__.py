
import logging
import os
import azure.functions as func
import requests
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    location = req.params.get('location')
    if not location:
        return func.HttpResponse("請提供 ?location=轉運站 或 校區", status_code=400)

    now = datetime.now()

    # === 校車班表（簡化） ===
    school_schedule = {
        "大巴:轉運站,A7,校區": ["07:15", "07:35", "16:15", "16:30", "17:35", "18:00", "19:00", "20:00", "21:00", "22:00", "23:40"],
        "大巴:校區,A7,轉運站": ["15:50", "16:10", "16:55", "17:35", "18:20", "19:20", "20:20", "21:20", "22:20"],
    }

    location_routes = {
        "轉運站": ["大巴:轉運站,A7,校區", "967", "967直"],
        "校區": ["大巴:校區,A7,轉運站", "967", "967直"]
    }

    def suggest_school_bus(now):
        suggestions = []
        now_time = now.time()
        for route in location_routes.get(location, []):
            if route.startswith("大巴"):
                times = []
                for t in school_schedule.get(route, []):
                    try:
                        times.append(datetime.strptime(t, "%H:%M").time())
                    except:
                        continue
                upcoming = [t for t in times if t > now_time]
                if upcoming:
                    next_time = upcoming[0]
                    wait_min = (datetime.combine(now.date(), next_time) - now).seconds // 60
                    suggestions.append((route, next_time.strftime("%H:%M"), wait_min))
        return suggestions

    def get_token():
        url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        headers = { "Content-Type": "application/x-www-form-urlencoded" }
        data = {
            "grant_type": "client_credentials",
            "client_id": os.environ["TDX_CLIENT_ID"],
            "client_secret": os.environ["TDX_CLIENT_SECRET"]
        }
        r = requests.post(url, headers=headers, data=data)
        return r.json()["access_token"]

    def get_eta(token, route, stop_id="NWT163345"):
        url = f"https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/NewTaipei/{route}?$filter=StopID eq '{stop_id}'&$format=JSON"
        headers = { "Authorization": f"Bearer {token}" }
        r = requests.get(url, headers=headers)
        j = r.json()
        for item in j:
            if item.get("EstimateTime"):
                return int(item["EstimateTime"]) // 60
        return None

    def suggest_bus(token):
        results = []
        if location in location_routes:
            for route in location_routes[location]:
                if route.startswith("967"):
                    wait = get_eta(token, route)
                    if wait is not None:
                        results.append((f"公車:{route}", "-", wait))
        return results

    try:
        token = get_token()
        result = suggest_school_bus(now) + suggest_bus(token)
        result.sort(key=lambda x: x[2])
        lines = [f"{r[0]}｜發車:{r[1]}｜等待:{r[2]} 分" for r in result]
        return func.HttpResponse("\n".join(lines), status_code=200)
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
