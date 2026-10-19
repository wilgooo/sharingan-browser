# Percobaan build di GitHub Actions standar

**Baseline baru: Kiwi resmi / Chromium 105.0.5195.24, runner standar `ubuntu-22.04`.** Audit dan port Sharingan sudah dilakukan; kapasitas untuk kompilasi penuh dan APK belum terbukti. Run #4 sebelumnya gagal dengan baseline 132 yang tidak cocok. Lihat [BASELINE.md](BASELINE.md).

## Hasil preflight pertama

[Run #1, 14 Oktober 2026](https://github.com/wilgooo/sharingan-browser/actions/runs/38576425331), commit `61ef07f3f035fb4f3ef9c254edef073f65f7dd12`, mode `preflight`, selesai sukses dalam 1 menit 40 detik pada `ubuntu-24.04`.

- Verifikasi 8.291 hash source dan 18 tes tooling lolos.
- Ruang disk kosong: **84,97 GiB sebelum → 113,85 GiB setelah cleanup**; bertambah 28,88 GiB dan melewati ambang awal eksperimen 70 GiB.
- RAM total yang dilaporkan: 16.373.448 KiB (sekitar 15,61 GiB); swap sekitar 3 GiB.
- Artifact diagnostik berhasil diunggah dengan retensi satu hari.
- Chromium tidak diunduh atau dikompilasi; tidak ada APK. Kapasitas pada run berikutnya bisa berbeda.

## Cara menjalankan

1. Buat repository GitHub kosong dengan visibility **Public**. Runner standar untuk repo publik gratis. Workflow sengaja melewati repo private dan tidak menggunakan larger runner.
2. Ekstrak paket source terbaru. Masuk ke folder `sharingan-browser` yang berisi README, `scripts/`, `config/`, `chromium-overlay/`, dan `.github/`.
3. Push **isi folder itu** ke root repo. Jangan hanya mengunggah file arsip, jangan menaruh source satu tingkat di bawah root, dan jangan melewatkan folder tersembunyi `.github`.

Dari Terminal Mac, untuk repo baru (ganti `USERNAME`):

```bash
cd /path/hasil-ekstrak/sharingan-browser
git init -b main
git add .
git commit -m "Prepare Sharingan source and free Actions build"
git remote add origin https://github.com/USERNAME/sharingan-browser.git
git push -u origin main
```

Repo publik proyek sudah tersedia di [wilgooo/sharingan-browser](https://github.com/wilgooo/sharingan-browser). Langkah 1–3 di atas hanya diperlukan jika membuat repo baru sendiri. GitHub memerlukan autentikasi Git/SSH/GitHub CLI yang sudah disiapkan di Mac. Jangan masukkan token ke source atau workflow. Tidak ada secret custom yang dibutuhkan build ini.

4. Buka **Actions → Sharingan Android - free runner experiment → Run workflow** pada branch default.
5. Pilih mode:
   - **preflight**: hanya cleanup dan pengukuran runner. Tidak download Chromium dan tidak membuat APK. Baca `disk_gate_passed` pada `status.json`.
   - **gn-only**: sama dengan build sampai `gn gen --check`, lalu berhenti tanpa Ninja/APK (`status: gn-complete`). Pakai ini selama masih memperbaiki error GN supaya jatah runner tidak habis untuk compile; cache paket tetap disimpan.
   - **build**: cleanup → shallow checkout → sync dependensi → dependency installer resmi → hooks → overlay → GN → Ninja → APK. Default dua worker; tiga/empat worker bisa lebih cepat dengan risiko RAM lebih tinggi.
6. Setelah selesai, buka halaman run → **Artifacts**:
   - `sharingan-diagnostics-…`: per-stage log, `status.json`, metrik disk/RAM/swap, dan konfigurasi build jika tahap tersebut tercapai.
   - `SharinganBrowser-dev-arm64-…`: hanya tersedia jika compile berhasil, berisi APK development dan `SHA256SUMS`.

Workflow hanya manual. Push tidak otomatis memulai build panjang. Dua run untuk branch yang sama tidak berjalan bersamaan; GitHub dapat mengganti run pending saat ada permintaan tambahan. Jangan klik Run berulang tanpa membaca hasil sebelumnya.

## Optimasi yang diterapkan

| Optimasi | Tujuan / tradeoff |
|---|---|
| `ubuntu-22.04` x86-64 standar | Library host termasuk libncurses5 cocok dengan toolchain Chromium 105; tetap runner gratis |
| Hapus toolchain preinstalled yang tidak dipakai | Membebaskan .NET, Android SDK bawaan, Haskell, Boost, Swift, dan hosted tool cache; Chromium mengambil toolchain yang cocok sendiri |
| Shallow clone + `gclient --no-history --shallow` | Mengurangi history Git, tetap mengambil file build yang diperlukan |
| Checkout `small`; skip coverage/telemetry/PGO test dependencies | Tidak mengunduh beberapa komponen yang tidak diperlukan build development |
| arm64 saja, satu APK | Menghindari build matriks beberapa arsitektur |
| `symbol_level`, `blink_symbol_level`, `v8_symbol_level` = 0 | Mengurangi ukuran object dan RAM link; stack trace native kurang lengkap |
| ThinLTO dan PGO dimatikan | Mengurangi beban optimasi compile/link; performa hasil bukan konfigurasi release optimal |
| Dua compile worker, satu linker | Menahan penggunaan RAM; build lebih lambat |
| Tidak memakai cache build multi-GB | Menghindari kuota cache dan biaya restore/save; run berikutnya mulai lagi dari awal |
| Artifact retention satu hari | Mengurangi akumulasi storage; download hasil segera |

Cleanup hanya berjalan pada runner GitHub-hosted Linux X64 untuk repo publik. Script memakai allowlist path, menolak mesin lokal/self-hosted, dan melindungi path executable/source aktif. **Jangan memalsukan environment GitHub untuk menjalankan cleanup di komputer pribadi.** Script ini sengaja menghapus toolchain pada VM sekali pakai.

Tidak ada penghapusan renderer sandbox, permission checks extension, atau pemakaian APK Kiwi jadi untuk membuat build tampak sukses.

## Ambang resource dan waktu

- Minimal **70 GiB kosong setelah cleanup** untuk mulai percobaan. Ini ambang eksperimen di bawah rekomendasi resmi Chromium 100 GB; bukan ukuran pasti source+build.
- Minimal **20 GiB** tersisa setelah dependency sync sebelum memasang dependensi sistem/hooks.
- Minimal **15 GiB** tersisa sebelum Ninja.
- Saat proses berjalan, disk diperiksa tiap 30 detik. Proses dihentikan bila ruang turun di bawah **3 GiB**, agar ada peluang menyimpan log. Penulisan cepat masih bisa memenuhi disk sebelum polling berikutnya.
- Driver membatasi total pekerjaan sekitar **315 menit**; step memiliki limit 330 menit, job 350 menit. Ada waktu cadangan untuk upload sebelum batas GitHub-hosted 6 jam. Timeout/cancellation keras tetap bisa menghalangi penyimpanan artifact.
- Tidak menambahkan swapfile besar karena swap juga memakan disk. Penggunaan swap bawaan dicatat dalam log.

Ruang yang berhasil dibebaskan bervariasi antar image runner. Pembersihan bukan cara mendapatkan kapasitas tertentu yang dijamin GitHub. Jika gate 70 GiB gagal, mode build berhenti sebelum unduhan besar; hasil preflight tetap berguna.

Compute runner standar publik gratis menurut dokumentasi GitHub. Artifact tetap mengikuti kuota storage akun; download lalu hapus artifact lama sebelum mengulang banyak build. Workflow ini tidak mengubah billing atau mengaktifkan runner berbayar.

## Membaca kegagalan

| Tahap terakhir | Arti / tindakan berikutnya |
|---|---|
| Cleanup/disk gate | Runner tidak punya cukup kapasitas untuk ambang eksperimen; lihat `before_cleanup`/`after_cleanup` |
| Chromium clone/dependency sync | Periksa network, disk, dan log gclient sebelum mengulang |
| System dependencies/hooks | Periksa log installer shell, library Ubuntu 22.04, dan toolchain Chromium 105 |
| Overlay | Periksa checkout/tag dan perubahan file dari hooks; jangan bypass pemeriksaan tanpa memahami error |
| GN | Dependency graph/arg/source baseline bermasalah; jangan menghapus `--check` untuk menutupi masalah |
| Compile | Perbaiki error compiler pertama; exit 137/SIGKILL dapat menunjukkan tekanan memori tetapi perlu bukti dari log |
| Timeout | Fetch+build melebihi budget; workflow ini tidak menyediakan resume object build lintas run |
| APK berhasil diunggah | Kompilasi berhasil, tetapi belum membuktikan browsing/ZIP/MV3/Web Store berfungsi; jalankan `TEST_PLAN.md` |

Baseline Kiwi masih eksperimental. Mengubah kapasitas runner tidak menyelesaikan inkompatibilitas source. Depot tools dipin dalam `config/upstream.lock.json`; kompatibilitas revisi tool tersebut dengan Chromium 105 masih perlu dibuktikan melalui build penuh.

## Referensi

- [Standard hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Actions limits](https://docs.github.com/en/actions/reference/limits)
- [Billing dan artifact storage](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Ubuntu 22.04 runner image](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md)
- [Chromium 105 DEPS](https://chromium.googlesource.com/chromium/src/+/105.0.5195.24/DEPS)
- [Chromium 105 link concurrency](https://chromium.googlesource.com/chromium/src/+/105.0.5195.24/build/toolchain/concurrent_links.gni)
