#!/bin/zsh
rm -rf build dist tariff_clock.spec
/Users/icrucrob/.pyenv/shims/python3.11 -m PyInstaller --name tariff_clock --windowed --onedir --icon icon/icon.icns --osx-bundle-identifier uk.ac.lshtm.tariff-clock --version-file version.plist src/project_chess_clock.py