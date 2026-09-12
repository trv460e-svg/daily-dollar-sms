import os
import sys
import time
import requests
from openai import OpenAI


# ============================================================
# Configuration
# ============================================================

MODEL = "gpt-4o-mini"

# حداکثر طول پیام SMS
MAX_SMS_LENGTH = 500

# تعداد تلاش مجدد در صورت خطای موقت
MAX_RETRIES = 3

# Timeout درخواست‌ها
REQUEST_TIMEOUT = 30


# ============================================================
# Environment Variables
# ============================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

MELIPAYAMAK_USERNAME = os.environ.get("MELIPAYAMAK_USERNAME")
MELIPAYAMAK_PASSWORD = os.environ.get("MELIPAYAMAK_PASSWORD")

MELIPAYAMAK_FROM = os.environ.get("MELIPAYAMAK_FROM")

SMS_TO = os.environ.get("SMS_TO", "")


# ============================================================
# Prompt
# ============================================================

PROMPT = """
تو یک تحلیلگر متخصص بازار دلار ایران هستی.

برای پیامک روزانه، فقط اطلاعات زیر را ارائه کن:

نرخ دلار آزاد: X تومان
دلار زاهدی آزاد: X تومان

احتمال صعود دلار: XX٪
بازه قیمت: XXX تا XXX تومان
علت/توضیح: یک جمله بسیار کوتاه

احتمال نزول دلار: XX٪
بازه قیمت: XXX تا XXX تومان

قوانین بسیار مهم:

1. فقط همین اطلاعات را ارائه کن.
2. هیچ مقدمه یا نتیجه‌گیری اضافه ننویس.
3. از جدول استفاده نکن.
4. از Markdown استفاده نکن.
5. از ایموجی استفاده نکن.
6. پاسخ برای SMS مناسب باشد.
7. حداکثر 500 کاراکتر باشد.
8. اعداد را به صورت خوانا و با واحد تومان بنویس.
9. احتمال صعود و نزول باید در مجموع 100٪ باشد.
10. اگر اطلاعاتی در دسترس نیست، حدس بی‌پایه نزن.
"""


# ============================================================
# Validate Environment Variables
# ============================================================

def validate_environment():
    """
    بررسی می‌کند تمام Secrets مورد نیاز وجود داشته باشند.
    """

    required_variables = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "MELIPAYAMAK_USERNAME": MELIPAYAMAK_USERNAME,
        "MELIPAYAMAK_PASSWORD": MELIPAYAMAK_PASSWORD,
        "MELIPAYAMAK_FROM": MELIPAYAMAK_FROM,
        "SMS_TO": SMS_TO,
    }

    missing = [
        name
        for name, value in required_variables.items()
        if not value or not value.strip()
    ]

    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
        )


# ============================================================
# Parse SMS Recipients
# ============================================================

def get_recipients():
    """
    شماره‌های گیرنده از SMS_TO خوانده می‌شوند.

    مثال:

    09121234567,09129876543,09351234567
    """

    recipients = [
        number.strip()
        for number in SMS_TO.split(",")
        if number.strip()
    ]

    if not recipients:
        raise RuntimeError(
            "SMS_TO does not contain any recipient number."
        )

    return recipients


# ============================================================
# Generate AI Report
# ============================================================

def generate_report():
    """
    دریافت گزارش کوتاه از OpenAI.
    """

    client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = client.chat.completions.create(
                model=MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "شما یک تحلیلگر دقیق بازار ارز ایران "
                            "هستید و باید پاسخ بسیار کوتاه و مناسب "
                            "پیامک تولید کنید."
                        ),
                    },
                    {
                        "role": "user",
                        "content": PROMPT,
                    },
                ],

                temperature=0.2,

                # خروجی کوتاه نگه داشته می‌شود
                max_tokens=250,
            )

            if not response.choices:
                raise RuntimeError(
                    "OpenAI returned no choices."
                )

            message = response.choices[0].message.content

            if not message:
                raise RuntimeError(
                    "OpenAI returned an empty response."
                )

            report = message.strip()

            # حذف Markdown احتمالی
            report = report.replace("**", "")
            report = report.replace("__", "")
            report = report.replace("###", "")

            # حذف فاصله‌های اضافی
            report = " ".join(report.split())

            # محدودیت نهایی SMS
            if len(report) > MAX_SMS_LENGTH:
                report = report[:MAX_SMS_LENGTH].rstrip()

                # جلوگیری از قطع شدن کلمه
                last_space = report.rfind(" ")

                if last_space > 350:
                    report = report[:last_space].rstrip()

            return report

        except Exception as exc:

            print(
                f"OpenAI attempt {attempt}/{MAX_RETRIES} failed: "
                f"{exc}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(3 * attempt)
            else:
                raise RuntimeError(
                    f"OpenAI request failed after "
                    f"{MAX_RETRIES} attempts."
                ) from exc


# ============================================================
# Send SMS
# ============================================================

def send_sms_to_recipient(message, recipient):
    """
    ارسال یک SMS به یک گیرنده.
    """

    url = (
        "https://rest.payamak-panel.com/"
        "api/SendSMS/SendSMS"
    )

    payload = {
        "username": MELIPAYAMAK_USERNAME,
        "password": MELIPAYAMAK_PASSWORD,
        "from": MELIPAYAMAK_FROM,
        "to": recipient,
        "text": message,
    }

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = requests.post(
                url,
                data=payload,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            result = response.text.strip()

            print(
                f"SMS sent to {recipient}"
            )

            print(
                f"Melipayamak response: {result}"
            )

            return True

        except requests.RequestException as exc:

            print(
                f"SMS attempt {attempt}/{MAX_RETRIES} "
                f"failed for {recipient}: {exc}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(3 * attempt)

            else:
                print(
                    f"SMS failed permanently for {recipient}"
                )

                return False

    return False


# ============================================================
# Send SMS to All Recipients
# ============================================================

def send_sms_to_all(message, recipients):
    """
    ارسال پیام به تمام شماره‌های موجود در SMS_TO.
    """

    success_count = 0
    failed_count = 0

    for recipient in recipients:

        success = send_sms_to_recipient(
            message,
            recipient
        )

        if success:
            success_count += 1
        else:
            failed_count += 1

    print(
        f"SMS summary: "
        f"{success_count} successful, "
        f"{failed_count} failed."
    )

    return failed_count == 0


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("Daily Dollar SMS Report")
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # 1. Validate environment
        # ----------------------------------------------------

        print("Checking environment variables...")

        validate_environment()

        # ----------------------------------------------------
        # 2. Get recipients
        # ----------------------------------------------------

        recipients = get_recipients()

        print(
            f"Recipients: {len(recipients)}"
        )

        # ----------------------------------------------------
        # 3. Generate AI report
        # ----------------------------------------------------

        print(
            "Generating report with OpenAI..."
        )

        report = generate_report()

        print("-" * 60)
        print("Generated report:")
        print(report)
        print("-" * 60)

        print(
            f"Message length: {len(report)} characters"
        )

        # ----------------------------------------------------
        # 4. Send SMS
        # ----------------------------------------------------

        print(
            "Sending SMS..."
        )

        all_successful = send_sms_to_all(
            report,
            recipients
        )

        # ----------------------------------------------------
        # 5. Final status
        # ----------------------------------------------------

        if not all_successful:

            print(
                "WARNING: One or more SMS messages failed."
            )

            # GitHub Actions را failed می‌کنیم
            sys.exit(1)

        print(
            "All SMS messages sent successfully."
        )

    except Exception as exc:

        print(
            f"ERROR: {exc}"
        )

        sys.exit(1)


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
