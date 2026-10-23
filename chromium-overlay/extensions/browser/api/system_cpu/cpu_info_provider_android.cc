// Copyright 2026 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "extensions/browser/api/system_cpu/cpu_info_provider.h"

#include "base/notreached.h"

namespace extensions {

// Sharingan: Kiwi exposes chrome.system.cpu on Android. Apps cannot read
// /proc/stat on Android 8+, and the Linux parser treats offline cores (common
// on big.LITTLE phones) as NOTREACHED, so report per-processor time as
// unavailable, like Fuchsia. The rest of the API (model, features) still works.
bool CpuInfoProvider::QueryCpuTimePerProcessor(
    std::vector<api::system_cpu::ProcessorInfo>* infos) {
  DCHECK(infos);
  NOTIMPLEMENTED_LOG_ONCE();
  return false;
}

}  // namespace extensions
