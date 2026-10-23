// Copyright 2026 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Sharingan: Kiwi sets enable_supervised_users = false on Android (extensions
// are enabled), so child_account_service_android.cc is not built, but
// ChildAccountService.java still declares its native and is registered in the
// JNI table. Its only entry point is @CalledByNative from that unbuilt file, so
// this is never reached; it mirrors the pristine implementation to resolve the
// link.

#include <memory>

#include "base/callback.h"
#include "chrome/android/chrome_jni_headers/ChildAccountService_jni.h"

void JNI_ChildAccountService_OnReauthenticationFailed(JNIEnv* env,
                                                      jlong jcallbackPtr) {
  // Take ownership of the callback passed to Java, as the pristine code does.
  std::unique_ptr<base::RepeatingCallback<void()>> callback(
      reinterpret_cast<base::RepeatingCallback<void()>*>(jcallbackPtr));
  callback->Run();
}
