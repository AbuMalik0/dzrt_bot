import threading
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# إعداد بيانات Telegram
TELEGRAM_TOKEN = "8041160533:AAE2ZkeYiqg7qDi1eLcJa4Iwh4JEaRNDrVw"
CHAT_IDS = ["1112926012", "7851677711", "6633625111", "799591241"]  # معرفات Chat ID

# إرسال رسالة نصية إلى Telegram
def send_telegram_message(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload)

# إعداد المتصفح
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# التحقق من توفر المنتج
def check_product(product, previous_status, start_time, is_initial_run):
    driver = setup_driver()
    try:
        driver.get(product['url'])
        wait = WebDriverWait(driver, 20)
        add_to_cart_button = wait.until(
            EC.presence_of_element_located((By.XPATH, '//button[contains(text(), "اضف الى السلة") or contains(text(), "Add to Basket")]'))
        )
        available = add_to_cart_button.is_enabled()

        # إذا كان التشغيل الأولي، نحفظ الحالة فقط دون إرسال إشعار "أصبح متوفر"
        if is_initial_run:
            previous_status[product['name']] = available
            if available:
                start_time[product['name']] = datetime.now()
            return available  # نعيد الحالة الحالية بدون إرسال إشعار إضافي

        # التحقق من تغيير الحالة
        if available and not previous_status[product['name']]:
            previous_status[product['name']] = True
            start_time[product['name']] = datetime.now()
            send_telegram_message(f"✅ المنتج {product['name']} أصبح متوفر.")

        elif not available and previous_status[product['name']]:
            previous_status[product['name']] = False
            end_time = datetime.now()
            duration = end_time - start_time[product['name']]
            hours, remainder = divmod(duration.seconds, 3600)
            minutes = remainder // 60
            send_telegram_message(
                f"🚫 المنتج {product['name']} أصبح غير متوفر.\n⏳ كان متوفرًا لمدة {hours} ساعات و{minutes} دقيقة."
            )

        return available  # إرجاع الحالة الحالية
    except Exception as e:
        send_telegram_message(f"⚠️ خطأ أثناء التحقق من المنتج {product['name']}: {e}")
        return previous_status[product['name']]  # الاحتفاظ بالحالة السابقة في حال وجود خطأ
    finally:
        driver.quit()

if __name__ == "__main__":
    products = [
        {"url": "https://www.dzrt.com/ar-sa/products/icy-rush", "name": "Icy Rush"},
        {"url": "https://www.dzrt.com/ar-sa/products/seaside-frost", "name": "Seaside Frost"}
    ]

    # حفظ الحالة السابقة ووقت التوفر
    previous_status = {product['name']: False for product in products}
    start_time = {product['name']: None for product in products}

    # إرسال رسالة تشغيل واحدة تتضمن حالة جميع المنتجات
    initial_message = "🚀 تم تشغيل البوت.\n📊 حالة المنتجات عند بدء التشغيل:\n"
    for product in products:
        available = check_product(product, previous_status, start_time, is_initial_run=True)
        initial_message += f"{'✅ متوفر' if available else '🚫 غير متوفر'} - {product['name']}\n"

    send_telegram_message(initial_message.strip())

    # دورة التحقق المستمرة
    while True:
        threads = []
        for product in products:
            thread = threading.Thread(target=check_product, args=(product, previous_status, start_time, False))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        time.sleep(120)  # الانتظار لمدة دقيقتين قبل التحقق مرة أخرى
