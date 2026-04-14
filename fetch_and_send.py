import requests
import json
from datetime import datetime, timedelta
import os
import sys

# ========== 配置 ==========
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = os.getenv('FEISHU_APP_TOKEN')
FEISHU_TABLE_ID = os.getenv('FEISHU_TABLE_ID')
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN')
START_DATE = os.getenv('START_DATE')

# ========== 计算今天是第几天 ==========
def get_today_day_number():
    start = datetime.strptime(START_DATE, '%Y-%m-%d')
    today = datetime.now() + timedelta(hours=8)
    diff = (today.date() - start.date()).days + 1
    return diff

# ========== 获取飞书 Token ==========
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get('code') == 0:
        return data['tenant_access_token']
    else:
        print(f"❌ 获取飞书 Token 失败: {data}")
        sys.exit(1)

# ========== 提取文本内容 ==========
def extract_text(field_value):
    if field_value is None:
        return "暂无内容"
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, (int, float)):
        return str(field_value)
    if isinstance(field_value, list):
        result = ""
        for item in field_value:
            if isinstance(item, dict):
                result += item.get('text', '')
            elif isinstance(item, str):
                result += item
        return result if result else "暂无内容"
    return str(field_value)

# ========== 获取表格记录 ==========
def get_records(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"

    print(f"🔍 APP_TOKEN: {FEISHU_APP_TOKEN[:4]}***{FEISHU_APP_TOKEN[-4:]}")
    print(f"🔍 TABLE_ID: {FEISHU_TABLE_ID}")
    print(f"🔍 请求 URL: {url}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    all_records = []
    page_token = None

    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        response = requests.get(url, headers=headers, params=params)

        print(f"🔍 HTTP 状态码: {response.status_code}")
        print(f"🔍 返回内容前300字: {response.text[:300]}")

        if response.status_code != 200:
            print(f"❌ HTTP 错误: {response.status_code}")
            print(f"❌ 完整返回: {response.text}")
            sys.exit(1)

        data = response.json()

        if data.get('code') != 0:
            print(f"❌ API 错误码: {data.get('code')}")
            print(f"❌ 错误信息: {data.get('msg')}")
            sys.exit(1)

        items = data.get('data', {}).get('items', [])
        all_records.extend(items)

        if not data.get('data', {}).get('has_more', False):
            break
        page_token = data['data'].get('page_token')

    return all_records

# ========== 查找今天的记录 ==========
def find_today_record(records, day_number):
    target_patterns = [
        f"Day {day_number}",
        f"Day{day_number}",
        f"day {day_number}",
        f"day{day_number}",
        f"第{day_number}天",
        str(day_number),
    ]

    for record in records:
        fields = record.get('fields', {})
        day_value = fields.get('学习天数', '')
        day_text = extract_text(day_value).strip()

        for pattern in target_patterns:
            if pattern in day_text:
                return fields

    return None

# ========== 发送推送 ==========
def send_to_pushplus(day_number, content1, content2, content3):
    today_str = (datetime.now() + timedelta(hours=8)).strftime('%Y年%m月%d日')

    full_message = f"""
<h2>📚 Day {day_number} 学习内容推送</h2>
<p style="color:#888;">{today_str}</p>
<hr/>

<h3>📚 部分一：当日学习内容</h3>
<div style="background:#f5f5f5; padding:15px; border-radius:8px; margin:10px 0;">
<pre style="white-space:pre-wrap; word-wrap:break-word; font-family:inherit; font-size:14px; line-height:1.8; margin:0;">{content1}</pre>
</div>

<hr/>

<h3>✅ 部分二：周打卡任务</h3>
<div style="background:#f0f9f0; padding:15px; border-radius:8px; margin:10px 0;">
<pre style="white-space:pre-wrap; word-wrap:break-word; font-family:inherit; font-size:14px; line-height:1.8; margin:0;">{content2}</pre>
</div>

<hr/>

<h3>🔥 部分三：每日打卡接龙</h3>
<div style="background:#fff8f0; padding:15px; border-radius:8px; margin:10px 0;">
<pre style="white-space:pre-wrap; word-wrap:break-word; font-family:inherit; font-size:14px; line-height:1.8; margin:0;">{content3}</pre>
</div>

<hr/>
<p style="color:#888;">💡 三个部分分别长按复制，粘贴到对应微信群即可</p>
"""

    url = "http://www.pushplus.plus/send"
    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": f"📚 Day {day_number} 学习内容",
        "content": full_message,
        "template": "html"
    }

    response = requests.post(url, json=payload)
    result = response.json()

    if result.get('code') == 200:
        print("✅ 推送成功！")
    else:
        print(f"❌ 推送失败: {result}")
        sys.exit(1)

# ========== 主程序 ==========
def main():
    print("=" * 50)
    print("🚀 每日学习内容推送")
    print("=" * 50)

    day_number = get_today_day_number()
    print(f"📅 START_DATE: {START_DATE}")
    print(f"📅 今天是: Day {day_number}")

    if day_number < 1 or day_number > 35:
        print(f"⚠️ Day {day_number} 超出范围 (1-35)，跳过推送")
        return

    token = get_feishu_token()
    print("✅ 飞书 Token 获取成功")

    records = get_records(token)
    print(f"✅ 获取到 {len(records)} 条记录")

    record = find_today_record(records, day_number)

    if not record:
        print(f"⚠️ 没有找到 Day {day_number} 的记录")
        print("📋 可用的记录：")
        for r in records:
            fields = r.get('fields', {})
            day_val = extract_text(fields.get('学习天数', ''))
            print(f"   - {day_val}")
        return

    content1 = extract_text(record.get('当日学习内容', None))
    content2 = extract_text(record.get('周打卡任务', None))
    content3 = extract_text(record.get('每日打卡接龙', None))

    print(f"✅ 当日学习内容: {content1[:50]}...")
    print(f"✅ 周打卡任务: {content2[:50]}...")
    print(f"✅ 每日打卡接龙: {content3[:50]}...")

    send_to_pushplus(day_number, content1, content2, content3)

    print("=" * 50)
    print("🎉 完成！")

if __name__ == "__main__":
    main()
