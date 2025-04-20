import psutil
import time
import threading
from plyer import notification
import winsound
from PIL import Image, ImageDraw
import pystray
import sys

# Settings
FULL_BATTERY = 100
MAX_BATTERY = 80
MIN_BATTERY = 20
last_alert_message = "Battery Guardian is running..."
last_percent = -1  # Track previous battery percentage

def alert(message, high=False):
    global last_alert_message
    last_alert_message = message
    print(message)
    
    # Close any existing notification first
    notification.notify(title="", message="", timeout=1)
    time.sleep(0.5)
    
    # New notification
    notification.notify(
        title="Battery Alert!",
        message=message,
        timeout=10,
        toast=True  # Better for Windows 10/11
    )
    
    # More reliable sound method
    try:
        duration = 1000 if high else 500
        winsound.Beep(3000 if high else 2000, duration)
    except:
        import os
        os.system('powershell -c (New-Object Media.SoundPlayer "SystemExclamation").PlaySync()')

def check_battery():
    global last_percent
    while True:
        try:
            battery = psutil.sensors_battery()
            if not battery:
                time.sleep(60)
                continue
                
            percent = battery.percent
            plugged = battery.power_plugged
            
            # Only alert if percentage actually changed
            if percent != last_percent:
                if plugged and percent >= MAX_BATTERY:
                    alert(f"⚡ Battery is {percent}% - Unplug the charger!")
                elif not plugged and percent <= MIN_BATTERY:
                    alert(f"🔋 Battery is {percent}% - Plug in soon!")
                elif plugged and percent >= FULL_BATTERY:
                    alert(f"⚡ Battery FULL ({percent}%) - Unplug now!", high=True)
                
                last_percent = percent
                
        except Exception as e:
            print(f"Error: {e}")
        
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
