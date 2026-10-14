// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.

#include <string>
#include <utility>

#include "base/android/jni_android.h"
#include "base/android/jni_string.h"
#include "base/android/scoped_java_ref.h"
#include "base/bind.h"
#include "base/files/file_util.h"
#include "base/task/task_runner_util.h"
#include "chrome/browser/extensions/extension_service.h"
#include "chrome/browser/extensions/unpacked_installer.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/profiles/profile_manager.h"
#include "chrome/common/pref_names.h"
#include "components/prefs/pref_service.h"
#include "content/public/browser/browser_thread.h"
#include "extensions/browser/extension_file_task_runner.h"
#include "extensions/browser/extension_system.h"
#include "extensions/browser/zipfile_installer.h"
#include "extensions/common/extension.h"
#include "chrome/android/chrome_jni_headers/DevModeExtensionLoader_jni.h"

namespace extensions {
namespace {
using JavaCallback = base::android::ScopedJavaGlobalRef<jobject>;

bool DeveloperModeEnabled(Profile* profile) {
  return profile && !profile->IsOffTheRecord() &&
         profile->GetPrefs()->GetBoolean(prefs::kExtensionsUIDeveloperMode);
}

void Reply(JavaCallback callback, bool success, const std::string& detail) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  JNIEnv* env = base::android::AttachCurrentThread();
  Java_DevModeExtensionLoader_onComplete(
      env, callback, success, base::android::ConvertUTF8ToJavaString(env, detail));
}

void DeleteDirectory(const base::FilePath& path) {
  if (path.empty()) return;
  GetExtensionFileTaskRunner()->PostTask(FROM_HERE, base::BindOnce(
      [](base::FilePath dir) { base::DeletePathRecursively(dir); }, path));
}

base::FilePath MakeInstallDirectory(const base::FilePath& parent) {
  base::FilePath directory;
  if (!base::CreateDirectory(parent) ||
      !base::CreateTemporaryDirInDir(parent, "extension-", &directory))
    return base::FilePath();
  return directory;
}

void UnpackedComplete(JavaCallback callback,
                      const base::FilePath& owned_directory,
                      const Extension* extension,
                      const base::FilePath& loaded_path,
                      const std::string& error) {
  // A successful unzip alone is NOT a successful extension install.
  if (!extension) DeleteDirectory(owned_directory);
  Reply(std::move(callback), extension != nullptr,
        extension ? extension->id() : error);
}

void ZipComplete(base::WeakPtr<ExtensionService> service,
                 JavaCallback callback,
                 const base::FilePath& owned_directory,
                 const base::FilePath& zip,
                 const base::FilePath& unpacked,
                 const std::string& error) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  if (!service || !DeveloperModeEnabled(service->profile())) {
    DeleteDirectory(owned_directory);
    Reply(std::move(callback), false, "Developer mode is off or the profile was closed.");
    return;
  }
  if (unpacked.empty() || !error.empty() || unpacked != owned_directory) {
    DeleteDirectory(owned_directory);
    Reply(std::move(callback), false,
          error.empty() ? "manifest.json must be at the ZIP root." : error);
    return;
  }
  auto installer = UnpackedInstaller::Create(service.get());
  installer->set_be_noisy_on_failure(false);
  installer->set_allow_file_access(false);
  installer->set_allow_incognito_access(false);
  installer->set_completion_callback(base::BindOnce(
      &UnpackedComplete, std::move(callback), owned_directory));
  installer->Load(unpacked);
}

void DirectoryReady(base::WeakPtr<ExtensionService> service,
                    JavaCallback callback,
                    const base::FilePath& zip,
                    const base::FilePath& directory) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  if (directory.empty() || !service || !DeveloperModeEnabled(service->profile())) {
    DeleteDirectory(directory);
    Reply(std::move(callback), false, "Unable to prepare extension storage or developer mode is off.");
    return;
  }
  auto installer = ZipFileInstaller::Create(GetExtensionFileTaskRunner(),
      base::BindOnce(&ZipComplete, service, std::move(callback), directory));
  // Persistent profile storage: Android is free to evict the staging ZIP in cache.
  // Only Chromium's sandboxed ZIP service extracts archive entries.
  installer->LoadFromZipFileInDir(zip, directory);
}
}  // namespace

static jboolean JNI_DevModeExtensionLoader_IsDeveloperModeEnabled(JNIEnv* env) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  return DeveloperModeEnabled(ProfileManager::GetLastUsedProfile());
}

static void JNI_DevModeExtensionLoader_SetDeveloperModeEnabled(JNIEnv* env,
                                                               jboolean enabled) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  Profile* profile = ProfileManager::GetLastUsedProfile();
  if (profile && !profile->IsOffTheRecord())
    profile->GetPrefs()->SetBoolean(prefs::kExtensionsUIDeveloperMode, enabled);
}

static void JNI_DevModeExtensionLoader_LoadFromZip(
    JNIEnv* env,
    const base::android::JavaParamRef<jobject>& caller,
    const base::android::JavaParamRef<jstring>& path) {
  DCHECK_CURRENTLY_ON(content::BrowserThread::UI);
  JavaCallback callback(env, caller);
  Profile* profile = ProfileManager::GetLastUsedProfile();
  if (!DeveloperModeEnabled(profile)) {
    Reply(std::move(callback), false, "Enable extension developer mode first.");
    return;
  }
  auto* system = ExtensionSystem::Get(profile);
  auto* service = system ? system->extension_service() : nullptr;
  if (!service) {
    Reply(std::move(callback), false, "The extension service is unavailable.");
    return;
  }
  base::FilePath zip(base::android::ConvertJavaStringToUTF8(env, path));
  if (!zip.IsAbsolute() || zip.ReferencesParent()) {
    Reply(std::move(callback), false, "Invalid staging path.");
    return;
  }
  base::PostTaskAndReplyWithResult(GetExtensionFileTaskRunner().get(), FROM_HERE,
      base::BindOnce(&MakeInstallDirectory,
                    profile->GetPath().AppendASCII("SharinganDevExtensions")),
      base::BindOnce(&DirectoryReady, service->AsWeakPtr(), std::move(callback), zip));
}
}  // namespace extensions
