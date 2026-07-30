from PIL import Image

# 1. Open your uploaded 1024x1024 logo
img = Image.open("loqin_logo.png")

# 2. Create a lightweight 256x256 version for the PyQt6 UI
img_ui = img.resize((256, 256), Image.Resampling.LANCZOS)
img_ui.save("loqin_logo_small.png")
print("Saved UI logo: loqin_logo_small.png")

# 3. Create a multi-layer .ico file for Windows/PyInstaller
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save("loqin_icon.ico", format="ICO", sizes=icon_sizes)
print("Saved Windows Icon: loqin_icon.ico")