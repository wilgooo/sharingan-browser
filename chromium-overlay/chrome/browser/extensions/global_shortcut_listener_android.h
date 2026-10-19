// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
#ifndef CHROME_BROWSER_EXTENSIONS_GLOBAL_SHORTCUT_LISTENER_ANDROID_H_
#define CHROME_BROWSER_EXTENSIONS_GLOBAL_SHORTCUT_LISTENER_ANDROID_H_
#include "chrome/browser/extensions/global_shortcut_listener.h"
namespace extensions {
// Android applications cannot register system-wide extension shortcuts.
class GlobalShortcutListenerAndroid final : public GlobalShortcutListener {
 public:
  GlobalShortcutListenerAndroid() = default;
  ~GlobalShortcutListenerAndroid() override = default;
 private:
  void StartListening() override {}
  void StopListening() override {}
  bool RegisterAcceleratorImpl(const ui::Accelerator&) override { return false; }
  void UnregisterAcceleratorImpl(const ui::Accelerator&) override {}
};
}  // namespace extensions
#endif
