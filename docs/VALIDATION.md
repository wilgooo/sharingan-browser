# Hasil pemeriksaan — 14 Oktober 2026

Pemeriksaan lokal: macOS / Apple Silicon (Darwin arm64). Percobaan build tambahan: GitHub-hosted Ubuntu 24.04 x86-64. Tidak ada APK yang dibuat atau dipasang. [Run #4 terblokir pada evaluasi GN](BUILD_BLOCKER.md).

| Pemeriksaan | Hasil |
|---|---|
| Repo publik di-clone dan commit dipin | PASS — `9806d8c9a2ae8952a1e68b64aedcd225bcd3fbe3` |
| `git diff --check` | PASS |
| Patch diterapkan ke salinan bersih commit fork | PASS — `git apply --check`, lalu `git apply` |
| Patch mereproduksi overlay yang dikemas | PASS — hash semua 8.291 file identik |
| Checksum source dan referensi JNI/GN/resource | PASS — `scripts/verify_source.py` |
| XML yang ditambah/diubah | PASS — parser XML; manifest Jinja hanya diperiksa referensi resource baru |
| Fixture MV3 | PASS — manifest dan file yang dirujuk tersedia dalam ZIP |
| JavaScript contoh | PASS — `node --check` untuk background/content/popup |
| Sintaks skrip shell | PASS — `bash -n` untuk fetch dan build |
| Guard platform builder | PASS — script menolak macOS sebelum mencoba build |
| Test tooling persiapan checkout | PASS — 8 test Python |
| GN generation / dependency resolution | GAGAL — run #4: `enable_updater` tidak terdefinisi karena overlay berbeda baseline |
| Java/JNI/C++ compilation | BELUM DIJALANKAN |
| APK, signature, install Android | BELUM DIJALANKAN |
| Default developer mode, persistensi, install ZIP di perangkat | BELUM DIJALANKAN |
| MV3 service worker/content script/popup di browser | BELUM DIJALANKAN |
| ZIP negatif/traversal di native installer | BELUM DIJALANKAN — fixture tersedia saja |
| Chrome Web Store / semua API extension | BELUM DIJALANKAN |

Delapan test tooling: apply dan idempotence; penolakan revisi keliru; preservasi checkout kotor; checksum mismatch sebelum menulis; preservasi args build pengguna; preservasi edit setelah prepare; penolakan file tak terlacak yang akan tertimpa; penolakan path keluar checkout.

Pemeriksaan string referensi JNI/GN tidak membuktikan type signature atau dependency graph bisa dikompilasi. Validitas fixture ZIP tidak membuktikan installer Android aman terhadap arsip tersebut. Temuan RE Lemur di handoff tidak direproduksi; APK Lemur dan report aslinya tidak tersedia.

## Langkah lanjutan yang menentukan

Jalankan GN/build dari source pada Linux untuk menetapkan baseline yang benar-benar bisa dibangun. Jika overlay fork tidak cocok dengan Chromium 132, perbaiki/rebase baseline atau pindahkan perubahan Sharingan ke fork dengan build source yang dapat diverifikasi. Setelah APK berhasil dibuat, jalankan seluruh `TEST_PLAN.md` sebelum menyebut fitur berfungsi pada perangkat.

## Tambahan workflow GitHub Actions standar

- Workflow manual `.github/workflows/android-free.yml` diperiksa dengan **actionlint 1.7.7: PASS** (integrasi shellcheck/pyflakes tidak diaktifkan).
- Pemeriksaan checksum/source/resource paket: **PASS**.
- Test Python kumulatif: **18 PASS**, terdiri dari 8 test prepare dan 10 test driver CI (guard public/Linux/hosted, kapasitas disk, output sukses/gagal, deadline dan status).
- Action checkout v4.2.2, upload-artifact v4.6.2, dan depot_tools dikunci ke commit yang diambil dari upstream saat persiapan.
- Opsi checkout `small`, skip coverage/telemetry/PGO, `concurrent_links`, `use_thin_lto`, serta opsi installer dependency diperiksa terhadap source resmi Chromium 132.
- **Preflight GitHub terverifikasi:** [run #1](https://github.com/wilgooo/sharingan-browser/actions/runs/38576425331), 14 Oktober 2026, commit `61ef07f3f035fb4f3ef9c254edef073f65f7dd12`. Verifikasi source dan 18 tes lolos; cleanup runner sebenarnya menaikkan ruang kosong 84,97 → 113,85 GiB; artifact diagnostik diunggah. Job selesai dalam 1 menit 40 detik.
- **Percobaan build #4:** checkout, dependency sync, system packages, hooks, dan overlay selesai. GN dijalankan dan gagal pada source compatibility. 22 tes tooling lolos. Lihat [BUILD_BLOCKER.md](BUILD_BLOCKER.md) untuk log dan temuan tambahan.
- **Tidak dijalankan:** kompilasi Java/C++/JNI, instalasi APK, dan pengujian extension pada Android.

## Baseline replacement — 2026-10-18

Official Kiwi 105 replaces the Revived fork/Chromium 132 combination. See [BASELINE.md](BASELINE.md) for pinned commits, full-overlay blob comparison and port details. 23 host tests, 8,289 hashes/resource checks, actionlint and shell syntax passed. No APK or successful Linux compile is claimed yet.
