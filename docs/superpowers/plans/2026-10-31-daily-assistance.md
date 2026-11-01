# Daily assistance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the six approved daily assistance features and ship the updated macOS app.
**Architecture:** Retain the existing local Python service, browser editor and native Swift panel. Separate profile persistence, browser assistance algorithms and native presentation policy.
**Tech Stack:** Python stdlib, JavaScript, AppKit/SwiftUI, UserNotifications.
**Spec:** docs/superpowers/specs/2026-10-31-companion-assistance-design.md

## Global Constraints

- macOS only; local data, no typed-text history.
- Automatic panel is the user-selected default; no firmware changes.
- Preserve map/build matching, backup and operation locking.
- Existing checkout, feature branch; implement inline under user's instruction to do everything.

## Review Focus

- Stale or mismatched maps must not produce misleading instructions.
- Imports and profile identifiers cannot escape local storage.
- Deletion/correction must not count the same training error again.
- Stale battery readings cannot generate low battery alerts.
- Pending edits and active flash/build must prevent profile replacement.

### Task 1: Profile persistence
Files: local/profiles.py, local/test_profiles.py, local/server.py, scripts/package-macos.py.
Interfaces: Store(root).list(), create(name,source), read(id), rename(id,name), delete(id); API /api/profiles and /api/profile/{create,preview,apply,rename,delete,export}.
- [x] Write and run failing unittest for full-source preservation, traversal rejection, backup/CAS replacement and templates.
- [x] Implement store validation and atomic replacement through keymap.replace; wire API behind existing token and operation lock.
- [x] Run unittest suite; commit.

### Task 2: Search, practice and diagnostic algorithms
Files: local/static/assistance-core.js, local/test_assistance.cjs.
Interfaces: resolve(layers,query,inputMap), observe(stats,target,previous,value), sequence(stats), diagnostics(state).
- [x] Write/run failing tests for nested layer paths, modifiers, unknown actions, symbol map, error correction and stale diagnosis.
- [x] Implement pure algorithms with explicit unsupported results; run JS tests.

### Task 3: Editor assistance interface
Files: local/static/assistance.js, index.html, style.css, app.js, tutorial.js; local/browser-assistance.cjs.
Interfaces: window.TotemAssistance.open(section), totem:state event; profile APIs from Task 1.
- [x] Add failing browser flow for search results, adaptive practice, preview and profile guards.
- [x] Build accessible dialog tabs for search, practice, profiles and diagnostics with own 38-key map; persist aggregates scoped by map hash only.
- [x] Wire menu bridge entry points and verify browser suite.

### Task 4: Native panel policy and battery alerts
Files: native/Assistance.swift, TotemApp.swift, NativeMonitor.swift, PanelMenuTests.swift; build scripts.
Interfaces: OverlayPolicy(mode,live,layer), BatteryPolicy.observe(side,percentage,fresh), LiveModel.onUpdate.
- [x] Write/run failing native tests for automatic visibility, close suppression and battery rearm/duplicate suppression.
- [x] Implement 350ms delayed hide with cancellation, persisted modes, explicit notification opt-in and foreground fallback.
- [x] Verify native tests and app compilation.

### Task 5: Review and release
Files: README.md, native/Info.plist, checks workflow and packaging scripts.
- [x] Run Python, JS, browser and native checks; independent whole-change review; resolve material findings.
- [x] Package universal app and verify signature; open updated developer app.
- [x] Commit and publish public source and prerelease ZIP under existing authorization; report actual validation limits.
