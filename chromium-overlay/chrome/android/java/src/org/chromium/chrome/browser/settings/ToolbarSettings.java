// Copyright 2022-2026 The Chromium Authors & Kiwi Browser Revived Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package org.chromium.chrome.browser.settings;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;

import androidx.appcompat.app.AlertDialog;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreferenceCompat;

import org.chromium.base.ContextUtils;
import org.chromium.base.Log;
import org.chromium.ui.widget.Toast;

/**
 * Settings fragment for configuring Kiwi Browser Revived toolbar and menu customization.
 */
public class ToolbarSettings extends PreferenceFragmentCompat {
    private static final String TAG = "ToolbarSettings";

    public static final String PREF_BOTTOM_TOOLBAR = "enable_bottom_toolbar";
    public static final String PREF_OVERSCROLL_BUTTON = "enable_overscroll_button";
    public static final String PREF_KEEP_ADDRESS_BAR = "keep_address_bar_content";
    public static final String PREF_SHOW_EXTENSIONS_FIRST = "show_extensions_first";
    public static final String PREF_TABSWITCHER_MENU = "tabswitcher_opens_contextual_menu";

    @Override
    public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
        if (getActivity() != null) {
            getActivity().setTitle("Toolbar & Navigation");
        }
        Context context = getPreferenceManager().getContext();
        PreferenceScreen screen = getPreferenceManager().createPreferenceScreen(context);
        setPreferenceScreen(screen);

        SharedPreferences prefs = ContextUtils.getAppSharedPreferences();

        SwitchPreferenceCompat bottomToolbar = new SwitchPreferenceCompat(context);
        bottomToolbar.setKey(PREF_BOTTOM_TOOLBAR);
        bottomToolbar.setTitle("Bottom Address Bar");
        bottomToolbar.setSummary("Move the address bar and navigation controls to the bottom of the screen");
        bottomToolbar.setChecked(prefs.getBoolean(PREF_BOTTOM_TOOLBAR, false));
        bottomToolbar.setOnPreferenceChangeListener((preference, newValue) -> {
            prefs.edit().putBoolean(PREF_BOTTOM_TOOLBAR, (Boolean) newValue).apply();
            AskForRelaunch(getActivity());
            return true;
        });
        screen.addPreference(bottomToolbar);

        SwitchPreferenceCompat swipeToolbar = new SwitchPreferenceCompat(context);
        swipeToolbar.setKey(PREF_OVERSCROLL_BUTTON);
        swipeToolbar.setTitle("Toolbar Swipe Gestures");
        swipeToolbar.setSummary("Enable horizontal swipe gestures on the toolbar to switch tabs");
        swipeToolbar.setChecked(prefs.getBoolean(PREF_OVERSCROLL_BUTTON, true));
        swipeToolbar.setOnPreferenceChangeListener((preference, newValue) -> {
            prefs.edit().putBoolean(PREF_OVERSCROLL_BUTTON, (Boolean) newValue).apply();
            return true;
        });
        screen.addPreference(swipeToolbar);

        SwitchPreferenceCompat keepUrl = new SwitchPreferenceCompat(context);
        keepUrl.setKey(PREF_KEEP_ADDRESS_BAR);
        keepUrl.setTitle("Keep URL in Address Bar on Tap");
        keepUrl.setSummary("Retain the current page URL for quick editing when focusing the Omnibox");
        keepUrl.setChecked(prefs.getBoolean(PREF_KEEP_ADDRESS_BAR, false));
        keepUrl.setOnPreferenceChangeListener((preference, newValue) -> {
            prefs.edit().putBoolean(PREF_KEEP_ADDRESS_BAR, (Boolean) newValue).apply();
            return true;
        });
        screen.addPreference(keepUrl);

        SwitchPreferenceCompat extensionsFirst = new SwitchPreferenceCompat(context);
        extensionsFirst.setKey(PREF_SHOW_EXTENSIONS_FIRST);
        extensionsFirst.setTitle("Pin Extensions to Top of Menu");
        extensionsFirst.setSummary("Show installed desktop extensions at the top of the main 3-dot menu");
        extensionsFirst.setChecked(prefs.getBoolean(PREF_SHOW_EXTENSIONS_FIRST, false));
        extensionsFirst.setOnPreferenceChangeListener((preference, newValue) -> {
            prefs.edit().putBoolean(PREF_SHOW_EXTENSIONS_FIRST, (Boolean) newValue).apply();
            return true;
        });
        screen.addPreference(extensionsFirst);

        SwitchPreferenceCompat tabMenu = new SwitchPreferenceCompat(context);
        tabMenu.setKey(PREF_TABSWITCHER_MENU);
        tabMenu.setTitle("Tab Switcher Quick Menu");
        tabMenu.setSummary("Open quick tab actions when long-pressing the tab switcher button");
        tabMenu.setChecked(prefs.getBoolean(PREF_TABSWITCHER_MENU, false));
        tabMenu.setOnPreferenceChangeListener((preference, newValue) -> {
            prefs.edit().putBoolean(PREF_TABSWITCHER_MENU, (Boolean) newValue).apply();
            return true;
        });
        screen.addPreference(tabMenu);
    }

    /**
     * Helper to prompt the user to restart the browser after changing core UI/rendering preferences.
     */
    public static void AskForRelaunch(Activity activity) {
        if (activity == null || activity.isFinishing()) return;
        try {
            new AlertDialog.Builder(activity)
                    .setTitle("Relaunch Required")
                    .setMessage("Please restart Kiwi Browser for toolbar layout changes to take effect.")
                    .setPositiveButton("Relaunch Now", (dialog, which) -> {
                        android.content.Intent intent = activity.getPackageManager()
                                .getLaunchIntentForPackage(activity.getPackageName());
                        if (intent != null) {
                            intent.addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP
                                    | android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
                            activity.startActivity(intent);
                        }
                        System.exit(0);
                    })
                    .setNegativeButton("Later", null)
                    .show();
        } catch (Throwable t) {
            Log.w(TAG, "Failed to display relaunch dialog, falling back to toast", t);
            try {
                Toast.makeText(activity, "Restart Kiwi Browser to apply changes", Toast.LENGTH_SHORT).show();
            } catch (Throwable ignored) {
            }
        }
    }
}
