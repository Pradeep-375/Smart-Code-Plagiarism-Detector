#!/usr/bin/env python3
"""
Smart Code Plagiarism Detector — Quick Setup Script
Run this once to verify your environment and create required directories.
Usage: python setup.py
"""
import os
import sys
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

DIRS = [
    os.path.join(BASE, 'uploads'),
    os.path.join(BASE, 'reports'),
    os.path.join(BASE, 'static', 'images'),
]

REQUIRED_PACKAGES = [
    'flask', 'pymysql', 'bcrypt', 'pygments',
    'sklearn', 'reportlab', 'numpy', 'pandas',
]


def check_python():
    if sys.version_info < (3, 8):
        print('❌ Python 3.8+ required. Current:', sys.version)
        sys.exit(1)
    print(f'✅ Python {sys.version.split()[0]}')


def create_directories():
    for d in DIRS:
        os.makedirs(d, exist_ok=True)
        print(f'✅ Directory ready: {os.path.relpath(d, BASE)}')


def check_packages():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
            print(f'✅ Package: {pkg}')
        except ImportError:
            missing.append(pkg)
            print(f'❌ Missing: {pkg}')
    return missing


def install_missing(packages):
    print(f'\nInstalling {len(packages)} missing package(s)...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r',
                           os.path.join(BASE, 'requirements.txt')])


def check_config():
    config_path = os.path.join(BASE, 'config.py')
    if os.path.exists(config_path):
        print('✅ config.py found')
    else:
        print('❌ config.py missing!')


def print_instructions():
    print('\n' + '='*55)
    print('  Smart Code Plagiarism Detector — Setup Complete!')
    print('='*55)
    print('\nNext steps:')
    print('  1. Set up MySQL:')
    print('       mysql -u root -p < database/schema.sql')
    print('\n  2. Edit config.py with your DB credentials')
    print('\n  3. Run the application:')
    print('       python app.py')
    print('\n  4. Open in browser:')
    print('       http://localhost:5000')
    print('\nDemo login (password: admin123):')
    print('  Admin   → admin@plagiarism.edu')
    print('  Faculty → faculty@plagiarism.edu')
    print('  Student → student@plagiarism.edu')
    print('='*55 + '\n')


if __name__ == '__main__':
    print('\n🔍 Smart Code Plagiarism Detector — Environment Check\n')
    check_python()
    create_directories()
    check_config()
    missing = check_packages()
    if missing:
        install_missing(missing)
    print_instructions()
