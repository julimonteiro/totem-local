#!/bin/zsh
set -e
TASK_ROOT="${0:A:h:h}"
mkdir -p "$TASK_ROOT/TOTEM Local.app/Contents/MacOS"
cp "$TASK_ROOT/native/Info.plist" "$TASK_ROOT/TOTEM Local.app/Contents/Info.plist"
xcrun swiftc "$TASK_ROOT/native/TotemApp.swift" "$TASK_ROOT/native/NativeMonitor.swift" -o "$TASK_ROOT/TOTEM Local.app/Contents/MacOS/TotemLocal.next" -framework Cocoa -framework WebKit -framework SwiftUI -framework CoreBluetooth
mv "$TASK_ROOT/TOTEM Local.app/Contents/MacOS/TotemLocal.next" "$TASK_ROOT/TOTEM Local.app/Contents/MacOS/TotemLocal"
codesign --force --deep --sign - "$TASK_ROOT/TOTEM Local.app"
