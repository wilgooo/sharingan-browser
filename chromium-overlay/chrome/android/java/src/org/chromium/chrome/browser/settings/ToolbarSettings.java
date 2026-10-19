// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
package org.chromium.chrome.browser.settings;
import android.app.Activity;
import android.widget.Toast;
import org.chromium.chrome.R;
/** Shared notice for preferences that take effect when the browser restarts. */
public final class ToolbarSettings {
    private ToolbarSettings() {}
    public static void AskForRelaunch(Activity activity) {
        if (activity != null && !activity.isFinishing()) {
            Toast.makeText(activity, R.string.sharingan_restart_notice, Toast.LENGTH_LONG).show();
        }
    }
}
