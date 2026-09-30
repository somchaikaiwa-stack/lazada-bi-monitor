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

RUN_MODE = os.getenv("RUN_MODE", "auto_hourly").strip()
CUSTOM_DAY1 = os.getenv("CUSTOM_DAY1", "").strip()
CUSTOM_DAY2 = os.getenv("CUSTOM_DAY2", "").strip()
CUSTOM_HOUR = os.getenv("CUSTOM_HOUR", "").strip()

API_URL = "https://bi.th.kex-express.com/cdbi-ext/widget/queryData"
WEB_URL = "https://somchaikaiwa-stack.github.io/lazada-bi-monitor/"

def get_bkk_now():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.datetime.now(tz)

def format_hour(hour_val):
    clean = str(hour_val).strip("[]'\" ")
    return f"[{clean}]", clean

def send_dingtalk_message(title, markdown_text):
    if not DINGTALK_WEBHOOK:
        print("[DingTalk] ไม่พบ Webhook URL")
        return False

    url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET and DINGTALK_SECRET.lower() != "none":
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
    try:
        res = requests.post(url, json=body, timeout=15)
        print(f"[DingTalk Response] HTTP {res.status_code}: {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"[DingTalk Exception] {e}")
        return False

def query_widget(widget_id, widget_name, day1, day2, time_filter_val, zone="BKKC1", page_size=100):
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
            {"name": "Partition_Day1", "values": day1},
            {"name": "Partition_Day2", "values": day2},
            {"name": "Report_time_Choose_lasted_time", "values": time_filter_val}
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
        return None
    except Exception as e:
        print(f"[Query Error] {widget_name}: {e}")
        return None

def fetch_data_pipeline(day1, day2, formatted_time, clean_time, zone="BKKC1"):
    podoh_rows = query_widget("cab3376f0a2d403992774991eb4809af", "9.1) Delivery Success (Lazada)-PODOH", day1, day2, formatted_time, zone)
    oh_rows = query_widget("7581c9f7d34444779cec7b7627029b74", "9.2) Delivery Success (Lazada)-OH", day1, day2, formatted_time, zone)
    
    if not podoh_rows or not oh_rows:
        return False, None

    sopd_rows = query_widget("2d6b5a21376e44a48a7c331466eb3288", "9.3) Delivery Success (Lazada)-SOP-D", day1, day2, formatted_time, zone) or []
    dvl_rows = query_widget("c5846544c1874d6fb5ec8986feff66ff", "9.4) Delivery Success (Lazada)-DVL", day1, day2, formatted_time, zone) or []
    pod_rows = query_widget("06afd1a5435945ce8164ee720dac5ff3", "9.5) Delivery Success (Lazada)-POD", day1, day2, formatted_time, zone) or []
    dc_rows = query_widget("c110b81a94a54e1f983ea5e946fbc9ca", "9.8) Delivery Success (Lazada)-DC Lazada Performance", day1, day2, formatted_time, zone) or []
    all_con_rows = query_widget("e65fea3ad1d44702b03e406ada8c0c35", "9.9) Delivery Success (Lazada)-all con", day1, day2, formatted_time, zone, page_size=300) or []

    try:
        podoh_val = float(podoh_rows[0][0]) * 100 if podoh_rows and len(podoh_rows) > 0 and podoh_rows[0] else 0.0
    except:
        podoh_val = 0.0

    try:
        total_oh = int(oh_rows[0][0]) if oh_rows and len(oh_rows) > 0 and oh_rows[0] and oh_rows[0][0] is not None else 0
    except:
        total_oh = 0

    try:
        total_sopd = int(sopd_rows[0][0]) if sopd_rows and len(sopd_rows) > 0 and sopd_rows[0] and sopd_rows[0][0] is not None else 0
    except:
        total_sopd = 0

    try:
        total_dvl = int(dvl_rows[0][0]) if dvl_rows and len(dvl_rows) > 0 and dvl_rows[0] and dvl_rows[0][0] is not None else 0
    except:
        total_dvl = 0

    try:
        total_pod = int(pod_rows[0][0]) if pod_rows and len(pod_rows) > 0 and pod_rows[0] and pod_rows[0][0] is not None else 0
    except:
        total_pod = 0

    dc_data = []
    for r in dc_rows:
        try:
            rate = float(r[7]) * 100
        except:
            rate = 0.0
        dc_data.append({
            "outlet_code": r[0] if len(r) > 0 else "-",
            "region_code": r[1] if len(r) > 1 else "-",
            "area_code": r[2] if len(r) > 2 else "-",
            "on_hand": int(r[3]) if len(r) > 3 and r[3] is not None else 0,
            "sopd": int(r[4]) if len(r) > 4 and r[4] is not None else 0,
            "dvl": int(r[5]) if len(r) > 5 and r[5] is not None else 0,
            "pod": int(r[6]) if len(r) > 6 and r[6] is not None else 0,
            "success_rate": round(rate, 2)
        })

    parcels_data = []
    for c in all_con_rows:
        parcels_data.append({
            "waybill_no": c[0] if len(c) > 0 else "-",
            "outlet_code": c[1] if len(c) > 1 else "-",
            "area_code": c[3] if len(c) > 3 else "-",
            "customer_channel": c[6] if len(c) > 6 else "-",
            "arrival_shift": c[7] if len(c) > 7 else "-",
            "out_time": c[8] if len(c) > 8 else "-",
            "last_dvl_time": c[9] if len(c) > 9 else "-",
            "status": c[11] if len(c) > 11 else "-",
            "dly_code": c[12] if len(c) > 12 and c[12] else "-",
            "dly_type": c[13] if len(c) > 13 and c[13] else "-",
            "con_type": c[16] if len(c) > 16 and c[16] else "-",
            "aoi_id": c[17] if len(c) > 17 and c[17] else "-"
        })

    result_payload = {
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
    return True, result_payload

def update_daily_history_log(day_str, clean_time, display_time, result_payload):
    os.makedirs("data", exist_ok=True)
    history_file = "data/daily_history.json"
    
    history_data = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception:
            history_data = {}

    summary = result_payload["summary"]
    is_closing_hour = (str(clean_time) == "22") or (summary["on_hand"] == 0)

    entry = {
        "date": day_str,
        "recorded_at": display_time,
        "final_hour": clean_time,
        "is_day_closed": is_closing_hour,
        "podoh_rate": summary["podoh_rate"],
        "on_hand": summary["on_hand"],
        "pod": summary["pod"],
        "sopd": summary["sopd"],
        "dvl": summary["dvl"],
        "dc_list": result_payload["dc_list"]
    }
    history_data[day_str] = entry

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

def save_and_notify(result_payload, day1, day2, formatted_time, clean_time, display_time, zone="BKKC1"):
    os.makedirs("data", exist_ok=True)
    web_payload = {
        "updated_at": display_time,
        "date_range": f"{day1} - {day2}" if day1 != day2 else day1,
        "partition_day1": day1,
        "partition_day2": day2,
        "report_time": formatted_time,
        "report_hour": clean_time,
        "zone": zone,
        **result_payload
    }

    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(web_payload, f, ensure_ascii=False, indent=2)

    update_daily_history_log(day1, clean_time, display_time, result_payload)

    summary = result_payload["summary"]
    is_all_pod = (summary["on_hand"] == 0)
    
    if is_all_pod:
        title_tag = " [🚀 จัดส่งสำเร็จครบถ้วน 100%]"
    elif str(clean_time) == "22":
        title_tag = " [🌙 สรุปปิดยอดประจำวัน]"
    else:
        title_tag = ""

    lines = [
        f"### 📦 รายงานสถานะจัดส่ง Lazada ({zone}){title_tag}",
        f"**รอบเวลา:** `{clean_time}:00 น.` (ข้อมูลรอบ {formatted_time})",
        f"**วันที่ค้นหา:** `{day1}` | **เวลาที่ส่ง:** {display_time}",
        f"---",
        f"- **อัตราสำเร็จ (PODOH):** `{summary['podoh_rate']:.2f}%`",
        f"- **ยอดคงค้าง On-Hand (OH):** `{summary['on_hand']}` ชิ้น",
        f"- **จัดส่งสำเร็จ (POD):** `{summary['pod']}` ชิ้น",
        f"- **ยอด SOP-D:** `{summary['sopd']}` ชิ้น",
        f"---",
        f"#### 🏢 ยอดแยกรายสาขา (DC):"
    ]
    
    for dc in result_payload["dc_list"]:
        lines.append(f"> **DC {dc['outlet_code']}:** ค้าง `{dc['on_hand']}` | POD `{dc['pod']}` | สำเร็จ `{dc['success_rate']}%`")

    parcels = result_payload["parcels"]
    if parcels:
        lines.append("---")
        lines.append("#### 📋 รายการเลขพัสดุตกค้างแยกตามสาขา:")
        dc_group = {}
        for p in parcels:
            dc_code = p["outlet_code"] or "UNKNOWN"
            if dc_code not in dc_group:
                dc_group[dc_code] = []
            dc_group[dc_code].append(p)

        for dc_code, p_list in dc_group.items():
            lines.append(f"> **สาขา {dc_code} ({len(p_list)} ชิ้น):**")
            for p in p_list[:8]:
                dly = f" [{p['dly_code']}]" if p['dly_code'] and p['dly_code'] != '-' else ""
                lines.append(f">   `{p['waybill_no']}` - {p['status']}{dly}")
            if len(p_list) > 8:
                lines.append(f">   *...และอีก {len(p_list)-8} ชิ้น*")
    else:
        lines.append("---")
        lines.append("🎉 **ยอดพัสดุทั้งหมดถูกจัดส่งสำเร็จ (POD) เรียบร้อยแล้ว ไม่มีค้างส่ง!**")

    lines.append("---")
    lines.append(f"หากต้องการดูรายละเอียดเพิ่มเติมกดเข้าเว็บนี้\n{WEB_URL}")

    send_dingtalk_message(f"รายงาน Lazada {zone} ({clean_time}:00น.)", "\n\n".join(lines))

def main():
    now_bkk = get_bkk_now()
    display_time = now_bkk.strftime("%Y-%m-%d %H:%M:%S")
    zone = "BKKC1"

    if RUN_MODE == "test_bot_only":
        print("[MODE] กำลังทดสอบส่งข้อความเข้า DingTalk...")
        test_msg = (
            f"### 🔔 ทดสอบการเชื่อมต่อ DingTalk Bot สำเร็จ\n"
            f"- **ระบบ:** Lazada Operations Live Monitor\n"
            f"- **เวลาทดสอบ:** {display_time}\n"
            f"- **สถานะ Webhook:** เชื่อมต่อสำเร็จปกติ\n\n"
            f"หากต้องการดูรายละเอียดเพิ่มเติมกดเข้าเว็บนี้\n{WEB_URL}"
        )
        send_dingtalk_message("ทดสอบบอท DingTalk", test_msg)
        return

    if RUN_MODE == "manual_custom":
        day1 = CUSTOM_DAY1 if CUSTOM_DAY1 else now_bkk.strftime("%Y%m%d")
        day2 = CUSTOM_DAY2 if CUSTOM_DAY2 else day1
        hour_target = CUSTOM_HOUR if CUSTOM_HOUR else str(now_bkk.hour)
    else:
        day1 = now_bkk.strftime("%Y%m%d")
        day2 = day1
        hour_target = str(now_bkk.hour)

    formatted_time, clean_time = format_hour(hour_target)

    if RUN_MODE == "test_full_flow":
        print(f"[MODE] ทดสอบ Flow เต็มระบบ: วันที่ {day1} รอบเวลา {formatted_time}")
        ok, result = fetch_data_pipeline(day1, day2, formatted_time, clean_time, zone)
        if ok:
            save_and_notify(result, day1, day2, formatted_time, clean_time, display_time, zone)
            print("-> ทดสอบ Flow สำเร็จเรียบร้อย!")
        else:
            print("-> ทดสอบ Flow ไม่สำเร็จ (ไม่สามารถดึงข้อมูลจาก API ได้)")
        return

    print(f"[AUTO] เริ่มดึงข้อมูลรอบ {clean_time}:00 น. (ตัวกรอง: {formatted_time})")
    retry_delay_sec = 180
    max_attempts = 14

    attempt = 1
    while attempt <= max_attempts:
        current_time = get_bkk_now()
        ok, result = fetch_data_pipeline(day1, day2, formatted_time, clean_time, zone)
        
        if ok:
            save_and_notify(result, day1, day2, formatted_time, clean_time, current_time.strftime("%Y-%m-%d %H:%M:%S"), zone)
            
            if result["summary"]["on_hand"] == 0:
                print("-> พัสดุถูกจัดส่งสำเร็จครบ 100% แล้ว สิ้นสุดการรายงานของวันนี้ล่วงหน้า")
                return
            return

        if current_time.minute >= 40 and current_time.hour != now_bkk.hour:
            print("-> ใกล้ถึงรอบเวลาใหม่แล้ว ข้ามรอบนี้เพื่อให้รอบถัดไปทำงานแทน")
            break

        time.sleep(retry_delay_sec)
        attempt += 1

if __name__ == "__main__":
    main()
