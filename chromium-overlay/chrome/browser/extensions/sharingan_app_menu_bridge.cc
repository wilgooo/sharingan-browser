// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
#include <string>
#include "base/android/jni_string.h"
#include "chrome/browser/extensions/extension_action_runner.h"
#include "chrome/browser/extensions/extension_tab_util.h"
#include "content/public/browser/browser_thread.h"
#include "content/public/browser/browser_context.h"
#include "content/public/browser/web_contents.h"
#include "extensions/browser/extension_action.h"
#include "extensions/browser/extension_action_manager.h"
#include "extensions/browser/extension_registry.h"
#include "extensions/browser/extension_util.h"
#include "extensions/common/extension.h"
#include "chrome/android/chrome_jni_headers/AppMenuBridge_jni.h"

namespace extensions {
namespace {
bool Allowed(content::WebContents* contents, const Extension& extension) {
  auto* context = contents->GetBrowserContext();
  return !context->IsOffTheRecord() || util::IsIncognitoEnabled(extension.id(), context);
}
std::string MenuName(const std::string& name) {
  std::string result = name;
  for (char& c : result) {
    if (static_cast<unsigned char>(c) < 32) c = ' ';
  }
  return result;
}
}  // namespace

static base::android::ScopedJavaLocalRef<jstring>
JNI_AppMenuBridge_GetRunningExtensions(
    JNIEnv* env, const base::android::JavaParamRef<jobject>& java_contents) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  auto* contents = content::WebContents::FromJavaWebContents(java_contents);
  std::string entries;
  if (contents) {
    auto* context = contents->GetBrowserContext();
    auto* registry = ExtensionRegistry::Get(context);
    auto* manager = ExtensionActionManager::Get(context);
    if (registry && manager) {
      const int tab_id = ExtensionTabUtil::GetTabId(contents);
      for (const auto& extension : registry->enabled_extensions()) {
        if (!Allowed(contents, *extension)) continue;
        auto* action = manager->GetExtensionAction(*extension);
        if (!action || !action->GetIsVisible(tab_id)) continue;
        if (!entries.empty()) entries += '\x1f';
        entries += MenuName(extension->name()) + '\x1e' + extension->id();
      }
    }
  }
  return base::android::ConvertUTF8ToJavaString(env, entries);
}

static base::android::ScopedJavaLocalRef<jstring> JNI_AppMenuBridge_RunAction(
    JNIEnv* env, const base::android::JavaParamRef<jobject>& java_contents,
    const base::android::JavaParamRef<jstring>& java_id) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  std::string popup;
  auto* contents = content::WebContents::FromJavaWebContents(java_contents);
  if (contents) {
    auto* context = contents->GetBrowserContext();
    auto* registry = ExtensionRegistry::Get(context);
    const std::string id = base::android::ConvertJavaStringToUTF8(env, java_id);
    const auto* extension = registry ? registry->enabled_extensions().GetByID(id) : nullptr;
    auto* runner = ExtensionActionRunner::GetForWebContents(contents);
    auto* manager = ExtensionActionManager::Get(context);
    if (extension && runner && manager && Allowed(contents, *extension)) {
      auto* action = manager->GetExtensionAction(*extension);
      if (action && runner->RunAction(extension, true) == ExtensionAction::ACTION_SHOW_POPUP) {
        popup = action->GetPopupUrl(ExtensionTabUtil::GetTabId(contents)).spec();
      }
    }
  }
  return base::android::ConvertUTF8ToJavaString(env, popup);
}
}  // namespace extensions
