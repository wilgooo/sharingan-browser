# Melanjutkan di Linux

Status resep: audit source Kiwi resmi cocok dengan Chromium 105.0.5195.24; kompilasi masih perlu dibuktikan. Gunakan checkout khusus untuk eksperimen ini.

Untuk percobaan tanpa mesin sendiri, gunakan [workflow GitHub Actions gratis](GITHUB_ACTIONS_FREE.md). Workflow memakai driver CI tersendiri dengan ambang disk eksperimental; skrip fetch lokal tetap mensyaratkan 100 GiB.

## Mesin

Linux x86-64, idealnya Ubuntu, RAM 32 GiB dan disk kosong 200+ GiB direkomendasikan untuk kenyamanan. Dokumentasi Chromium menyebut minimum 8 GiB RAM dan 100 GB disk, dengan lebih dari 16 GiB RAM sangat dianjurkan. Build awal bisa lama dan membutuhkan unduhan besar. Linux ARM64 atau Docker ARM64 di Apple Silicon bukan builder native yang didukung resep ini.

## 1. Checkout kandidat Chromium

Salin seluruh folder `sharingan-browser` ke Linux. Dari folder paket:

```bash
bash scripts/fetch_chromium.sh /absolute/path/sharingan-build
```

Direktori tujuan harus baru. Skrip mengambil checkout Chromium 105.0.5195.24 dan dependensi Android tanpa menjalankan hooks. Revisi Chromium dan depot_tools dipin dalam `config/upstream.lock.json`. Gunakan Ubuntu 22.04 x86-64 untuk resep ini.

## 2. Dependensi sistem dan hooks

```bash
export PATH="/absolute/path/sharingan-build/depot_tools:$PATH"
cd /absolute/path/sharingan-build/src
```

Gunakan instruksi `docs/android_build_instructions.md` **di checkout 105** untuk nama dan opsi script dependensi yang cocok. Jika tersedia pada checkout tersebut:

```bash
bash build/install-build-deps-android.sh --unsupported
sudo apt-get install -y ninja-build
```

Jika file tersebut tidak ada, ikuti instruksi versi checkout; jangan menyalin daftar dependensi dari versi Chromium terbaru secara membabi buta.

```bash
cd /absolute/path/sharingan-build
gclient runhooks
```

Hooks resmi dapat mengunduh SDK/NDK/JDK/Clang. Hindari memaksa JDK 11 hanya karena README fork menyebutnya. Toolchain harus mengikuti `DEPS` checkout.

## 3. Terapkan overlay

Dari folder paket Sharingan:

```bash
python3 scripts/verify_source.py
python3 scripts/prepare.py /absolute/path/sharingan-build/src
```

Skrip memeriksa tag checkout, checksum overlay, perubahan lokal, symlink yang keluar checkout, serta file tak terlacak yang akan tertimpa. Ia tidak menghapus source pengguna atau menjalankan reset Git. Overlay yang identik dapat dicek ulang. Setelah source hasil overlay diedit, jangan jalankan persiapan ulang; pertahankan perubahan dan lanjutkan build.

`chromium-overlay/` sudah memuat patch Sharingan. Patch terpisah hanya untuk review/reproduksi terhadap commit Kiwi yang dipin, bukan diterapkan lagi pada checkout hasil persiapan.

## 4. Kompilasi dari source

```bash
bash scripts/build_linux.sh /absolute/path/sharingan-build/src
```

Skrip menjalankan:

```bash
buildtools/linux64/gn gen out/sharingan_arm64 --check --fail-on-unused-args
ninja -C out/sharingan_arm64 -j2 chrome_public_apk
```

Jika sukses, keluaran yang diharapkan:

```text
src/out/sharingan_arm64/apks/ChromePublic.apk
src/out/sharingan_arm64/apks/SharinganBrowser-dev-arm64.apk
```

Tidak ada fallback ke APK Kiwi yang sudah jadi. Jika GN/compile gagal, simpan error pertama dan pisahkan kegagalan baseline warisan dari perubahan Sharingan. Jangan menandai hasil build berhasil hanya karena `prepare.py` atau pemeriksaan host lulus. Kandidat baseline mungkin perlu rebase besar atau diganti dengan fork yang memiliki build source terverifikasi.

## 5. Verifikasi Android

Periksa manifest keluaran memakai `apkanalyzer manifest application-id`, lalu verifikasi sertifikat dengan `apksigner verify --verbose`. Pastikan application ID adalah `com.sharingan.browser` sebelum sideload ke perangkat uji. Paket menggunakan konfigurasi development, belum release signing.

```bash
adb install -r /absolute/path/sharingan-build/src/out/sharingan_arm64/apks/SharinganBrowser-dev-arm64.apk
```

Lanjutkan seluruh langkah di `TEST_PLAN.md`. Jangan memakai `pm clear` pada profil berisi data penting; pemeriksaan default OFF perlu fresh install/perangkat uji terpisah.
