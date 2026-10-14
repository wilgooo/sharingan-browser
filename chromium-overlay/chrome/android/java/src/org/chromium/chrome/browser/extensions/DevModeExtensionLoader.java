// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
package org.chromium.chrome.browser.extensions;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;

import androidx.appcompat.app.AlertDialog;

import org.chromium.base.ContextUtils;
import org.chromium.base.annotations.CalledByNative;
import org.chromium.base.annotations.JNINamespace;
import org.chromium.base.annotations.NativeMethods;
import org.chromium.chrome.R;
import org.chromium.ui.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.ref.WeakReference;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Developer ZIP import. All public entry points run after native startup, on the UI thread. */
@JNINamespace("extensions")
public final class DevModeExtensionLoader {
    private static final int REQUEST_ZIP = 0x5347;
    private static final long MAX_ZIP_BYTES = 64L * 1024 * 1024;
    private static final ExecutorService IO = Executors.newSingleThreadExecutor();
    private static final Handler UI = new Handler(Looper.getMainLooper());
    private static boolean sInstalling;

    private final WeakReference<Activity> mActivity;
    private final File mZip;

    private DevModeExtensionLoader(Activity activity, File zip) {
        mActivity = new WeakReference<>(activity);
        mZip = zip;
    }

    public static boolean isDeveloperModeEnabled() {
        return DevModeExtensionLoaderJni.get().isDeveloperModeEnabled();
    }

    public static void setDeveloperModeEnabled(boolean enabled) {
        // Same profile preference as chrome://extensions. No second SharedPreferences toggle.
        DevModeExtensionLoaderJni.get().setDeveloperModeEnabled(enabled);
    }

    public static void launchPicker(Activity activity, boolean incognito) {
        if (incognito) {
            toast(R.string.sharingan_zip_regular_only);
            return;
        }
        if (!isDeveloperModeEnabled()) {
            toast(R.string.sharingan_zip_enable_dev);
            return;
        }
        if (sInstalling) {
            toast(R.string.sharingan_zip_busy);
            return;
        }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        // Some document providers label ZIPs as octet-stream. Validate through the native
        // ZIP parser, not a filename or an unreliable provider MIME type.
        intent.setType("*/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            activity.startActivityForResult(intent, REQUEST_ZIP);
        } catch (ActivityNotFoundException | SecurityException e) {
            toast(R.string.sharingan_zip_no_picker);
        }
    }

    public static boolean onPickerResult(
            Activity activity, int requestCode, int resultCode, Intent data) {
        if (requestCode != REQUEST_ZIP) return false;
        if (resultCode != Activity.RESULT_OK || data == null || data.getData() == null) return true;
        Uri uri = data.getData();
        if (!"content".equals(uri.getScheme())) {
            toast(R.string.sharingan_zip_invalid_uri);
            return true;
        }
        if (!isDeveloperModeEnabled()) {
            toast(R.string.sharingan_zip_enable_dev);
            return true;
        }
        new AlertDialog.Builder(activity)
                .setTitle(R.string.sharingan_zip_title)
                .setMessage(R.string.sharingan_zip_confirm)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.sharingan_zip_install,
                        (dialog, which) -> stage(activity, uri))
                .show();
        return true;
    }

    private static void stage(Activity activity, Uri uri) {
        if (sInstalling) {
            toast(R.string.sharingan_zip_busy);
            return;
        }
        if (!isDeveloperModeEnabled()) {
            toast(R.string.sharingan_zip_enable_dev);
            return;
        }
        sInstalling = true;
        toast(R.string.sharingan_zip_loading);
        Context context = ContextUtils.getApplicationContext();
        WeakReference<Activity> activityRef = new WeakReference<>(activity);
        IO.execute(() -> {
            File zip = null;
            try {
                zip = File.createTempFile("sharingan-extension-", ".zip", context.getCacheDir());
                try (InputStream in = context.getContentResolver().openInputStream(uri);
                        FileOutputStream out = new FileOutputStream(zip)) {
                    if (in == null) throw new IOException("Document provider returned no data.");
                    byte[] buffer = new byte[32768];
                    long total = 0;
                    int count;
                    while ((count = in.read(buffer)) != -1) {
                        total += count;
                        if (total > MAX_ZIP_BYTES) throw new IOException("ZIP exceeds 64 MiB.");
                        out.write(buffer, 0, count);
                    }
                    if (total == 0) throw new IOException("ZIP is empty.");
                }
                File staged = zip;
                UI.post(() -> {
                    DevModeExtensionLoader loader =
                            new DevModeExtensionLoader(activityRef.get(), staged);
                    if (!isDeveloperModeEnabled()) {
                        loader.onComplete(false, context.getString(R.string.sharingan_zip_enable_dev));
                        return;
                    }
                    DevModeExtensionLoaderJni.get().loadFromZip(loader, staged.getAbsolutePath());
                });
            } catch (IOException | SecurityException e) {
                if (zip != null) zip.delete();
                UI.post(() -> {
                    sInstalling = false;
                    showResult(activityRef.get(), false, e.getMessage());
                });
            }
        });
    }

    @CalledByNative
    private void onComplete(boolean success, String detail) {
        sInstalling = false;
        IO.execute(() -> mZip.delete());
        showResult(mActivity.get(), success, detail);
    }

    private static void showResult(Activity activity, boolean success, String detail) {
        if (success) {
            toast(R.string.sharingan_zip_success);
        } else if (activity != null && !activity.isFinishing() && !activity.isDestroyed()) {
            new AlertDialog.Builder(activity)
                    .setTitle(R.string.sharingan_zip_failed)
                    .setMessage(detail == null ? "Unable to read extension ZIP." : detail)
                    .setPositiveButton(android.R.string.ok, null)
                    .show();
        } else {
            toast(R.string.sharingan_zip_failed);
        }
    }

    private static void toast(int message) {
        Toast.makeText(ContextUtils.getApplicationContext(), message, Toast.LENGTH_LONG).show();
    }

    @NativeMethods
    interface Natives {
        boolean isDeveloperModeEnabled();
        void setDeveloperModeEnabled(boolean enabled);
        void loadFromZip(DevModeExtensionLoader caller, String path);
    }
}
