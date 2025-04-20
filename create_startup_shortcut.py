import os
import sys
import winshell
from win32com.client import Dispatch

def create_startup_shortcut():
    # Get the path to the startup folder
    startup_folder = winshell.startup()
    
    # Get the path to the current Python script
    script_path = os.path.abspath("batterysaver.py")
    
    # Create the shortcut path
    shortcut_path = os.path.join(startup_folder, "BatteryGuardian.lnk")
    
    # Create the shortcut
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = sys.executable  # Path to Python executable
    shortcut.Arguments = f'"{script_path}"'  # Path to the script
    shortcut.WorkingDirectory = os.path.dirname(script_path)
    shortcut.save()

if __name__ == "__main__":
    create_startup_shortcut()
    print("Startup shortcut created successfully!") 