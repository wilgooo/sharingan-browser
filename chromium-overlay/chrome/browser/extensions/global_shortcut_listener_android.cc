// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
#include "chrome/browser/extensions/global_shortcut_listener_android.h"
#include "base/no_destructor.h"
namespace extensions {
GlobalShortcutListener* GlobalShortcutListener::GetInstance() {
  static base::NoDestructor<GlobalShortcutListenerAndroid> listener;
  return listener.get();
}
}  // namespace extensions
