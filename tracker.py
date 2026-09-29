def fetch_data_pipeline(day1, day2, formatted_time, clean_time, zone="BKKC1"):
    podoh_rows = query_widget("cab3376f0a2d403992774991eb4809af", "9.1) Delivery Success (Lazada)-PODOH", day1, day2, formatted_time, zone)
    oh_rows = query_widget("7581c9f7d34444779cec7b7627029b74", "9.2) Delivery Success (Lazada)-OH", day1, day2, formatted_time, zone)
    
    # ถ้าดึงข้อมูลหลักไม่ได้ ให้คืนค่า False ป้องกันโปรแกรมแครช
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
