# CodeTribunal — Courtroom UI/UX Redesign — Implementation Plan

## Konteks proyek

CodeTribunal adalah sistem code security review berbasis 5 AI agent adversarial:
- **AEGIS** — agent prosecutor, mengajukan temuan/vulnerability (finding)
- **AXIOM** — agent defense, melakukan cross-examination / menyanggah temuan
- **METRIC** — agent analyst, menghitung skor rubric berdasarkan hasil debat
- **ARBITER** — agent judge, memberi ruling/verdict final (dismiss atau accept finding)
- **LEDGER** — agent clerk, mencatat semua keputusan ke record/log

Repo: https://github.com/einzeinn/codetribunal
Stack saat ini: Next.js (App Router atau Pages Router — **cek dulu**, jangan asumsi) + backend FastAPI di Render.

Tujuan task ini: mengubah tampilan hasil review dari UI biasa menjadi **visual novel courtroom style** terinspirasi Ace Attorney, dengan ilustrasi karakter custom per agent.

---

## Step 0 — Audit repo (WAJIB dilakukan sebelum coding apapun)

Sebelum membuat/mengubah file apapun, lakukan audit ini dan laporkan hasilnya:

1. Cek apakah project pakai App Router (`app/`) atau Pages Router (`pages/`).
2. Cek struktur folder komponen saat ini (`components/`, `src/`, dll).
3. Temukan komponen/page yang menampilkan halaman hero/landing — **cari komponen "page ksatria/knight"** yang menahan gerbang di hero section. Komponen ini harus **dihapus total** (termasuk asset gambar terkait jika sudah tidak dipakai di tempat lain).
4. Temukan komponen yang menampilkan hasil review (tempat AEGIS/AXIOM/METRIC/ARBITER/LEDGER outputnya ditampilkan saat ini) — ini target utama yang akan diubah ke courtroom UI.
5. Cek apakah Tailwind CSS sudah terpasang (kemungkinan besar iya untuk stack Next.js standar) dan versi React yang dipakai.
6. Cek apakah ada library animasi terpasang (Framer Motion dll). Jika belum, akan diinstall di Step 1.

Laporkan hasil audit ini sebelum lanjut ke step berikutnya.

---

## Step 1 — Setup dependency

Install Framer Motion untuk semua animasi/transisi (pose swap, slide-in, shake effect, overlay):

```bash
npm install framer-motion
```

Tidak perlu library VN-engine khusus (Ren'Py-style state machine), tidak perlu Three.js/WebGL untuk background. Semua animasi cukup dengan Framer Motion + CSS.

---

## Step 2 — Struktur asset

Buat struktur folder berikut di `public/` (sesuaikan path persis dengan konvensi project setelah audit Step 0):

```
public/
  characters/
    aegis/
      neutral.png
      active.png
    axiom/
      neutral.png
      active.png
    metric/
      neutral.png
      active.png
    arbiter/
      neutral.png
      active.png
    ledger/
      neutral.png
      writing.png
  vectors/
    inquisitor-sword.svg
```

**Catatan penting:** File PNG sprite karakter dan SVG pedang akan diupload manual oleh saya (bukan agent) ke folder ini setelah folder dibuat. Agent hanya perlu membuat struktur foldernya dan menulis kode yang me-reference path ini — tidak perlu generate atau mencari gambar apapun.

### Modifikasi wajib pada SVG pedang (`inquisitor-sword.svg`)

File SVG ini punya warna stroke hardcoded `#1a1a1a` di semua elemen (circle, line, path, text). Ini harus diganti agar adaptif ke dark/light mode:

- Ganti semua `stroke="#1a1a1a"` menjadi `stroke="currentColor"`
- Ganti `fill="#1a1a1a"` (pada elemen text) menjadi `fill="currentColor"`
- Bungkus penggunaan SVG ini dengan elemen yang punya `color: var(--foreground)` atau setara token warna teks utama project, supaya otomatis ikut tema.

---

## Step 3 — Komponen karakter (`CourtroomCharacter`)

Buat 1 komponen reusable untuk semua karakter, bukan 5 komponen terpisah:

```
components/courtroom/CourtroomCharacter.tsx
```

Props yang dibutuhkan:
- `agentId`: `'aegis' | 'axiom' | 'metric' | 'arbiter' | 'ledger'`
- `pose`: `'neutral' | 'active'`
- `isSpeaking`: boolean (untuk trigger animasi highlight/scale saat giliran bicara)
- `dialogue`: string | null (teks yang ditampilkan di dialogue box)

Setiap agent punya warna aksen tetap (dari ilustrasi yang sudah dibuat):
- AEGIS → merah (`#D85A30` / sesuai warna kostum di sprite)
- AXIOM → navy/biru (`#185FA5`)
- METRIC → abu-abu netral (`#5F5E5A`)
- ARBITER → hitam-emas (gunakan emas sebagai aksen, misal `#BA7517`)
- LEDGER → coklat/emas muted (warna vest di sprite)

Simpan mapping warna ini di satu file konstanta, misal `lib/courtroom-theme.ts`, supaya konsisten dipakai ulang di semua komponen.

### Dialogue box

Sesuai keputusan desain: dialogue box menempel dari **bagian dada karakter sampai ke bawah area panel** (bukan kotak nama generic terpisah ala Ace Attorney klasik). Posisi: `absolute`, dimulai dari kira-kira 45-50% tinggi sprite ke bawah, dengan background semi-transparent menggunakan warna aksen agent tersebut (opacity rendah, misal 10-15%, dengan border solid warna aksen).

Header kecil di dalam dialogue box menampilkan nama agent + role badge (misal "AEGIS — Prosecutor").

---

## Step 4 — Layout utama courtroom

Buat komponen container:

```
components/courtroom/CourtroomStage.tsx
```

Layout (urutan z-index dari bawah ke atas):

1. **Background layer** — CSS flat/gradient saja, TIDAK pakai gambar courtroom realistis. Gunakan gradient halus 2 warna gelap netral (misal dari `#1a1a1a` ke `#2a2418`, nuansa kayu/mahogany gelap tanpa tekstur foto) plus aksen garis tipis dekoratif di pinggir (opsional, pakai CSS border atau SVG garis simpel — bukan ilustrasi detail).

2. **Tier utama — 3 panel berdampingan**: AEGIS, AXIOM, METRIC selalu tampil bersamaan, grid 3 kolom sejajar (representasi POV penonton melihat ketiga analis berdiri/duduk berdampingan). Panel yang sedang `isSpeaking=true` mendapat: scale sedikit lebih besar (1.0 → 1.05), background sedikit lebih terang, dan border aksen warnanya menyala.

3. **ARBITER overlay** — saat ARBITER aktif memberi ruling, muncul sebagai overlay yang dominan secara visual di atas 3 panel (bukan menutup 100% — sesuai diskusi sebelumnya, posisi "di atas" secara hierarki tapi 3 panel tetap terlihat redup/dim di belakang, BUKAN full opaque cover). Animasi masuk: slide down dari atas + sedikit efek "bang" (scale overshoot lalu settle) untuk merepresentasikan ketukan gavel.

4. **LEDGER notification system** — TIDAK pernah tampil statis. Behavior:
   - Default: tidak terlihat sama sekali.
   - Saat event penting terjadi (verdict final / finding di-dismiss / finding di-confirm): muncul **toast singkat** di posisi bottom-center, isi singkat (misal "LEDGER: AEGIS-F001 dismissed"), auto-dismiss setelah ~1.5 detik.
   - Setelah toast hilang, muncul **badge kecil dengan counter** di pojok kanan bawah (persist, tidak hilang sendiri) menampilkan jumlah entry yang sudah tercatat.
   - Badge bisa diklik untuk membuka **panel log slide-in dari sisi kanan**, menampilkan riwayat lengkap semua entry LEDGER pada sesi tersebut, urutan terbaru di atas.

---

## Step 5 — State management & event mapping

Gunakan React state sederhana di level `CourtroomStage`, tidak perlu state management library eksternal (Redux/Zustand) kecuali project sudah memakainya untuk hal lain.

State yang dibutuhkan:
```typescript
activeSpeaker: 'aegis' | 'axiom' | 'metric' | 'arbiter' | null
agentPoses: Record<AgentId, 'neutral' | 'active'>
ledgerEntries: { id: string; text: string; timestamp: string }[]
isLedgerPanelOpen: boolean
```

### Mapping event backend → pose & UI trigger

Sesuaikan dengan struktur event/response asli dari backend FastAPI CodeTribunal (cek dulu bagaimana backend mengirim event — kemungkinan via WebSocket streaming berdasarkan konteks project). Mapping yang disepakati:

| Event dari backend | Agent aktif | Pose | Aksi UI tambahan |
|---|---|---|---|
| Finding baru diajukan | AEGIS | active | dialogue muncul isi finding |
| Cross-examination / sanggahan | AXIOM | active | dialogue muncul isi sanggahan |
| Rubric score dihitung/update | METRIC | active | dialogue muncul ringkasan skor |
| Verdict/ruling final | ARBITER | active | overlay muncul + 3 panel dim + LEDGER toast otomatis terpicu setelahnya |
| Selain di atas (idle/menunggu) | — | neutral untuk semua | — |

LEDGER tidak punya "giliran bicara" dalam arti dia bukan bagian dari `activeSpeaker` — dia murni reactive terhadap event penting (terutama hasil ruling ARBITER), sesuai keputusan desain sebelumnya.

**Catatan untuk agent IDE:** jika struktur event backend yang sebenarnya berbeda dari asumsi tabel di atas, sesuaikan mapping-nya mengikuti event yang benar-benar dikirim backend — yang penting prinsip pemicunya (siapa aktif kapan) tetap sama.

---

## Step 6 — Animasi (Framer Motion)

- Pose swap (`neutral` → `active`): gunakan `AnimatePresence` dengan crossfade singkat (200-250ms), opsional sedikit `scale` dari 0.98 → 1.
- Panel speaking highlight: `animate` pada `scale` dan `boxShadow`/border opacity, transisi 200ms ease-out.
- ARBITER overlay masuk: `initial={{ y: -40, opacity: 0 }}` → `animate={{ y: 0, opacity: 1 }}` dengan sedikit spring overshoot (`type: 'spring', bounce: 0.3`).
- LEDGER toast: slide up + fade in dari bawah, hold, lalu fade out (gunakan `AnimatePresence` dengan delay exit).
- LEDGER panel slide-in: `translateX` dari `100%` ke `0%`, ease standar 300ms.

Hormati `prefers-reduced-motion` — kurangi/skip animasi transform besar jika user mengaktifkan setting tersebut di OS, sisakan crossfade opacity saja.

---

## Step 7 — Hapus komponen lama

1. Cari dan **hapus total** komponen "ksatria/knight" yang menahan gerbang di hero section (ditemukan saat audit Step 0).
2. Hapus asset gambar terkait knight tersebut jika tidak dipakai di tempat lain dalam codebase (cek dengan grep sebelum hapus file).
3. Ganti elemen gerbang di hero section dengan SVG pedang (`inquisitor-sword.svg`) yang sudah dimodifikasi warnanya (lihat Step 2).

---

## Step 8 — Integrasi ke halaman hasil review

Pasang `CourtroomStage` di halaman/route tempat hasil review CodeTribunal ditampilkan (ditemukan saat audit Step 0, poin 4). Pastikan:
- Data event dari backend (WebSocket atau polling, sesuai implementasi asli) di-mapping ke state `CourtroomStage` sesuai tabel Step 5.
- Tidak menghapus logic backend/data-fetching yang sudah ada — hanya mengganti layer presentasi/UI-nya.

---

## Urutan eksekusi yang disarankan untuk agent

1. Step 0 (audit, lapor hasil)
2. Step 1 (install dependency)
3. Step 2 (buat struktur folder asset — tanpa isi gambar)
4. Step 3 (komponen `CourtroomCharacter`)
5. Step 4 (komponen `CourtroomStage` — layout & LEDGER system)
6. Step 5 (state & event mapping — sesuaikan ke backend asli)
7. Step 6 (animasi)
8. Step 7 (hapus knight component, pasang sword SVG)
9. Step 8 (integrasi ke page asli)

Setelah setiap step besar (terutama Step 0, 3, 4, 8), berhenti dan tunggu konfirmasi sebelum lanjut ke step berikutnya — supaya tidak terjadi revisi besar di tengah jalan jika ada penyesuaian arah.
