import psutil
import time
import threading
from plyer import notification
import os
from PIL import Image, ImageDraw
import pystray
import sys
import winsound
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
from datetime import datetime
import ctypes
from ctypes import wintypes

# Settings
FULL_BATTERY = 100
MAX_BATTERY = 80
MIN_BATTERY = 20
last_alert_message = "Battery Guardian is running..."
last_percent = -1

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('BatteryGuardian')

# Windows API for battery status
class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]

def get_battery_status():
    """Get battery status using Windows API as fallback"""
    try:
        # Try psutil first
        battery = psutil.sensors_battery()
        if battery is not None:
            return battery.percent, battery.power_plugged
            
        # Fallback to Windows API
        GetSystemPowerStatus = ctypes.windll.kernel32.GetSystemPowerStatus
        GetSystemPowerStatus.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
        GetSystemPowerStatus.restype = wintypes.BOOL
        
        status = SYSTEM_POWER_STATUS()
        if GetSystemPowerStatus(ctypes.pointer(status)):
            percent = status.BatteryLifePercent
            if percent == 255:  # Unknown status
                return None, None
            plugged = status.ACLineStatus == 1
            return percent, plugged
            
    except Exception as e:
        # Only log if both methods fail
        if battery is None and not GetSystemPowerStatus(ctypes.pointer(status)):
            logger.error(f"Error getting battery status: {e}")
    return None, None

def play_sound(high_alert=False):
    """Play Windows notification sound"""
    try:
        logger.info("Attempting to play sound...")
        if high_alert:
            # Play a more urgent sound for high alerts
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            logger.info("Playing SystemExclamation sound")
        else:
            # Play standard notification sound
            winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
            logger.info("Playing SystemNotification sound")
        # Add a small delay to ensure sound plays
        time.sleep(0.5)
    except Exception as e:
        logger.error(f"Sound error: {e}")
        # Try alternative sound if first attempt fails
        try:
            logger.info("Trying alternative sound method...")
            winsound.Beep(1000, 500)  # 1000Hz for 500ms
            logger.info("Played beep sound")
        except Exception as beep_error:
            logger.error(f"Alternative sound also failed: {beep_error}")

def alert(message, high=False):
    global last_alert_message
    last_alert_message = message
    logger.info(f"Alert: {message}")
    
    # Play sound first
    play_sound(high)
    
    # Then show notification
    try:
        # Close any existing notification first
        notification.notify(title="", message="", timeout=1)
        time.sleep(0.1)
        
        # New notification
        notification.notify(
            title="Battery Alert!",
            message=message,
            timeout=10,
            toast=True
        )
        logger.info("Notification shown")
    except Exception as e:
        logger.error(f"Notification error: {e}")

class BatteryGuardianGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Battery Guardian")
        self.root.geometry("400x500")
        
        # Handle window minimize
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status label
        self.status_label = ttk.Label(self.main_frame, text="Status: Running")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=5)
        
        # Battery info
        self.battery_frame = ttk.LabelFrame(self.main_frame, text="Battery Information", padding="5")
        self.battery_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        self.percent_label = ttk.Label(self.battery_frame, text="Battery: --%")
        self.percent_label.grid(row=0, column=0, pady=2)
        
        self.plugged_label = ttk.Label(self.battery_frame, text="Status: --")
        self.plugged_label.grid(row=1, column=0, pady=2)
        
        # Debug console
        self.debug_frame = ttk.LabelFrame(self.main_frame, text="Debug Console", padding="5")
        self.debug_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.debug_text = scrolledtext.ScrolledText(self.debug_frame, height=10, width=40)
        self.debug_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Test sound button
        self.test_sound_button = ttk.Button(self.main_frame, text="Test Sound", command=self.test_sound)
        self.test_sound_button.grid(row=3, column=0, pady=5)
        
        # Exit button
        self.exit_button = ttk.Button(self.main_frame, text="Exit", command=self.exit_app)
        self.exit_button.grid(row=3, column=1, pady=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.debug_frame.columnconfigure(0, weight=1)
        self.debug_frame.rowconfigure(0, weight=1)
        
        # Setup system tray icon
        self.setup_tray()
        
        # Start battery monitoring
        self.monitor_thread = threading.Thread(target=self.monitor_battery, daemon=True)
        self.monitor_thread.start()
        
        # Redirect logging to debug console
        self.setup_logging()
        
    def setup_logging(self):
        class DebugHandler(logging.Handler):
            def __init__(self, text_widget):
                logging.Handler.__init__(self)
                self.text_widget = text_widget
                
            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.configure(state='normal')
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                    self.text_widget.configure(state='disabled')
                self.text_widget.after(0, append)
        
        handler = DebugHandler(self.debug_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        
    def setup_tray(self):
        # Create tray icon
        image = Image.new('RGB', (64, 64), "white")
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 24, 48, 40), fill="green")  # Battery body
        dc.rectangle((28, 16, 36, 24), fill="green")  # Battery tip
        
        self.tray_icon = pystray.Icon("BatteryGuardian")
        self.tray_icon.icon = image
        self.tray_icon.title = "Battery Guardian"
        
        # Create tray menu
        self.tray_icon.menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Test Sound", self.test_sound),
            pystray.MenuItem("Exit", self.exit_app)
        )
        
        # Start tray icon in a separate thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        
    def minimize_to_tray(self):
        self.root.withdraw()
        
    def test_sound(self):
        logger.info("Testing sound...")
        play_sound(True)
        
    def update_battery_info(self, percent, plugged):
        if percent is None:
            self.percent_label.config(text="Battery: Unknown")
            self.plugged_label.config(text="Status: Unknown")
            self.tray_icon.title = "Battery: Unknown"
        else:
            self.percent_label.config(text=f"Battery: {percent}%")
            self.plugged_label.config(text=f"Status: {'Plugged in' if plugged else 'Unplugged'}")
            self.tray_icon.title = f"Battery: {percent}% - {'Plugged in' if plugged else 'Unplugged'}"
        
    def monitor_battery(self):
        while True:
            try:
                percent, plugged = get_battery_status()
                
                if percent is None:
                    logger.warning("Could not get battery status. Retrying in 60 seconds...")
                    self.update_battery_info(None, None)
                    time.sleep(60)
                    continue
                    
                self.update_battery_info(percent, plugged)
                
                if plugged and percent >= MAX_BATTERY:
                    alert(f"⚡ Battery is {percent}% - Unplug the charger!")
                elif not plugged and percent <= MIN_BATTERY:
                    alert(f"🔋 Battery is {percent}% - Plug in soon!")
                elif plugged and percent >= FULL_BATTERY:
                    alert(f"⚡ Battery is {percent}% - Unplug the charger!", high=True)
                    
            except Exception as e:
                # Only log if it's not the expected "No usable implementation" error
                if "No usable implementation" not in str(e):
                    logger.error(f"Error monitoring battery: {e}")
                time.sleep(60)  # Wait before retrying
            time.sleep(60)
            
    def exit_app(self):
        logger.info("Exiting application...")
        self.tray_icon.stop()
        self.root.quit()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    gui = BatteryGuardianGUI()
    gui.run()
