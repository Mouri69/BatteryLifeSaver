import PyInstaller.__main__

PyInstaller.__main__.run([
    'batterysaver.py',
    '--onefile',
    '--noconsole',
    '--name=BatteryGuardian',
    '--icon=icon.ico'
]) 