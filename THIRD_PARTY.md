# Third-party components

- TOTEM keyboard and shield definitions: https://github.com/GEIGEIGEIST/TOTEM and https://github.com/GEIGEIGEIST/zmk-config. Firmware shield files retain their MIT SPDX headers and ZMK contributor notices.
- Original configuration reference: https://github.com/julimonteiro/zmk-config/pull/2. The distributed default is a fresh, simplified three-layer QWERTY keymap.
- ZMK: https://github.com/zmkfirmware/zmk, MIT license, revision 7823a43f627e5a14fc92238783480d52ae5ed1ce.
- Zephyr and its modules: https://github.com/zephyrproject-rtos/zephyr, primarily Apache-2.0; individual modules retain their own licenses in the acquired Docker volume.
- Standalone CPython: https://github.com/astral-sh/python-build-standalone, release 20261026, CPython 3.13.18. Python is licensed under the PSF License and bundled runtime licenses are retained. Build asset SHA-256 hashes are pinned in scripts/package-macos.py.

The source repository does not vendor the complete ZMK/Zephyr toolchain. The macOS release bundles the Python runtime, local companion sources, starter configuration and compiled firmware. Key positions and HID output are kept in memory; personal USB identities and diagnostic logs are excluded.
