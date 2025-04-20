import psutil
import time
import threading
from plyer import notification
import winsound
import csv
from datetime import datetime
from PIL import Image, ImageDraw
import pystray

# Settings
FULL_BATTERY = 100
MAX_BATTERY = 80
MIN_BATTERY = 20
last_alert_message = "Battery Guardian is running..."



def alert(message, high=False):
    global last_alert_message
    last_alert_message = message
    print(message)
    notification.notify(title="Battery Alert!", message=message, timeout=10)
    winsound.Beep(3000 if high else 2000, 5000 if high else 1000)

def check_battery():
    while True:
        battery = psutil.sensors_battery()
        percent = battery.percent
        plugged = battery.power_plugged

        if plugged and percent >= MAX_BATTERY:
            alert(f"⚡ Battery is {percent}% - Unplug the charger!")
        elif not plugged and percent <= MIN_BATTERY:
            alert(f"🔋 Battery is {percent}% - Plug in soon!")
        elif plugged and percent == FULL_BATTERY:
            alert(f"⚡ Battery is {percent}% - Unplug the charger!", high=True)
        time.sleep(60)

def create_image():
    # Create an icon (16x16)
    image = Image.new('RGB', (64, 64), "white")
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 24, 48, 40), fill="green")  # Battery body
    dc.rectangle((28, 16, 36, 24), fill="green")  # Battery tip
    return image

def setup_tray():
    icon = pystray.Icon("BatteryGuardian")
    icon.icon = create_image()
    icon.title = "Battery Guardian"
    icon.visible = True

    def update_tooltip(icon):
        icon.visible = False
        icon.title = last_alert_message
        icon.visible = True

    def exit_app(icon, item):
        icon.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem(lambda text: last_alert_message, None, enabled=False),
        pystray.MenuItem("Quit", exit_app)
    )

    # Run battery checker in background
    threading.Thread(target=check_battery, daemon=True).start()

    # Periodically update tooltip
    def tooltip_updater():
        while True:
            update_tooltip(icon)
            time.sleep(10)

    threading.Thread(target=tooltip_updater, daemon=True).start()

    icon.run()

if __name__ == "__main__":
    setup_tray()
