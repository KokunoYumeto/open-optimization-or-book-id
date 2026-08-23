import React, { useState } from "react";
import { Terminal } from "lucide-react";
import { Tex } from "./math.jsx";

/* ============================================================
   EXCEL SOLVER — tutorial
   ISE 5406

   Tiga jenis masalah, masing-masing disusun sebagai lembar kerja agar
   mahasiswa dapat melihat dengan tepat sel mana yang harus diisi:

     • LP   (perencanaan produksi)
     • IP   (knapsack biner)
     • NLP  (pencocokan kurva / regresi nonlinear)

   Setiap tab menampilkan:
     • Lembar kerja beserta rumusnya
     • Dialog Solver Parameters (maket)
     • Hasil setelah Solve
     • Catatan pengajaran tentang jebakan khusus Excel
   ============================================================ */

const TABS = [
  { key: "lp", label: "LP — Perencanaan produksi", color: "#1f4e3d" },
  { key: "ip", label: "IP — Ransel 0/1", color: "#0b3da0" },
  { key: "nlp", label: "NLP — Pencocokan kurva", color: "#7a3da0" },
];

// ============================================================
// Komponen utama
// ============================================================
export default function ExcelSolverDemo() {
  const [tab, setTab] = useState("lp");
  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 24px 80px" }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>
        Excel Solver — Menyiapkan Optimisasi di Lembar Kerja
      </h1>
      <p style={{ color: "#666", marginBottom: 18, maxWidth: 880 }}>
        Add-in <i>Solver</i> di Excel menangani LP, IP, dan NLP kecil
        langsung di dalam lembar kerja. Kuncinya adalah menata sel dengan
        cermat agar model mudah dibaca, serta menggunakan rumus seperti{" "}
        <code style={inlineCode}>SUMPRODUCT</code>,{" "}
        <code style={inlineCode}>INDEX</code>, serta{" "}
        <code style={inlineCode}>SUMIFS</code>, bukan persamaan yang ditulis
        langsung. Berikut tiga contoh lengkap.
      </p>

      <EnableSolverPanel />

      <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: "8px 14px",
              border: "1px solid #ccc",
              borderRadius: 6,
              cursor: "pointer",
              background: tab === t.key ? t.color : "#fff",
              color: tab === t.key ? "#fff" : "#222",
              fontWeight: tab === t.key ? 700 : 500,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "lp" && <LPExample />}
      {tab === "ip" && <IPExample />}
      {tab === "nlp" && <NLPExample />}

      <FormulaCheatSheet />
      <PedagogicalNotes />
    </div>
  );
}

// ============================================================
// Mengaktifkan Solver
// ============================================================
function EnableSolverPanel() {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: 16, border: "1px solid #d3d3d3", borderRadius: 8, background: "#fafafa" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "10px 14px",
          background: "transparent",
          border: 0,
          cursor: "pointer",
          fontWeight: 700,
          fontSize: 14,
          color: "#222",
          textAlign: "left",
        }}
      >
        <Terminal size={16} />
        Aktifkan add-in Solver
        <span style={{ color: "#888", fontWeight: 400, fontSize: 12, marginLeft: 6 }}>
          ({open ? "klik untuk menciutkan" : "klik untuk memperluas"})
        </span>
      </button>
      {open && (
        <div style={{ padding: "0 14px 14px 14px", fontSize: 13, color: "#333", lineHeight: 1.55 }}>
          <ol style={{ paddingLeft: 22, margin: 0 }}>
            <li>
              <b>Windows:</b> File (Berkas) → Options (Opsi) → Add-ins → Manage (Kelola):{" "}
              <i>Excel Add-ins</i> → Go… → centang{" "}
              <b>Solver Add-in</b> → OK.
            </li>
            <li>
              <b>Mac:</b> menu Tools (Alat) → Excel Add-ins → centang{" "}
              <b>Solver Add-in</b> → OK.
            </li>
            <li>
              Setelah diaktifkan, tombol <b>Solver</b> muncul di grup Analyze
              pada tab <b>Data</b>.
            </li>
            <li>
              <b>Tiga mesin</b> tersedia dalam Solver: <i>Simplex LP</i>{" "}
              (linear), <i>GRG Nonlinear</i> (nonlinear mulus, bawaan),{" "}
              <i>Evolutionary</i> (tidak mulus / diskontinu /
              tidak terdiferensialkan).
            </li>
          </ol>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Contoh LP
// ============================================================
function LPExample() {
  // Tata letak lembar kerja:
  //   B  C  D
  //   ----------
  // 2 |    kursi  meja   (tajuk)
  // 3 |  x  3.6   0.8     (variabel keputusan)
  // 4 |  c  3     5       (laba per unit)
  // 5 |  Laba total:      =SUMPRODUCT(C3:D3, C4:D4)   →  14.8  (target)
  // 7 |    kendala     terpakai   batas
  // 8 |    kayu        =2*C3 + 1*D3   8
  // 9 |    tenaga kerja =1*C3 + 3*D3   6
  return (
    <>
      <div style={problemBox}>
        <Tex block>
          {String.raw`\max\;\; 3\,x_{\text{kursi}} + 5\,x_{\text{meja}} \;\;\text{dengan kendala}\;\; 2 x_{\text{c}} + x_{\text{t}} \le 8,\;\; x_{\text{c}} + 3 x_{\text{t}} \le 6,\;\; x \ge 0`}
        </Tex>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(440px, 1fr) minmax(420px, 1fr)", gap: 22 }}>
        <div>
          <Spreadsheet
            cells={[
              ["", "B", "C", "D", "E"],
              ["1", "", "kursi", "meja", ""],
              ["2", "x  (keputusan)", "0", "0", "← sel yang diubah"],
              ["3", "c  (laba/unit)", "3", "5", ""],
              ["4", "Laba (sel target)", "=SUMPRODUCT(C2:D2, C3:D3)", "0", ""],
              ["5", "", "", "", ""],
              ["6", "kendala", "LHS (rumus ruas kiri)", "≤", "RHS (ruas kanan)"],
              ["7", "kayu", "=2*C2 + 1*D2", "≤", "8"],
              ["8", "tenaga kerja", "=1*C2 + 3*D2", "≤", "6"],
            ]}
            highlight={{
              decision: { rows: [2], cols: [2, 3] },
              objective: { rows: [4], cols: [2] },
              constraints: { rows: [7, 8], cols: [2] },
            }}
          />
        </div>

        <div>
          <SolverDialog
            target="$C$4"
            sense="Max"
            changing="$C$2:$D$2"
            constraints={[
              { lhs: "$C$7", op: "≤", rhs: "$E$7" },
              { lhs: "$C$8", op: "≤", rhs: "$E$8" },
              { lhs: "$C$2:$D$2", op: "≥", rhs: "0" },
            ]}
            method="Simplex LP"
          />
          <ResultBlock
            title="Setelah mengeklik Solve"
            result={[
              ["x_kursi", "3.6"],
              ["x_meja", "0.8"],
              ["Laba", "14.8 ★"],
              ["kayu terpakai", "8 (aktif)"],
              ["tenaga kerja terpakai", "6 (aktif)"],
            ]}
          />
          <Notes
            title="Mengapa SUMPRODUCT?"
            body={`Karena rumus ini dapat mengikuti pertambahan jumlah variabel dengan baik. Rumus sel yang sama, =SUMPRODUCT(decision_range, coefficient_range), berlaku untuk 2 maupun 200 variabel. Hindari =3*C2+5*D2 — Anda harus menyuntingnya kembali setiap kali menambahkan variabel.`}
          />
          <Notes
            title="Sensitivity Report (Laporan Sensitivitas)"
            body={`Setelah Solver selesai, tersedia tiga laporan: Answer, Sensitivity, dan Limits. Laporan Sensitivity memuat harga bayangan (variabel dual kendala) dan biaya tereduksi. Gunakan laporan ini untuk analisis sensitivitas tanpa menyelesaikan ulang model.`}
          />
        </div>
      </div>
    </>
  );
}

// ============================================================
// Contoh IP — knapsack
// ============================================================
function IPExample() {
  return (
    <>
      <div style={problemBox}>
        <Tex block>
          {String.raw`\max\;\; \sum_i v_i\, x_i \;\;\text{dengan kendala}\;\; \sum_i w_i\, x_i \le W,\;\; x_i \in \{0, 1\}`}
        </Tex>
        <div style={{ fontSize: 13, color: "#444", marginTop: 4 }}>
          Enam barang, batas berat 50. Solusi optimal: pilih barang 1, 2, 5, dan 6 (nilai
          = 240, berat = 50).
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(440px, 1fr) minmax(420px, 1fr)", gap: 22 }}>
        <div>
          <Spreadsheet
            cells={[
              ["", "B", "C", "D", "E"],
              ["1", "barang", "nilai", "berat", "x  (0/1)"],
              ["2", "1", "60", "10", "0"],
              ["3", "2", "100", "20", "0"],
              ["4", "3", "120", "30", "0"],
              ["5", "4", "80", "25", "0"],
              ["6", "5", "30", "5", "0"],
              ["7", "6", "50", "15", "0"],
              ["8", "Total", "=SUMPRODUCT(C2:C7, E2:E7)", "=SUMPRODUCT(D2:D7, E2:E7)", ""],
              ["9", "Kapasitas", "", "50", ""],
            ]}
            highlight={{
              decision: { rows: [2, 3, 4, 5, 6, 7], cols: [4] },
              objective: { rows: [8], cols: [2] },
              constraints: { rows: [8], cols: [3] },
            }}
          />
        </div>
        <div>
          <SolverDialog
            target="$C$8"
            sense="Max"
            changing="$E$2:$E$7"
            constraints={[
              { lhs: "$D$8", op: "≤", rhs: "$D$9" },
              { lhs: "$E$2:$E$7", op: "= binary", rhs: "" },
            ]}
            method="Simplex LP"
            note="Menambahkan kendala 'bin' (binary/biner) memaksa nilai 0/1 — Simplex LP menanganinya secara otomatis dengan branch-and-bound (pencabangan dan pembatasan)."
          />
          <ResultBlock
            title="Setelah mengeklik Solve"
            result={[
              ["barang 1", "1"],
              ["barang 2", "1"],
              ["barang 3", "0"],
              ["barang 4", "0"],
              ["barang 5", "1"],
              ["barang 6", "1"],
              ["Nilai total", "240 ★"],
              ["Berat total", "50 / 50"],
            ]}
          />
          <Notes
            title="Kendala bilangan bulat biner"
            body={`Dalam dialog Solver, klik Add → pilih 'bin' dari menu tarik turun operator → biarkan Constraint kosong. Excel menuliskannya sebagai $E$2:$E$7 = binary. Untuk bilangan bulat umum, gunakan 'int'. Simplex LP menyelesaikannya dengan branch-and-bound (pencabangan dan pembatasan); untuk ribuan variabel bilangan bulat, prosesnya dapat berjalan lambat (batas Excel Solver versi gratis: 200 variabel / 100 kendala).`}
          />
        </div>
      </div>
    </>
  );
}

// ============================================================
// Contoh NLP — pencocokan kurva
// ============================================================
function NLPExample() {
  return (
    <>
      <div style={problemBox}>
        <Tex block>
          {String.raw`\min_{a, b, c}\;\; \sum_i \big(y_i - (a \cdot e^{-b \cdot x_i} + c)\big)^2`}
        </Tex>
        <div style={{ fontSize: 13, color: "#444", marginTop: 4 }}>
          Cocokkan peluruhan eksponensial <Tex>{`y = a e^{-b x} + c`}</Tex> dengan
          data amatan. Model ini mulus dan nonkonveks dalam <Tex>{`b`}</Tex> — sangat cocok
          untuk GRG Nonlinear.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(440px, 1fr) minmax(420px, 1fr)", gap: 22 }}>
        <div>
          <Spreadsheet
            cells={[
              ["", "B", "C", "D", "E"],
              ["1", "Parameter", "", "", ""],
              ["2", "a", "1.0", "← tebakan awal", ""],
              ["3", "b", "0.5", "", ""],
              ["4", "c", "0.0", "", ""],
              ["5", "", "", "", ""],
              ["6", "x", "y_obs (amatan)", "y_pred (prediksi)", "(y−ŷ)²"],
              ["7", "0", "5.1", "=$C$2*EXP(-$C$3*B7)+$C$4", "=(C7-D7)^2"],
              ["8", "1", "3.4", "=$C$2*EXP(-$C$3*B8)+$C$4", "=(C8-D8)^2"],
              ["9", "2", "2.2", "=$C$2*EXP(-$C$3*B9)+$C$4", "=(C9-D9)^2"],
              ["10", "3", "1.5", "=$C$2*EXP(-$C$3*B10)+$C$4", "=(C10-D10)^2"],
              ["11", "4", "1.0", "=$C$2*EXP(-$C$3*B11)+$C$4", "=(C11-D11)^2"],
              ["12", "SSE", "", "", "=SUM(E7:E11)"],
            ]}
            highlight={{
              decision: { rows: [2, 3, 4], cols: [2] },
              objective: { rows: [12], cols: [4] },
            }}
          />
        </div>
        <div>
          <SolverDialog
            target="$E$12"
            sense="Min"
            changing="$C$2:$C$4"
            constraints={[]}
            method="GRG Nonlinear"
            note="GRG menangani masalah nonlinear mulus tanpa kendala melalui gradien tereduksi. Untuk masalah tidak mulus atau diskontinu (misalnya, rumus Anda memuat IF), beralihlah ke Evolutionary."
          />
          <ResultBlock
            title="Nilai konvergen"
            result={[
              ["a", "5.043"],
              ["b", "0.422"],
              ["c", "0.064"],
              ["SSE", "0.0021 ★"],
              ["RMSE", "0.0207"],
            ]}
          />
          <Notes
            title="GRG versus Evolutionary"
            body={`GRG = Generalized Reduced Gradient — metode untuk NLP mulus. Metode ini cepat dan akurat, tetapi hanya menemukan optimum LOKAL dan memerlukan turunan. Evolutionary dapat digunakan untuk masalah apa pun (tidak mulus, diskontinu, dengan IF dan CHOOSE), tetapi lambat dan stokastik. Untuk pencocokan kurva → GRG. Untuk masalah kombinatorial / penjadwalan → Evolutionary.`}
          />
          <Notes
            title="Gunakan Multistart untuk solusi global"
            body={`Pada tab GRG di Solver Options, centang 'Multistart'. Opsi ini menjalankan GRG dari banyak titik awal acak dan mempertahankan hasil terbaik. Secara efektif, ini adalah pencarian basin-hopping — jauh lebih tangguh untuk masalah nonkonveks dengan banyak minimum lokal.`}
          />
        </div>
      </div>
    </>
  );
}

// ============================================================
// Perender lembar kerja
// ============================================================
function Spreadsheet({ cells, highlight = {} }) {
  return (
    <div style={panel}>
      <div style={{ fontFamily: "monospace", fontSize: 10, color: "#888", letterSpacing: "0.18em", textTransform: "uppercase", marginBottom: 6 }}>
        Tata letak lembar kerja
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontFamily: "Calibri, Arial, sans-serif", fontSize: 12 }}>
          <tbody>
            {cells.map((row, i) => (
              <tr key={i}>
                {row.map((c, j) => {
                  const isRowLabel = j === 0;
                  const isColHeader = i === 0 && j > 0;
                  const isHighlighted =
                    !isRowLabel &&
                    !isColHeader &&
                    Object.entries(highlight).some(
                      ([key, h]) => h.rows.includes(i) && h.cols.includes(j)
                    );
                  let bg = "#fff";
                  let color = "#222";
                  if (isRowLabel || isColHeader) {
                    bg = "#e7e7e7";
                    color = "#444";
                  } else if (isHighlighted) {
                    if (highlight.decision?.rows.includes(i) && highlight.decision?.cols.includes(j))
                      bg = "#fff4c8";
                    else if (highlight.objective?.rows.includes(i) && highlight.objective?.cols.includes(j))
                      bg = "#d4edda";
                    else if (highlight.constraints?.rows.includes(i) && highlight.constraints?.cols.includes(j))
                      bg = "#f8d7da";
                  }
                  return (
                    <td
                      key={j}
                      style={{
                        border: "1px solid #d0d0d0",
                        padding: "4px 8px",
                        background: bg,
                        color,
                        minWidth: 80,
                        textAlign: isRowLabel || isColHeader ? "center" : (typeof c === "string" && c.startsWith("=") ? "left" : "right"),
                        fontWeight: isRowLabel || isColHeader ? 700 : 400,
                        fontFamily: typeof c === "string" && c.startsWith("=") ? "monospace" : "inherit",
                        fontSize: typeof c === "string" && c.startsWith("=") ? 11 : 12,
                      }}
                    >
                      {c}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 8, fontSize: 11, color: "#555", display: "flex", gap: 16, flexWrap: "wrap" }}>
        <span>
          <span style={{ background: "#fff4c8", padding: "2px 8px" }}>kuning</span>
          &nbsp;= variabel keputusan (sel yang diubah)
        </span>
        <span>
          <span style={{ background: "#d4edda", padding: "2px 8px" }}>hijau</span>
          &nbsp;= fungsi tujuan (sel target)
        </span>
        <span>
          <span style={{ background: "#f8d7da", padding: "2px 8px" }}>merah</span>
          &nbsp;= ruas kiri kendala
        </span>
      </div>
    </div>
  );
}

// ============================================================
// Maket dialog Solver
// ============================================================
function SolverDialog({ target, sense, changing, constraints, method, note }) {
  return (
    <div style={{ ...panel, marginBottom: 12, background: "#f0f0f0" }}>
      <div style={{ background: "#0078d7", color: "#fff", padding: "6px 10px", marginTop: -12, marginLeft: -12, marginRight: -12, borderRadius: "8px 8px 0 0", fontWeight: 700, fontSize: 13 }}>
        Solver Parameters (Parameter Solver)
      </div>
      <table style={{ width: "100%", marginTop: 8, fontSize: 12, fontFamily: "Calibri, Arial, sans-serif" }}>
        <tbody>
          <tr>
            <td style={{ padding: 4, color: "#444" }}>Set Objective (Tetapkan Tujuan):</td>
            <td><code style={excelCode}>{target}</code></td>
          </tr>
          <tr>
            <td style={{ padding: 4, color: "#444" }}>To (Ke):</td>
            <td>
              <span style={{ marginRight: 12 }}>{sense === "Max" ? "● Max" : "○ Max"}</span>
              <span style={{ marginRight: 12 }}>{sense === "Min" ? "● Min" : "○ Min"}</span>
              <span>○ Value of (Nilai)</span>
            </td>
          </tr>
          <tr>
            <td style={{ padding: 4, color: "#444" }}>By Changing Variable Cells (Dengan Mengubah Sel Variabel):</td>
            <td><code style={excelCode}>{changing}</code></td>
          </tr>
          <tr>
            <td style={{ padding: 4, color: "#444", verticalAlign: "top" }}>Subject to the Constraints (Dengan Kendala):</td>
            <td>
              <div style={{ background: "#fff", border: "1px solid #ccc", padding: 4, fontFamily: "monospace", fontSize: 11, minHeight: 60 }}>
                {constraints.length === 0 ? (
                  <span style={{ color: "#999" }}>(tanpa kendala)</span>
                ) : (
                  constraints.map((c, i) => (
                    <div key={i}>
                      {c.lhs} {c.op} {c.rhs}
                    </div>
                  ))
                )}
              </div>
            </td>
          </tr>
          <tr>
            <td style={{ padding: 4, color: "#444" }}>Solving Method (Metode Penyelesaian):</td>
            <td><code style={excelCode}>{method}</code></td>
          </tr>
        </tbody>
      </table>
      <div style={{ marginTop: 6, textAlign: "right" }}>
        <button style={{ ...solveBtn }}>Solve (Selesaikan)</button>
        <button style={{ ...solveBtn, background: "#fff", color: "#444", marginLeft: 6 }}>Close (Tutup)</button>
      </div>
      {note && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#444", lineHeight: 1.5, padding: "8px 10px", background: "#fff8e1", border: "1px solid #f5d68d", borderRadius: 4 }}>
          {note}
        </div>
      )}
    </div>
  );
}

const excelCode = {
  fontFamily: "monospace",
  background: "#fff",
  padding: "2px 6px",
  border: "1px solid #ccc",
  fontSize: 11,
};
const solveBtn = {
  padding: "4px 14px",
  background: "#0078d7",
  color: "#fff",
  border: "1px solid #005bb5",
  borderRadius: 3,
  fontSize: 13,
  cursor: "pointer",
};

// ============================================================
// Blok hasil
// ============================================================
function ResultBlock({ title, result }) {
  return (
    <div style={{ ...panel, marginBottom: 12 }}>
      <div style={{ fontFamily: "monospace", fontSize: 10, color: "#888", letterSpacing: "0.18em", textTransform: "uppercase", marginBottom: 6 }}>
        {title}
      </div>
      <table style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}>
        <tbody>
          {result.map(([k, v], i) => (
            <tr key={i} style={{ borderBottom: "1px dotted #eee" }}>
              <td style={{ padding: "3px 6px", color: "#666" }}>{k}</td>
              <td style={{ padding: "3px 6px", textAlign: "right", color: v.includes("★") ? "#c8311c" : "#222", fontWeight: v.includes("★") ? 700 : 400 }}>
                {v}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// Blok catatan
// ============================================================
function Notes({ title, body }) {
  return (
    <div style={{ marginBottom: 10, padding: "8px 12px", background: "#fffaf0", border: "1px solid #ece8dd", borderRadius: 6, fontSize: 13, lineHeight: 1.5 }}>
      <b>{title}.</b> {body}
    </div>
  );
}

// ============================================================
// Ringkasan rumus
// ============================================================
function FormulaCheatSheet() {
  return (
    <div style={{ ...panel, marginTop: 18 }}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>
        Rumus Excel yang akan digunakan dalam model optimisasi
      </div>
      <table style={{ width: "100%", fontFamily: "monospace", fontSize: 12, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#f0f0f0" }}>
            <th style={th}>rumus</th>
            <th style={th}>fungsinya</th>
            <th style={th}>penggunaan umum</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["SUMPRODUCT(A1:A5, B1:B5)", "hasil kali titik dari dua rentang", "fungsi tujuan linear; ruas kiri kendala"],
            ["SUM(range)", "jumlah suatu rentang", "total; kendala satu sisi"],
            ["IF(test, val_if_true, val_if_false)", "bersyarat", "penetapan harga per segmen; hanya dengan mesin Evolutionary"],
            ["MIN(...)/MAX(...)", "minimum / maksimum suatu rentang", "waktu penyelesaian maksimum (makespan); pendapatan maksimum di antara produk"],
            ["INDEX(arr, row, col)", "mencari berdasarkan indeks", "parameter berindeks dalam model bergaya matriks"],
            ["MATCH(val, range, 0)", "menemukan baris yang memuat val", "mencari pasangan dengan INDEX"],
            ["VLOOKUP/XLOOKUP", "pencarian vertikal", "mengambil parameter dari tabel parameter"],
            ["SUMIFS(sum_range, crit_range, criterion, ...)", "jumlah bersyarat", "kendala yang diagregasikan menurut kelompok"],
            ["MMULT(A, B)", "perkalian matriks (Ctrl+Shift+Enter)", "Ax untuk A umum; jarang digunakan dalam Solver"],
            ["TRANSPOSE(range)", "transpos vektor / matriks", "mengubah baris parameter menjadi kolom"],
            ["EXP(x), LN(x), POWER(x, n)", "fungsi elementer", "NLP; model logistik / eksponensial"],
            ["RAND() / RANDBETWEEN(a, b)", "sampel acak", "eksperimen stokastik (JANGAN di dalam sel target Solver!)"],
          ].map(([f, what, use], i) => (
            <tr key={i} style={{ borderBottom: "1px dotted #eee" }}>
              <td style={{ padding: 6, fontWeight: 700 }}>{f}</td>
              <td style={{ padding: 6 }}>{what}</td>
              <td style={{ padding: 6, color: "#555" }}>{use}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 10, padding: "8px 12px", background: "#fff8e1", border: "1px solid #f5d68d", borderRadius: 4, fontSize: 12, lineHeight: 1.5, color: "#3d2f00" }}>
        <b>Jebakan — RAND() di dalam Solver.</b> Solver mengevaluasi ulang sel
        target berkali-kali; jika target Anda bergantung pada RAND(), nilainya
        berubah pada setiap iterasi dan Solver tidak akan pernah konvergen. Hitung
        data acak SEKALI (tempel sebagai nilai) sebelum menyelesaikan model.
      </div>
    </div>
  );
}
const th = { padding: 6, textAlign: "left", borderBottom: "1px solid #ccc" };

// ============================================================
// Catatan pengajaran
// ============================================================
function PedagogicalNotes() {
  return (
    <div style={{ marginTop: 28, padding: 16, background: "#fff8e1", borderRadius: 10, border: "1px solid #f5d68d" }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>
        <Terminal size={14} style={{ verticalAlign: "middle", marginRight: 6 }} />
        Catatan untuk kelas
      </div>
      <ul style={{ margin: 0, paddingLeft: 22, lineHeight: 1.6, fontSize: 14, color: "#3d2f00" }}>
        <li>
          <b>Tiga blok per model.</b> Variabel keputusan (disorot
          kuning), rumus fungsi tujuan (hijau), dan rumus ruas kiri kendala
          (merah). Memisahkannya secara visual membuat model terdokumentasi
          dengan sendirinya dan memungkinkan mahasiswa memeriksa dialog
          secara sekilas.
        </li>
        <li>
          <b>Gunakan SUMPRODUCT.</b> Rumus ini mudah diskalakan seiring pertambahan ukuran model dan terbaca sebagai
          'hasil kali titik', alih-alih dijabarkan menjadi +B2*C2+B3*C3+…. Ini
          adalah rumus terpenting dalam optimisasi lembar kerja.
        </li>
        <li>
          <b>Pilih mesin yang tepat.</b> Simplex LP untuk masalah linear/bilangan bulat.
          GRG Nonlinear untuk masalah nonlinear mulus (pencocokan kurva, NLP). Evolutionary
          untuk masalah tidak mulus (IF/CHOOSE) dan kombinatorial.
        </li>
        <li>
          <b>Batas ukuran Excel Solver versi gratis.</b> 200 variabel
          keputusan dan 100 kendala (di luar batas variabel dan kendala bilangan bulat).
          Jika melampaui batas itu, gunakan Frontline Solver SDK / Premium
          Solver Pro komersial atau beralih ke Python (PuLP/Gurobi/dan sebagainya).
        </li>
        <li>
          <b>Sensitivity Report (Laporan Sensitivitas).</b> Untuk LP, Solver menghasilkan
          laporan Sensitivity yang memuat harga bayangan dan informasi rentang — informasi
          yang sama dengan atribut Pi / SARHSLow dalam Gurobi atau atribut
          .pi dalam PuLP. Selalu buat laporan ini untuk LP kelas produksi.
        </li>
        <li>
          <b>OpenSolver.</b> Add-in Excel gratis yang menggantikan
          Solver bawaan dengan CBC dari COIN-OR (tanpa batas ukuran) dan mendukung
          Gurobi / CPLEX sebagai backend. Ini merupakan pengganti langsung untuk
          pekerjaan optimisasi lembar kerja yang serius.
        </li>
      </ul>
    </div>
  );
}

const panel = { background: "#fafafa", border: "1px solid #ddd", borderRadius: 8, padding: 12 };
const problemBox = { marginBottom: 16, padding: "12px 16px", background: "#f6f4ee", border: "1px solid #ece8dd", borderRadius: 8 };
const inlineCode = { background: "#f0eee9", padding: "1px 6px", borderRadius: 4, fontFamily: "monospace", fontSize: 13 };
