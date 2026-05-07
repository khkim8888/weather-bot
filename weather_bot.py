import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# 로컬 개발용 .env 파일 로드 (GitHub Actions에서는 무시됨)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 환경변수
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 서울 좌표
SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780
OWM_BASE = "https://api.openweathermap.org"


def check_env_vars():
    required = ["OPENWEATHER_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"오류: 환경변수 누락 → {', '.join(missing)}")
        sys.exit(1)


def get_current_weather():
    """현재 서울 날씨 조회 (무료 API)"""
    resp = requests.get(
        f"{OWM_BASE}/data/2.5/weather",
        params={
            "lat": SEOUL_LAT, "lon": SEOUL_LON,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric", "lang": "kr",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_yesterday_weather():
    """어제 서울 날씨 조회 (One Call API 3.0 timemachine — 구독 필요)"""
    yesterday_noon = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    try:
        resp = requests.get(
            f"{OWM_BASE}/data/3.0/onecall/timemachine",
            params={
                "lat": SEOUL_LAT, "lon": SEOUL_LON,
                "dt": int(yesterday_noon.timestamp()),
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"어제 날씨 조회 실패 (One Call API 3.0 구독 필요): {e}")
        return None


def get_forecast():
    """오늘 날씨 예보 조회 — 강수 확인용 (무료 API)"""
    resp = requests.get(
        f"{OWM_BASE}/data/2.5/forecast",
        params={
            "lat": SEOUL_LAT, "lon": SEOUL_LON,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric", "lang": "kr", "cnt": 8,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_air_quality():
    """현재 대기질 조회 (무료 API)"""
    resp = requests.get(
        f"{OWM_BASE}/data/2.5/air_pollution",
        params={"lat": SEOUL_LAT, "lon": SEOUL_LON, "appid": OPENWEATHER_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def parse_weather_data(current, yesterday_data, forecast, air_quality):
    """수집된 데이터 파싱 및 정리"""
    today_temp = round(current["main"]["temp"], 1)
    feels_like = round(current["main"]["feels_like"], 1)
    temp_max = round(current["main"]["temp_max"], 1)
    temp_min = round(current["main"]["temp_min"], 1)
    humidity = current["main"]["humidity"]
    description = current["weather"][0]["description"]

    # 어제 기온 비교
    yesterday_temp = None
    temp_diff = None
    temp_comparison = "비교 데이터 없음 (One Call API 3.0 구독 필요)"
    if yesterday_data and "data" in yesterday_data and yesterday_data["data"]:
        yesterday_temp = round(yesterday_data["data"][0]["temp"], 1)
        temp_diff = round(today_temp - yesterday_temp, 1)
        diff_abs = abs(temp_diff)
        if temp_diff >= 3:
            temp_comparison = f"어제({yesterday_temp}°C)보다 {diff_abs:.1f}°C 높음 ↑"
        elif temp_diff <= -3:
            temp_comparison = f"어제({yesterday_temp}°C)보다 {diff_abs:.1f}°C 낮음 ↓"
        else:
            temp_comparison = f"어제({yesterday_temp}°C)와 비슷함 →"

    # 강수 예보 — 첫 번째 강수 시간과 확률 기록
    rain_forecast = False
    rain_times = []
    first_rain_prob = 0
    kst = timedelta(hours=9)
    for item in forecast["list"]:
        if item["weather"][0]["main"] in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
            if not rain_forecast:
                first_rain_prob = round(item.get("pop", 0) * 100)
            rain_forecast = True
            t = datetime.fromtimestamp(item["dt"], tz=timezone.utc) + kst
            rain_times.append(t.strftime("%H:%M"))

    # 대기질
    aqi = air_quality["list"][0]["main"]["aqi"]
    components = air_quality["list"][0]["components"]
    pm25 = round(components.get("pm2_5", 0), 1)
    pm10 = round(components.get("pm10", 0), 1)
    aqi_label = {1: "좋음", 2: "보통", 3: "나쁨", 4: "매우 나쁨", 5: "위험"}.get(aqi, "알 수 없음")

    return {
        "현재_기온": today_temp,
        "최고_기온": temp_max,
        "최저_기온": temp_min,
        "체감_기온": feels_like,
        "습도": humidity,
        "날씨_상태": description,
        "기온_비교": temp_comparison,
        "어제_기온": yesterday_temp,
        "기온_차이": temp_diff,
        "비_예보": rain_forecast,
        "비_예상_시간": rain_times[:5],
        "첫_강수_확률": first_rain_prob,
        "대기질": aqi_label,
        "PM2.5(μg/m³)": pm25,
        "PM10(μg/m³)": pm10,
    }


def get_pm10_grade(pm10: float) -> str:
    """PM10 미세먼지 등급 — 한국 환경부 기준"""
    if pm10 <= 30:
        return "좋음"
    elif pm10 <= 80:
        return "보통"
    elif pm10 <= 150:
        return "나쁨"
    else:
        return "매우나쁨"


def get_pm25_grade(pm25: float) -> str:
    """PM2.5 초미세먼지 등급 — 한국 환경부 기준"""
    if pm25 <= 15:
        return "좋음"
    elif pm25 <= 35:
        return "보통"
    elif pm25 <= 75:
        return "나쁨"
    else:
        return "매우나쁨"


def get_clothing_items(temp: float, rain_forecast: bool) -> list:
    """기온과 강수 예보 기반 옷차림 추천 목록"""
    if temp <= 5:
        items = ["두꺼운 패딩, 목도리, 장갑"]
    elif temp <= 10:
        items = ["코트나 두꺼운 자켓"]
    elif temp <= 17:
        items = ["가벼운 자켓 또는 가디건"]
    elif temp <= 22:
        items = ["긴팔 셔츠"]
    elif temp <= 27:
        items = ["반팔 또는 얇은 긴팔"]
    else:
        items = ["반팔, 반바지"]

    if rain_forecast:
        items.append("우산 챙기기 필수!")

    return items


def generate_message(weather_info: dict) -> str:
    """템플릿 기반 한국어 날씨 알림 메시지 생성"""
    kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
    month = kst_now.month
    day = kst_now.day
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = weekdays[kst_now.weekday()]

    temp = weather_info["현재_기온"]
    yesterday_temp = weather_info.get("어제_기온")
    temp_diff = weather_info.get("기온_차이")
    rain_forecast = weather_info["비_예보"]
    rain_times = weather_info["비_예상_시간"]
    first_rain_prob = weather_info.get("첫_강수_확률", 0)
    pm10 = weather_info["PM10(μg/m³)"]
    pm25 = weather_info["PM2.5(μg/m³)"]
    weather_desc = weather_info.get("날씨_상태", "")

    # 날씨 헤더 이모지
    if "비" in weather_desc or "소나기" in weather_desc:
        header_emoji = "🌧"
    elif "눈" in weather_desc:
        header_emoji = "❄️"
    elif "구름" in weather_desc:
        header_emoji = "⛅"
    else:
        header_emoji = "🌤"

    # 기온 및 어제 대비 변화
    if yesterday_temp is not None and temp_diff is not None:
        diff_abs = abs(temp_diff)
        diff_str = f"{diff_abs:.0f}" if diff_abs == int(diff_abs) else f"{diff_abs:.1f}"
        if temp_diff > 0:
            temp_line = f"📊 기온: {temp}°C (어제보다 {diff_str}°C ⬆️ 따뜻해짐)"
        elif temp_diff < 0:
            temp_line = f"📊 기온: {temp}°C (어제보다 {diff_str}°C ⬇️ 추워짐)"
        else:
            temp_line = f"📊 기온: {temp}°C (어제와 비슷)"
    else:
        temp_line = f"📊 기온: {temp}°C"

    # 강수 예보
    if rain_forecast and rain_times:
        hour = int(rain_times[0].split(":")[0])
        if hour < 12:
            ampm = "오전"
            display_hour = hour if hour > 0 else 12
        elif hour == 12:
            ampm = "오후"
            display_hour = 12
        else:
            ampm = "오후"
            display_hour = hour - 12
        prob_str = f" (확률 {first_rain_prob}%)" if first_rain_prob > 0 else ""
        rain_line = f"☔ 강수: {ampm} {display_hour}시경 비 예보{prob_str}"
    elif rain_forecast:
        rain_line = "☔ 강수: 오늘 비 예보"
    else:
        rain_line = "☀️ 강수: 강수 없음"

    # 대기질 등급 (한국 환경부 기준)
    pm10_grade = get_pm10_grade(pm10)
    pm25_grade = get_pm25_grade(pm25)

    air_lines = [
        "😷 대기질",
        f"   - 미세먼지(PM10): {pm10_grade} ({pm10}㎍/㎥)",
        f"   - 초미세먼지(PM2.5): {pm25_grade} ({pm25}㎍/㎥)",
    ]

    # 마스크 권장 여부
    if pm10_grade == "매우나쁨" or pm25_grade == "매우나쁨":
        air_lines.append("   ⚠️ 마스크 필수, 외출 자제 권장")
    elif pm10_grade == "나쁨" or pm25_grade == "나쁨":
        air_lines.append("   ⚠️ 마스크 착용 권장")

    # 옷차림 추천
    clothing_items = get_clothing_items(temp, rain_forecast)
    clothing_lines = ["👔 옷차림 추천"] + [f"- {item}" for item in clothing_items]

    # 메시지 조합
    lines = [
        f"{header_emoji} {month}월 {day}일 ({weekday}) 오늘의 날씨",
        "",
        temp_line,
        rain_line,
        *air_lines,
        "",
        *clothing_lines,
    ]

    return "\n".join(lines)


def send_telegram_message(message: str) -> dict:
    """텔레그램 봇으로 메시지 전송"""
    resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
    print("=" * 50)
    print(f"날씨 봇 실행 — {kst_now.strftime('%Y-%m-%d %H:%M')} KST")
    print("=" * 50)

    check_env_vars()

    print("\n[1/4] 현재 날씨 수집 중...")
    current = get_current_weather()
    print(f"      현재 기온: {current['main']['temp']}°C")

    print("[2/4] 어제 날씨 수집 중...")
    yesterday = get_yesterday_weather()

    print("[3/4] 오늘 예보 수집 중...")
    forecast = get_forecast()

    print("[4/4] 대기질 정보 수집 중...")
    air = get_air_quality()

    print("\n데이터 분석 중...")
    info = parse_weather_data(current, yesterday, forecast, air)
    print(f"분석 결과: {json.dumps(info, ensure_ascii=False)}")

    print("\n날씨 메시지 생성 중...")
    message = generate_message(info)
    print(f"\n{'─' * 40}\n{message}\n{'─' * 40}")

    print("\n텔레그램 전송 중...")
    result = send_telegram_message(message)
    if result.get("ok"):
        print("전송 완료!")
    else:
        print(f"전송 실패: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
