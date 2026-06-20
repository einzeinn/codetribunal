# CodeTribunal — Upgrade Roadmap menuju Track 3: Agent Society

Dokumen ini adalah rencana eksekusi. Urutan prioritas penting — jangan loncat ke UI sebelum arsitektur agent-nya solid, karena juri menilai arsitektur (Technical Depth + Innovation = 60% skor) lebih berat daripada visual.

---

## 0. Prioritas Eksekusi (urutan disarankan)

1. Push repo ke GitHub (blocker untuk submission)
2. Refactor protokol agent: dari linear/scripted → conditional/parallel
3. Beri tiap agent tool access nyata (function calling)
4. Desain & jalankan benchmark vs single-agent baseline
5. Redesign UI/UX jadi courtroom presentation
6. Proof of Alibaba Cloud deployment + architecture diagram + demo video
7. Final polish dokumentasi

Kalau waktu terbatas, urutan 1–4 adalah yang menentukan menang/kalah secara substansi. UI bagus tapi arsitektur linear = "looks like multi-agent, isn't".

---

## 1. Refactor Arsitektur: Linear → Conditional Multi-Agent

### Masalah saat ini
Urutan tetap: AEGIS → AXIOM → METRIC → ARBITER, selalu 3 round, tanpa cabang. Ini secara teknis adalah pipeline, bukan negosiasi.

### Target arsitektur

**Fase 1 — Investigasi Paralel (bukan berurutan)**
Jalankan AEGIS, AXIOM (initial scan, bukan rebuttal), dan METRIC secara paralel (`asyncio.gather`) terhadap source code yang sama, masing-masing dengan tool berbeda (lihat bagian 2). Tiap agent menghasilkan daftar temuan terstruktur (JSON), bukan teks bebas:

```json
{
  "agent": "AEGIS",
  "findings": [
    {
      "id": "F-001",
      "line_range": [42, 47],
      "category": "security",
      "severity": "high",
      "claim": "...",
      "evidence_source": "bandit:B608",
      "confidence": 0.85
    }
  ]
}
```

**Fase 2 — Deteksi Konflik (logika, bukan LLM)**
Sebelum manggil LLM lagi, jalankan fungsi deterministik yang membandingkan `line_range` overlap antar temuan dari agent berbeda. Klasifikasikan:
- **No conflict**: hanya 1 agent flag area itu → langsung masuk laporan, skip debate round untuk item ini.
- **Conflict**: 2+ agent flag area sama dengan kesimpulan berbeda (mis. AEGIS bilang vulnerable, AXIOM/test result bilang sudah di-sanitize) → ini yang masuk ke debate round.

Ini kunci supaya "max 3 rounds" kamu jadi bermakna: round hanya dipakai untuk item yang benar-benar berkonflik, bukan semua temuan.

**Fase 3 — Cross-Examination Bertarget (conditional, bukan fixed)**
Untuk tiap conflict cluster, ARBITER memanggil ulang agent yang terlibat saja (bukan semua 5 agent tiap round) dan minta argumen tambahan secara spesifik:

```
ARBITER → AEGIS: "AXIOM mengklaim input di baris 45 sudah divalidasi oleh
fungsi validate_input() di baris 12. Apakah klaimmu masih berlaku?
Beri counter-evidence atau revisi confidence score."
```

Loop berhenti per-cluster kalau:
- Salah satu agent merevisi confidence-nya turun di bawah threshold (mis. < 0.3) → dianggap withdrawn, atau
- Sudah mencapai round maksimum untuk cluster itu (sarankan 2, bukan 3, supaya cost terkendali), atau
- Confidence kedua belah pihak tetap tinggi → eskalasi ke ARBITER untuk keputusan manual dengan catatan "disputed, low consensus" di laporan akhir (ini justru bagus untuk ditampilkan — menunjukkan sistem jujur soal ketidakpastian, bukan dipaksa konsensus palsu).

**Fase 4 — Verdict**
ARBITER menyusun verdict per item, bukan satu verdict global. Tiap item punya: status (confirmed/dismissed/disputed), severity, reasoning trail (link ke argumen mana yang menang), dan rekomendasi fix.

### Kenapa ini penting untuk skor
Ini langsung menjawab kritik "linear pipeline" dan membuat klaim "negotiation" di README benar-benar terverifikasi dari behavior sistem, bukan dari penamaan.

---

## 2. Tool Access per Agent (jangan cuma persona prompt)

| Agent | Tool nyata yang harus dipanggil (function calling) | Output yang dipakai sebagai evidence |
|---|---|---|
| **LEDGER** | `ast` module (Python) untuk parsing struktur kode jadi case file terindeks | Daftar fungsi/class/import dengan line number, dipakai semua agent lain sebagai referensi lokasi |
| **AEGIS** | `bandit` (security linter) + optional `semgrep` dengan custom rules | Finding dengan rule ID asli (mis. B608 SQL injection), bukan LLM menebak sendiri |
| **AXIOM** | Test runner (`pytest` kalau ada test file) + cek apakah ada validasi/sanitization terkait area yang di-flag AEGIS | Hasil test pass/fail, atau bukti baris kode validasi yang relevan |
| **METRIC** | `radon` (cyclomatic complexity, maintainability index) + `lizard` atau profiling sederhana | Angka numerik nyata, bukan estimasi kualitatif ("kompleksitasnya tinggi") |
| **ARBITER** | Tidak perlu tool eksternal, tapi orchestration logic-nya (conflict detection, round management) harus deterministic code, bukan LLM call | — |

**Kenapa ini krusial**: kriteria Technical Depth (30%) eksplisit minta "custom skills, MCP integrations". Kalau memungkinkan, bungkus tool-tool di atas sebagai MCP server lokal yang dipanggil tiap agent via MCP protocol — ini upgrade signifikan dari sekadar subprocess call, dan beri kamu bahan cerita konkret untuk submission ("agent kami pakai MCP untuk akses tool security/complexity").

Tanpa tool nyata ini, kelima agent secara epistemik membaca sumber informasi yang sama (raw source code) — defense-nya cuma argumen retorik LLM, bukan bukti independen. Itu yang membuat "adversarial" terasa kosmetik.

---

## 3. Desain Benchmark (Measurable Efficiency Gain)

### Dataset
Jangan pakai 1 file class Python kecil — itu tidak menunjukkan apa-apa karena baseline juga gampang. Siapkan:
- 5–10 file/repo kecil-menengah (100–500 baris) dengan **bug yang sengaja disisipkan dan diketahui jumlahnya** — campur kategori: security (SQLi, hardcoded secret, command injection), performance (N+1 query, O(n²) yang harusnya O(n log n)), maintainability (duplicate code, missing error handling).
- Sertakan juga beberapa **false-positive trap** — kode yang terlihat mencurigakan tapi sebenarnya aman (misal raw SQL string tapi parameterized dengan benar) — ini untuk mengukur klaim "false positive rate lebih rendah".

### Baseline
Single-call qwen-max (model terkuat yang kamu pakai) diberi prompt review umum atas file yang sama, sekali jalan, tanpa tool.

### Metrik yang diukur (isi tabel dengan angka asli, bukan kata sifat)

| Metrik | Cara hitung |
|---|---|
| Recall | (bug yang sengaja disisipkan dan terdeteksi) / (total bug yang disisipkan) |
| Precision | (temuan yang benar) / (total temuan yang dilaporkan) |
| False positive rate | (flag pada false-positive trap) / (total false-positive trap) |
| Token cost | total token input+output, dari API response usage field |
| Latency | wall-clock time end-to-end |
| Severity calibration | apakah severity yang diberi cocok dengan ground truth (opsional, nice-to-have) |

### Cara presentasi hasil
Tabel perbandingan langsung: baseline vs CodeTribunal, per metrik, per kategori dataset. Kalau token cost CodeTribunal lebih tinggi (kemungkinan besar iya, karena 5 agent), itu **tidak masalah** asal kamu bisa tunjukkan recall/precision/FP rate naik signifikan — artinya trade-off cost untuk akurasi itu sendiri adalah temuan yang valid dan jujur, lebih kredibel daripada klaim "lebih efisien di semua aspek" yang biasanya tidak realistis.

---

## 4. Redesign UI/UX: Dari Chat → Courtroom Presentation

### Masalah desain saat ini
Tampilan chat bubble per agent itu generic — terlihat seperti grup chat multi-bot, bukan persidangan. Tema courtroom yang kuat di README (medieval, Cinzel font, parchment) tidak terasa di interaksi utamanya kalau formatnya tetap chat linear.

### Konsep layout baru: "Courtroom Floor"

Bayangkan layout seperti panggung sidang, bukan timeline chat:

```
┌─────────────────────────────────────────────────┐
│              🏛️  ARBITER (Judge Bench)            │
│         status: "Mendengarkan argumen..."         │
├──────────────────────┬────────────────────────────┤
│   ⚔️ AEGIS            │   🛡️ AXIOM                  │
│   (Prosecution Table) │   (Defense Table)          │
│   speaking now...     │   waiting / objecting      │
├──────────────────────┴────────────────────────────┤
│   📊 METRIC (Witness Stand) — dipanggil saat       │
│   dibutuhkan evidence, bukan selalu tampil         │
├─────────────────────────────────────────────────────┤
│   📜 EXHIBIT BOARD — menampilkan snippet kode yang │
│   sedang dibahas, highlight baris terkait           │
├─────────────────────────────────────────────────────┤
│   🖋️ LEDGER — transcript log di sidebar/drawer,    │
│   collapsible, bukan main view                     │
└─────────────────────────────────────────────────────┘
```

### Elemen interaksi spesifik

1. **Exhibit Board sebagai fokus utama**, bukan chat. Tiap kali agent menyebutkan baris kode tertentu, kode itu muncul di Exhibit Board dengan highlight, dilabeli "Exhibit A", "Exhibit B", dst. Ini jauh lebih kuat secara visual daripada teks "di baris 45..." dalam chat bubble.

2. **Agent berbicara sebagai statement formal, bukan chat bubble**, dengan format:
   - Avatar/icon agent muncul "aktif" (animasi subtle: glow, scale up) saat gilirannya bicara
   - Teks muncul sebagai "pernyataan resmi" dengan style parchment scroll, bukan rounded bubble
   - Ada label fase di atas: "OPENING STATEMENT", "CROSS-EXAMINATION: Exhibit C", "OBJECTION", "RULING"

3. **"Objection!" sebagai event visual eksplisit.** Saat AXIOM membantah klaim AEGIS (dari conflict detection di bagian 1), trigger animasi singkat (flash merah/gold, teks besar "OBJECTION") sebelum menampilkan argumen baliknya. Ini secara visual menerjemahkan struktur adversarial yang sudah ada di backend.

4. **Verdict sebagai reveal moment**, bukan bubble terakhir di chat. Layar courtroom "freeze", ARBITER bicara terakhir, lalu transisi ke halaman laporan terstruktur (severity breakdown, exhibit per temuan, rekomendasi fix) — semacam "sidang selesai, ini putusan resminya" sebagai dokumen, bukan scroll chat ke bawah.

5. **Gallery / spectator view (opsional, nice-to-have untuk demo video)**: kalau sempat, tampilkan live progress bar fase sidang (Opening → Evidence → Cross-Exam → Verdict) di bagian atas supaya viewer demo video langsung paham di tahap mana sidang berlangsung tanpa harus baca semua teks.

### Implementasi teknis (Next.js + Tailwind, sesuai stack kamu)
- State: simpan "current phase" dan "active speaker" di state global (Zustand/Context), bukan cuma array pesan chat.
- WebSocket payload sebaiknya membawa metadata terstruktur (`phase`, `speaker`, `exhibit_ref`, `is_objection`), bukan cuma string teks — supaya frontend bisa trigger animasi/layout yang tepat tanpa parsing teks.
- Transisi antar fase pakai Framer Motion untuk animasi masuk/keluar elemen (cocok dengan tema dramatis courtroom).
- Font Cinzel/IM Fell English dipertahankan, tapi terapkan di elemen baru (label fase, exhibit tag, verdict scroll) supaya temanya konsisten di seluruh layout baru, bukan cuma chat bubble lama.

### Kenapa ini penting untuk skor
Perubahan ini menyasar Presentation & Documentation (15%) dan memperkuat Innovation (30%) — "tech stack sophistication" dinilai juga dari sejauh mana UI mencerminkan logika sistem yang sebenarnya, bukan generic chat wrapper di atas backend yang menarik.

---

## 5. Submission Checklist (Wajib, Jangan Sampai Terlewat)

- [ ] Push repo ke GitHub, public, license terdeteksi di About section repo
- [ ] Video terpisah (bukan demo video) yang membuktikan backend jalan di Alibaba Cloud, + link ke file kode yang pakai layanan/API Alibaba Cloud
- [ ] Architecture diagram (yang di README sudah ada draft-nya — perbarui setelah refactor bagian 1 & 2)
- [ ] Demo video ~3 menit, upload ke YouTube/Vimeo/Facebook Video, public
- [ ] Text description fitur & fungsionalitas project
- [ ] Tag track: Track 3 — Agent Society
- [ ] Deadline: 9 Juli 2026, 14:00 PDT

---

## 6. Hal yang Tidak Perlu Dikerjakan (supaya fokus)

- Gallery/spectator view real-time multi-user — nice to have, bukan prioritas, skip kalau waktu mepet.
- Blog post untuk Blog Post Award — opsional, kerjakan paling akhir kalau semua di atas sudah selesai.
- Jangan tambah agent ke-6 atau lebih — 5 agent dengan interaksi yang benar-benar conditional/evidence-based lebih kuat daripada 8 agent yang tetap linear.
