import os
import sys
import requests
from openai import OpenAI


# ==============================
# Environment Variables
# ==============================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

MELIPAYAMAK_USERNAME = os.environ.get("MELIPAYAMAK_USERNAME")
MELIPAYAMAK_PASSWORD = os.environ.get("MELIPAYAMAK_PASSWORD")

MELIPAYAMAK_FROM = os.environ.get("MELIPAYAMAK_FROM")
SMS_TO = os.environ.get("SMS_TO")


# ==============================
# Prompt
# ==============================

PROMPT = """
نقش شما تحلیلگر روزانه بازار دلار ایران است.

یک گزارش بسیار کوتاه برای SMS تولید کن.

فقط این موارد را بده:

نرخ دلار آزاد:
X تومان

دلار زاهدی آزاد:
X تومان

احتمال صعود دلار:
XX٪
بازه:
XXX تا XXX تومان
علت:
یک جمله کوتاه

احتمال نزول دلار:
XX٪
بازه:
XXX تا XXX تومان


قوانین:
- فقط متن کوتاه
- بدون توضیح اضافه
- مناسب پیامک
- حداکثر 500 کاراکتر
- از ایموجی استفاده نکن
"""


# ==============================
# Validate Environment
# ==============================

def check_env():

    required = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "MELIPAYAMAK_USERNAME": MELIPAYAMAK_USERNAME,
        "MELIPAYAMAK_PASSWORD": MELIPAYAMAK_PASSWORD,
        "MELIPAYAMAK_FROM": MELIPAYAMAK_FROM,
        "SMS_TO": SMS_TO,
    }

    missing = [
        key for key, value in required.items()
        if not value
    ]

    if missing:
        raise Exception(
            f"Missing environment variables: {', '.join(missing)}"
        )


# ==============================
# OpenAI Request
# ==============================

def generate_report():

    try:

        client = OpenAI(
            api_key=OPENAI_API_KEY
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content":
                    "شما یک تحلیلگر اقتصادی دقیق هستید."
                },
                {
                    "role": "user",
                    "content": PROMPT
                }
            ],
            temperature=0.3,
            max_tokens=300
        )


        text = response.choices[0].message.content.strip()


        # محدودیت SMS
        if len(text) > 500:
            text = text[:500]


        return text


    except Exception as e:

        raise Exception(
            f"OpenAI Error: {str(e)}"
        )


# ==============================
# Melipayamak SMS
# ==============================

def send_sms(message):

    url = (
        "https://rest.payamak-panel.com/"
        "api/SendSMS/SendSMS"
    )


    payload = {
        "username": MELIPAYAMAK_USERNAME,
        "password": MELIPAYAMAK_PASSWORD,
        "from": MELIPAYAMAK_FROM,
        "to": SMS_TO,
        "text": message
    }


    try:

        response = requests.post(
            url,
            data=payload,
            timeout=20
        )


        response.raise_for_status()


        result = response.text


        return result


    except requests.exceptions.RequestException as e:

        raise Exception(
            f"Melipayamak Error: {str(e)}"
        )


# ==============================
# Main
# ==============================

def main():

    try:

        check_env()

        report = generate_report()

        print(
            "Generated SMS:"
        )

        print(report)


        sms_result = send_sms(report)


        print(
            "SMS API Response:"
        )

        print(sms_result)



    except Exception as e:

        print(
            f"FAILED: {e}"
        )

        sys.exit(1)



if __name__ == "__main__":
    main()
