// Copyright 2026 Sharingan Browser contributors.
// Use of this source code is governed by a BSD-style license.
package org.chromium.chrome.browser.settings;
import android.os.Bundle;
import androidx.preference.PreferenceFragmentCompat;
import org.chromium.chrome.R;
import org.chromium.components.browser_ui.settings.SettingsUtils;
public class NightModeSettings extends PreferenceFragmentCompat {
    @Override
    public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
        getActivity().setTitle(R.string.preferences_nightmode);
        SettingsUtils.addPreferencesFromResource(this, R.xml.nightmode_preferences);
        RadioButtonGroupNightModePreference choices =
                (RadioButtonGroupNightModePreference) findPreference("nightmode_radio_group");
        choices.setActivity(getActivity());
    }
}
