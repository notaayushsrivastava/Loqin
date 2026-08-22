app = BUNDLE(
    exe,
    name='Loqin.app',
    icon='',
    bundle_identifier='com.notaayushsrivastava.loqin',
    info_plist={
        'CFBundleName': 'Loqin',
        'CFBundleDisplayName': 'Loqin',
        'CFBundleShortVersionString': '1.7.0',
        'CFBundleVersion': '1.7.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 Aayush Srivastava',
        'NSLocationWhenInUseUsageDescription': 'Loqin needs location access to scan for nearby VIT Wi-Fi networks for automatic login.',
        'NSLocationUsageDescription': 'Loqin needs location access to scan for nearby VIT Wi-Fi networks for automatic login.'
    },
)