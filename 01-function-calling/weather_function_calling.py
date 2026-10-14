"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Cách chạy:
    pip install -r ../requirements.txt
    export GEMINI_API_KEY=...
    python weather_function_calling.py
"""

import json
import os
import sys
from pathlib import Path

# Đảm bảo in tiếng Việt / emoji trên Windows terminal không bị lỗi charmap
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Nạp file .env từ thư mục hiện tại hoặc thư mục gốc
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else genai.Client()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


# 2. App tự thực thi tool: gọi OpenWeatherMap API nếu có API key, hoặc dùng mock data
def get_weather(city: str) -> str:
    """Trả về thời tiết của *city*. Ưu tiên OpenWeatherMap API, fallback mock data."""
    openweather_key = os.getenv("OPENWEATHER_API_KEY")
    if openweather_key:
        try:
            import httpx
            resp = httpx.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": openweather_key, "units": "metric", "lang": "vi"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps({
                    "city": city,
                    "nguồn": "OpenWeatherMap API (Live)",
                    "nhiệt_độ": f"{round(data['main']['temp'])}°C",
                    "cảm_giác_như": f"{round(data['main']['feels_like'])}°C",
                    "thời_tiết": data["weather"][0]["description"],
                    "độ_ẩm": f"{data['main']['humidity']}%",
                    "gió": {
                        "tốc_độ": f"{data['wind']['speed']} m/s",
                    },
                }, ensure_ascii=False)
        except Exception as e:
            print(f"  [Lưu ý: Không thể lấy dữ liệu online cho {city}, dùng mock data: {e}]")

    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }
    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, "nguồn": "mock", **mock_data.get(city, default)}, ensure_ascii=False)


import time

def call_gemini_with_retry(contents, config, retries=3):
    """Gọi Gemini với cơ chế retry và fallback model khi gặp lỗi 503 UNAVAILABLE (quá tải tạm thời)."""
    models = [MODEL, "gemini-3.5-flash-lite", "gemini-flash-latest"]
    last_err = None

    for m in models:
        for attempt in range(retries):
            try:
                return client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                    wait_time = (attempt + 1) * 2
                    print(f"  [⚠️ Google API quá tải tạm thời với {m}. Đang thử lại lần {attempt+1}/{retries} sau {wait_time}s...]")
                    time.sleep(wait_time)
                else:
                    break  # lỗi khác không phải 503 thì không retry model này
        # Nếu model này hết lượt thử mà vẫn lỗi 503, thử sang model tiếp theo
        print(f"  [Chuyển sang model dự phòng tiếp theo...]")

    raise last_err


def run(prompt: str) -> str:
    """Gửi *prompt* tới Gemini, tự động xử lý function calling và trả về câu trả lời cuối."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = call_gemini_with_retry(
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    while resp.function_calls:
        # Thêm phản hồi của model vào lịch sử hội thoại
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            result = get_weather(**fc.args)  # <-- app chạy, không phải model
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))
        resp = call_gemini_with_retry(
            contents=contents,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )

    # 5. Model tổng hợp câu trả lời cuối
    return resp.text


if __name__ == "__main__":
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:\n" + run(question))
