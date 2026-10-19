// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
package org.chromium.chrome.browser;
import org.chromium.base.annotations.JNINamespace;
import org.chromium.base.annotations.NativeMethods;
import org.chromium.content_public.browser.WebContents;
/** Android extension action menu; native code rechecks the current profile and extension. */
@JNINamespace("extensions")
public final class AppMenuBridge {
    private AppMenuBridge() {}
    public static String getRunningExtensions(WebContents contents) {
        return contents == null ? "" : AppMenuBridgeJni.get().getRunningExtensions(contents);
    }
    public static String runAction(WebContents contents, String extensionId) {
        return contents == null ? "" : AppMenuBridgeJni.get().runAction(contents, extensionId);
    }
    @NativeMethods
    interface Natives {
        String getRunningExtensions(WebContents contents);
        String runAction(WebContents contents, String extensionId);
    }
}
