import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import datetime
import pytz
import requests
import json
import uuid

BI_TOKEN = os.getenv("BI_ACCESS_TOKEN", "").strip()
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "").strip()
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "").strip()

API_URL = "https://bi.th.kex-express.com/cdbi-ext/widget/queryData"

def get_bkk_date_and_hour():
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.datetime.now(tz)
    return now.strftime("%Y%m%d"), str(now.hour), now.strftime("%Y-%m-%d %H:%M:%S")

def query_widget(widget_id, widget_name, date_str, hour_str, zone="BKKC1", page_size=100):
    headers = {
        "accept": "application/json, text/plain, */*",
        "accesstoken": BI_TOKEN,
        "content-type": "application/json",
        "origin": "https://bi.th.kex-express.com",
        "referer": "https://bi.th.kex-express.com/v2/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    payload = {
        "clientQueryId": str(uuid.uuid4()),
        "widgetId": widget_id,
        "widgetName": widget_name,
        "filters": [
            {
                "filterName": "Zone",
                "fieldId": "5b2b6d491e5c44eaa5f523c620096f43",
                "filterType": "=",
                "values": [zone]
            }
        ],
        "params": [
            {"name": "Partition_Day1", "values": date_str},
            {"name": "Partition_Day2", "values": date_str},
            {"name": "Report_time_Choose_lasted_time", "values": f"[{hour_str}]"}
        ],
        "drillFields": [],
        "purge": 0,
        "isDefaultFilter": 0,
        "widgetFields": None
    }
    
    if "all con" in widget_name:
        payload["pageNo"] = 1
        payload["pageSize"] = page_size

    try:
        res = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        data = res.json()
        if data.get("ok"):
            return data.get("data", {}).get("rows", [])
        return []
    except Exception as e:
        print(f"Error query {widget_name}: {e}")
        return []

def send_dingtalk_message(title, markdown_text):
    if not DINGTALK_WEBHOOK:
        return

    url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET and DINGTALK_SECRET != "none":
        timestamp = str(round(time.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = f'{timestamp}\n{DINGTALK_SECRET}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{url}&timestamp={timestamp}&sign={sign}"

    body = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": markdown_text
        }
    }
    requests.post(url, json=body)

def main():
    if not BI_TOKEN:
        print("ERROR: BI_ACCESS_TOKEN is missing!")
        return

    date_str, hour_str, display_time = get_bkk_date_and_hour()
    zone = "BKKC1"

    podoh_rows = query_widget("cab3376f0a2d403992774991eb4809af", "9.1) Delivery Success (Lazada)-PODOH", date_str, hour_str, zone)
    oh_rows = query_widget("7581c9f7d34444779cec7b7627029b74", "9.2) Delivery Success (Lazada)-OH", date_str, hour_str, zone)
    sopd_rows = query_widget("2d6b5a21376e44a48a7c331466eb3288", "9.3) Delivery Success (Lazada)-SOP-D", date_str, hour_str, zone)
    dvl_rows = query_widget("c5846544c1874d6fb5ec8986feff66ff", "9.4) Delivery Success (Lazada)-DVL", date_str, hour_str, zone)
    pod_rows = query_widget("06afd1a5435945ce8164ee720dac5ff3", "9.5) Delivery Success (Lazada)-POD", date_str, hour_str, zone)
    dc_rows = query_widget("c110b81a94a54e1f983ea5e946fbc9ca", "9.8) Delivery Success (Lazada)-DC Lazada Performance", date_str, hour_str, zone)
    all_con_rows = query_widget("e65fea3ad1d44702b03e406ada8c0c35", "9.9) Delivery Success (Lazada)-all con", date_str, hour_str, zone, page_size=200)

    try:
        podoh_val = float(podoh_rows[0][0]) * 100 if podoh_rows and podoh_rows[0] else 0.0
    except:
        podoh_val = 0.0

    total_oh = int(oh_rows[0][0]) if oh_rows and oh_rows[0] else 0
    total_sopd = int(sopd_rows[0][0]) if sopd_rows and sopd_rows[0] else 0
    total_dvl = int(dvl_rows[0][0]) if dvl_rows and dvl_rows[0] else 0
    total_pod = int(pod_rows[0][0]) if pod_rows and pod_rows[0] else 0

    dc_data = []
    if dc_rows:
        for r in dc_rows:
            try:
                rate = float(r[7]) * 100
            except:
                rate = 0.0
            dc_data.append({
                "outlet_code": r[0],
                "region_code": r[1],
                "area_code": r[2],
                "on_hand": int(r[3]),
                "sopd": int(r[4]),
                "dvl": int(r[5]),
                "pod": int(r[6]),
                "success_rate": round(rate, 2)
            })

    parcels_data = []
    if all_con_rows:
        for c in all_con_rows:
            parcels_data.append({
                "waybill_no": c[0],
                "outlet_code": c[1],
                "area_code": c[3],
                "customer_channel": c[6],
                "arrival_shift": c[7],
                "out_time": c[8],
                "last_dvl_time": c[9],
                "status": c[11],
                "dly_code": c[12] if len(c) > 12 else "-",
                "dly_type": c[13] if len(c) > 13 else "-",
                "con_type": c[16] if len(c) > 16 else "-",
                "aoi_id": c[17] if len(c) > 17 else "-"
            })

    os.makedirs("data", exist_ok=True)
    web_payload = {
        "updated_at": display_time,
        "date": date_str,
        "hour": hour_str,
        "zone": zone,
        "summary": {
            "podoh_rate": round(podoh_val, 2),
            "on_hand": total_oh,
            "pod": total_pod,
            "sopd": total_sopd,
            "dvl": total_dvl
        },
        "dc_list": dc_data,
        "parcels": parcels_data
    }

    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(web_payload, f, ensure_ascii=False, indent=2)

    lines = [
        f"### 📦 รายงานสถานะจัดส่ง Lazada ({zone})",
        f"**อัปเดตเมื่อ:** {display_time}",
        f"---",
        f"- **อัตราสำเร็จ (PODOH):** `{podoh_val:.2f}%`",
        f"- **ยอดคงค้าง On-Hand (OH):** `{total_oh}` ชิ้น",
        f"- **จัดส่งสำเร็จ (POD):** `{total_pod}` ชิ้น",
        f"- **ยอด SOP-D:** `{total_sopd}` ชิ้น",
        f"---",
        f"#### 🏢 ยอดแยกรายสาขา (DC):"
    ]
    for dc in dc_data:
        lines.append(f"> **DC {dc['outlet_code']}:** ค้าง `{dc['on_hand']}` | POD `{dc['pod']}` | สำเร็จ `{dc['success_rate']}%`")

    send_dingtalk_message(f"รายงาน Lazada {zone} ({display_time})", "\n\n".join(lines))

if __name__ == "__main__":
    main()
