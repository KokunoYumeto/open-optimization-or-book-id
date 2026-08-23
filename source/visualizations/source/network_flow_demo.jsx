import React, { useState } from "react";
import { Terminal } from "lucide-react";
import { Tex } from "./math.jsx";

/* ============================================================
   MASALAH ALIRAN JARINGAN
   ISE 5406

   Tiga masalah optimisasi graf klasik pada sebuah graf berarah kecil
   (8 simpul, 14 busur):
       • LINTASAN TERPENDEK (s → t)
       • ALIRAN MAKSIMUM    (s → t)
       • ALIRAN BIAYA MINIMUM (pasokan di s, kebutuhan di t)

   Untuk setiap masalah, graf YANG SAMA diberi atribut numerik yang
   relevan (bobot / kapasitas / biaya), lalu aliran atau lintasan
   hasilnya ditumpangkan dengan warna. Panel kode membandingkan
   NetworkX dan OR-Tools secara berdampingan.
   ============================================================ */

// ============================================================
// Graf (posisi + busur)
// ============================================================
const NODES = {
  s: { x: 60, y: 220, label: "s" },
  a: { x: 180, y: 100, label: "a" },
  b: { x: 180, y: 220, label: "b" },
  c: { x: 180, y: 340, label: "c" },
  d: { x: 320, y: 100, label: "d" },
  e: { x: 320, y: 220, label: "e" },
  f: { x: 320, y: 340, label: "f" },
  t: { x: 440, y: 220, label: "t" },
};

// Setiap busur memiliki bobot (untuk lintasan terpendek), kapasitas
// (untuk aliran maksimum), serta kapasitas dan biaya (untuk aliran
// biaya minimum).
const ARCS = [
  { u: "s", v: "a", w: 4, cap: 8, cost: 4 },
  { u: "s", v: "b", w: 2, cap: 12, cost: 2 },
  { u: "s", v: "c", w: 5, cap: 10, cost: 5 },
  { u: "a", v: "d", w: 3, cap: 6, cost: 3 },
  { u: "a", v: "e", w: 2, cap: 4, cost: 2 },
  { u: "b", v: "a", w: 1, cap: 4, cost: 1 },
  { u: "b", v: "e", w: 4, cap: 8, cost: 4 },
  { u: "b", v: "f", w: 6, cap: 6, cost: 6 },
  { u: "c", v: "f", w: 3, cap: 10, cost: 3 },
  { u: "d", v: "t", w: 4, cap: 6, cost: 4 },
  { u: "d", v: "e", w: 1, cap: 3, cost: 1 },
  { u: "e", v: "t", w: 2, cap: 9, cost: 2 },
  { u: "e", v: "f", w: 1, cap: 2, cost: 1 },
  { u: "f", v: "t", w: 5, cap: 8, cost: 5 },
];

// Daftar busur mandiri untuk cuplikan Python. Urutan setiap tupel:
// (pangkal, ujung, bobot, kapasitas, biaya_satuan).
const PYTHON_ARCS = `ARCS = [
    ("s", "a", 4, 8, 4),
    ("s", "b", 2, 12, 2),
    ("s", "c", 5, 10, 5),
    ("a", "d", 3, 6, 3),
    ("a", "e", 2, 4, 2),
    ("b", "a", 1, 4, 1),
    ("b", "e", 4, 8, 4),
    ("b", "f", 6, 6, 6),
    ("c", "f", 3, 10, 3),
    ("d", "t", 4, 6, 4),
    ("d", "e", 1, 3, 1),
    ("e", "t", 2, 9, 2),
    ("e", "f", 1, 2, 1),
    ("f", "t", 5, 8, 5),
]`;

// ============================================================
// Solusi yang telah dihitung
// ============================================================
// Lintasan terpendek dari s ke t berdasarkan bobot busur:
// s -b(2)-> b -a(1)-> a -e(2)-> e -t(2)-> t = 7.
// Pembanding: s-a-e-t = 4+2+2 = 8; s-b-e-t = 2+4+2 = 8.
const SHORTEST_PATH = ["s", "b", "a", "e", "t"];
const SHORTEST_LEN = 7;

// Aliran maksimum s→t berdasarkan kapasitas. Ketiga busur menuju t
// dapat dijenuhkan: d→t=6, e→t=9, dan f→t=8, sehingga nilainya 23.
// Potongan S={s,a,b,c,d,e,f}, T={t} berkapasitas 6+9+8=23;
// aliran layak di bawah ini mencapai batas tersebut.
const MAX_FLOW = {
  value: 23,
  arcFlow: {
    "s->a": 8, "s->b": 7, "s->c": 8,
    "a->d": 6, "a->e": 2,
    "b->a": 0, "b->e": 7, "b->f": 0,
    "c->f": 8,
    "d->t": 6, "d->e": 0,
    "e->t": 9, "e->f": 0,
    "f->t": 8,
  },
};

// Aliran biaya minimum untuk mengirim 12 unit dari s ke t.
// Aliran layak ini bernilai 12 dan berbiaya minimum 101.
const MIN_COST_FLOW = {
  value: 12,
  totalCost: 101,
  arcFlow: {
    "s->a": 3, "s->b": 9, "s->c": 0,
    "a->d": 3, "a->e": 4,
    "b->a": 4, "b->e": 5, "b->f": 0,
    "c->f": 0,
    "d->t": 3, "d->e": 0,
    "e->t": 9, "e->f": 0,
    "f->t": 0,
  },
};

// ============================================================
// Blok kode
// ============================================================
const CODE = {
  shortest_nx: `import networkx as nx

G = nx.DiGraph()
G.add_weighted_edges_from([
    ("s","a",4), ("s","b",2), ("s","c",5),
    ("a","d",3), ("a","e",2),
    ("b","a",1), ("b","e",4), ("b","f",6),
    ("c","f",3),
    ("d","t",4), ("d","e",1),
    ("e","t",2), ("e","f",1),
    ("f","t",5),
])

# Algoritma Dijkstra
path = nx.shortest_path(G, "s", "t", weight="weight")
length = nx.shortest_path_length(G, "s", "t", weight="weight")
print(path, length)        # ['s', 'b', 'a', 'e', 't']  7

# Semua pasangan simpul:
predecessors, distances = nx.floyd_warshall_predecessor_and_distance(
    G, weight="weight"
)`,

  shortest_or: `# OR-Tools tidak menyediakan fungsi bantu tunggal untuk lintasan
# terpendek. Masalah ini dapat ditulis sebagai aliran biaya minimum:
# pasokan 1 di s, kebutuhan 1 di t, biaya = bobot, kapasitas = 1.
from ortools.graph.python import min_cost_flow

${PYTHON_ARCS}

smcf = min_cost_flow.SimpleMinCostFlow()
NODE = {"s": 0, "a": 1, "b": 2, "c": 3,
        "d": 4, "e": 5, "f": 6, "t": 7}

for u, v, w, _, _ in ARCS:
    smcf.add_arc_with_capacity_and_unit_cost(
        NODE[u], NODE[v], 1, w
    )

# OR-Tools: pasokan positif berarti aliran keluar bersih.
smcf.set_node_supply(NODE["s"], 1)
smcf.set_node_supply(NODE["t"], -1)

status = smcf.solve()
total_cost = smcf.optimal_cost()    # 7
# Telusuri busur beraliran 1 untuk mendapatkan kembali lintasannya.`,

  maxflow_nx: `import networkx as nx

${PYTHON_ARCS}

G = nx.DiGraph()
for u, v, _, cap, _ in ARCS:
    G.add_edge(u, v, capacity=cap)

flow_value, flow_dict = nx.maximum_flow(G, "s", "t")
print("aliran maksimum =", flow_value)       # 23
cut_value, partition = nx.minimum_cut(G, "s", "t")
print("potongan minimum =", cut_value)        # 23
print("sisi S =", partition[0])               # {s,a,b,c,d,e,f}

# Pilihan algoritma jalur penambah:
nx.maximum_flow(
    G, "s", "t",
    flow_func=nx.algorithms.flow.edmonds_karp,
)
nx.maximum_flow(
    G, "s", "t",
    flow_func=nx.algorithms.flow.preflow_push,
)
nx.maximum_flow(
    G, "s", "t",
    flow_func=nx.algorithms.flow.dinitz,
)`,

  maxflow_or: `from ortools.graph.python import max_flow

${PYTHON_ARCS}

mf = max_flow.SimpleMaxFlow()
NODE = {"s": 0, "a": 1, "b": 2, "c": 3,
        "d": 4, "e": 5, "f": 6, "t": 7}

for u, v, _, cap, _ in ARCS:
    mf.add_arc_with_capacity(NODE[u], NODE[v], cap)

status = mf.solve(NODE["s"], NODE["t"])
print("aliran maksimum =", mf.optimal_flow())   # 23

# Potongan minimum: partisi pada sisi simpul sumber.
src_side = mf.get_source_side_min_cut()
print("sisi S =", [
    k for k, v in NODE.items() if v in src_side
])`,

  mincost_nx: `import networkx as nx

${PYTHON_ARCS}

G = nx.DiGraph()
for u, v, _, cap, cost in ARCS:
    G.add_edge(u, v, capacity=cap, weight=cost)

# NetworkX memakai kebutuhan bersih:
# positif = aliran masuk dikurangi aliran keluar.
G.nodes["s"]["demand"] = -12
G.nodes["t"]["demand"] = 12

flow_cost, flow_dict = nx.network_simplex(G)
print("biaya total =", flow_cost)     # 101
print(flow_dict["s"])                 # aliran keluar dari s

# Bentuk fungsi bantu yang setara:
flow = nx.min_cost_flow(G)
cost = nx.cost_of_flow(G, flow)       # 101`,

  mincost_or: `from ortools.graph.python import min_cost_flow

${PYTHON_ARCS}

smcf = min_cost_flow.SimpleMinCostFlow()
NODE = {"s": 0, "a": 1, "b": 2, "c": 3,
        "d": 4, "e": 5, "f": 6, "t": 7}

for u, v, _, cap, cost in ARCS:
    smcf.add_arc_with_capacity_and_unit_cost(
        NODE[u], NODE[v], cap, cost
    )

# OR-Tools memakai pasokan bersih:
# positif = aliran keluar dikurangi aliran masuk.
smcf.set_node_supply(NODE["s"], 12)
smcf.set_node_supply(NODE["t"], -12)

status = smcf.solve()
print("biaya total =", smcf.optimal_cost())   # 101
for i in range(smcf.num_arcs()):
    if smcf.flow(i) > 0:
        print(
            f"  {smcf.tail(i)} -> {smcf.head(i)}: "
            f"aliran={smcf.flow(i)}"
        )`,
};

// ============================================================
// Komponen utama
// ============================================================
export default function NetworkFlowDemo() {
  const [problem, setProblem] = useState("shortest");
  const [lib, setLib] = useState("nx");
  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 24px 80px" }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>
        Aliran Jaringan — NetworkX &amp; OR-Tools
      </h1>
      <p style={{ color: "#666", marginBottom: 18, maxWidth: 880 }}>
        Satu graf, tiga masalah klasik, dan dua pustaka. Pilih masalah untuk
        melihat graf yang sama dengan atribut yang relevan serta solusi yang
        diberi warna. Pilih pustaka untuk membandingkan NetworkX, pustaka graf
        Python serbaguna, dengan OR-Tools, kumpulan pemecah khusus Google
        berbasis C++ yang menyediakan antarmuka Python.
      </p>

      <div style={{ marginBottom: 12, display: "flex", gap: 14, flexWrap: "wrap" }}>
        {[
          ["shortest", "Lintasan terpendek", "#0b3da0"],
          ["maxflow", "Aliran maksimum", "#c8311c"],
          ["mincost", "Aliran biaya minimum", "#1f4e3d"],
        ].map(([k, label, color]) => (
          <button
            key={k}
            onClick={() => setProblem(k)}
            aria-pressed={problem === k}
            style={{
              padding: "8px 14px",
              border: "1px solid #ccc",
              borderRadius: 6,
              cursor: "pointer",
              background: problem === k ? color : "#fff",
              color: problem === k ? "#fff" : "#222",
              fontWeight: problem === k ? 700 : 500,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div style={problemBox}>
        {problem === "shortest" && (
          <>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
              Lintasan s–t terpendek
            </div>
            <div style={wordsStyle}>
              <b>Dengan kata-kata:</b> Anda berada di simpul <i>s</i> dan ingin
              mencapai simpul <i>t</i>. Setiap busur adalah jalan satu arah;
              angkanya menyatakan waktu, jarak, atau biaya untuk melintasinya.
              Carilah rute dari <i>s</i> ke <i>t</i> dengan jumlah terkecil.
              LP di bawah menyandikan sebuah rute dengan mengirim satu unit
              aliran dari <i>s</i> ke <i>t</i>: konservasi memaksa unit itu
              bergerak melalui lintasan yang tersambung, sedangkan minimisasi
              bobot total memilih lintasan termurah.
            </div>
            <Tex block>
              {String.raw`\min\;\; \sum_{(u,v) \in E} w_{uv}\, x_{uv} \;\; \text{dengan syarat}\;\; \sum_{v} x_{sv} - \sum_{v} x_{vs} = 1,\;\; \sum_{v} x_{tv} - \sum_{v} x_{vt} = -1,\;\; \sum_{v} x_{vu} = \sum_{v} x_{uv}\;\forall u \notin \{s,t\}, \;\; x_{uv} \ge 0`}
            </Tex>
          </>
        )}
        {problem === "maxflow" && (
          <>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
              Aliran s–t maksimum
            </div>
            <div style={wordsStyle}>
              <b>Dengan kata-kata:</b> sekarang busur-busurnya adalah pipa, dan
              setiap angka menyatakan kapasitas: jumlah maksimum yang dapat
              melewati pipa per jam. Air masuk di <i>s</i> dan keluar di{" "}
              <i>t</i>; pada setiap simpul lain, semua yang masuk harus keluar.
              Berapa jumlah total yang dapat dialirkan dari <i>s</i> ke{" "}
              <i>t</i>? Jawabannya dibatasi oleh leher botol berupa potongan
              minimum, yaitu himpunan busur yang jika dihapus memutus{" "}
              <i>s</i> dari <i>t</i>.
            </div>
            <Tex block>
              {String.raw`\max\;\; \sum_{v} x_{sv} \;\; \text{dengan syarat}\;\; \sum_{v} x_{vu} = \sum_{v} x_{uv}\;\forall u \notin \{s,t\},\;\; 0 \le x_{uv} \le c_{uv}`}
            </Tex>
            <div style={{ fontSize: 13, color: "#444", marginTop: 4 }}>
              Nilai aliran maksimum = kapasitas potongan minimum (teorema
              aliran-maksimum–potongan-minimum).
            </div>
          </>
        )}
        {problem === "mincost" && (
          <>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
              Aliran biaya minimum
            </div>
            <div style={wordsStyle}>
              <b>Dengan kata-kata:</b> masalah ini menggabungkan dua masalah
              sebelumnya. Anda harus mengirim 12 muatan truk dari gudang di{" "}
              <i>s</i> kepada pelanggan di <i>t</i>. Setiap busur memiliki
              kapasitas dan biaya per truk. Rutekan seluruh 12 muatan dengan
              biaya sekecil mungkin; solusi terbaik biasanya membagi kiriman
              ke beberapa rute. Lintasan terpendek dan aliran maksimum
              merupakan kasus khusus masalah ini.
            </div>
            <Tex block>
              {String.raw`\min\;\; \sum_{(u,v)} c_{uv}\, x_{uv} \;\; \text{dengan syarat}\;\; \sum_{v} x_{vu} - \sum_{v} x_{uv} = d_u\;\forall u,\;\; 0 \le x_{uv} \le \operatorname{cap}_{uv}`}
            </Tex>
            <div style={{ fontSize: 13, color: "#444", marginTop: 4 }}>
              Kirim 12 unit dari <i>s</i> ke <i>t</i> dengan biaya minimum.
              Pada rumus di atas dan dalam NetworkX, <Tex>{String.raw`d_u`}</Tex>{" "}
              adalah kebutuhan bersih (masuk dikurangi keluar), sehingga{" "}
              <Tex>{String.raw`d_s=-12`}</Tex> dan{" "}
              <Tex>{String.raw`d_t=+12`}</Tex>. OR-Tools memakai pasokan bersih
              dengan tanda berlawanan: +12 di <i>s</i> dan −12 di <i>t</i>.
            </div>
          </>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(440px, 1fr) minmax(420px, 1fr)",
          gap: 22,
          alignItems: "flex-start",
        }}
      >
        <GraphViz problem={problem} />
        <div>
          <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f6f4ee", border: "1px solid #ece8dd", borderRadius: 6, fontSize: 13 }}>
            Pustaka:&nbsp;
            <label style={{ marginRight: 12 }}>
              <input type="radio" checked={lib === "nx"} onChange={() => setLib("nx")} />
              &nbsp;NetworkX
            </label>
            <label>
              <input type="radio" checked={lib === "or"} onChange={() => setLib("or")} />
              &nbsp;OR-Tools
            </label>
          </div>
          <CodeBlock
            code={
              problem === "shortest"
                ? lib === "nx" ? CODE.shortest_nx : CODE.shortest_or
                : problem === "maxflow"
                ? lib === "nx" ? CODE.maxflow_nx : CODE.maxflow_or
                : lib === "nx" ? CODE.mincost_nx : CODE.mincost_or
            }
          />
          <ResultPanel problem={problem} />
        </div>
      </div>

      <ApplicationsPanel />
      <ComparisonTable />
      <PedagogicalNotes />
    </div>
  );
}

// ============================================================
// SVG graf
// ============================================================
function GraphViz({ problem }) {
  const W = 520, H = 460;
  const graphTitle =
    problem === "shortest"
      ? "Graf lintasan terpendek"
      : problem === "maxflow"
      ? "Graf aliran maksimum"
      : "Graf aliran biaya minimum";
  const graphDescription =
    problem === "shortest"
      ? "Graf berarah dengan bobot pada setiap busur; lintasan s ke t berbobot tujuh diberi warna biru."
      : problem === "maxflow"
      ? "Graf berarah berlabel aliran per kapasitas; aliran maksimum bernilai dua puluh tiga diberi warna."
      : "Graf berarah berlabel aliran per kapasitas dan biaya satuan; aliran dua belas unit berbiaya seratus satu diberi warna.";

  return (
    <div style={panel}>
      <svg
        width={W}
        height={H}
        role="img"
        aria-labelledby={`network-flow-title-${problem} network-flow-desc-${problem}`}
      >
        <title id={`network-flow-title-${problem}`}>{graphTitle}</title>
        <desc id={`network-flow-desc-${problem}`}>{graphDescription}</desc>

        {/* busur */}
        {ARCS.map((a, i) => {
          const u = NODES[a.u], v = NODES[a.v];
          const key = `${a.u}->${a.v}`;
          let highlight = false, label = "";
          let strokeColor = "#888", strokeW = 1.5;

          if (problem === "shortest") {
            // Tandai busur yang muncul berurutan dalam SHORTEST_PATH.
            for (let k = 0; k < SHORTEST_PATH.length - 1; k++) {
              if (SHORTEST_PATH[k] === a.u && SHORTEST_PATH[k + 1] === a.v) {
                highlight = true;
                break;
              }
            }
            label = `${a.w}`;
            strokeColor = highlight ? "#0b3da0" : "#aaa";
            strokeW = highlight ? 4 : 1.5;
          } else if (problem === "maxflow") {
            const f = MAX_FLOW.arcFlow[key] || 0;
            highlight = f > 0;
            label = `${f}/${a.cap}`;
            strokeColor = f === a.cap ? "#c8311c" : f > 0 ? "#7a3da0" : "#aaa";
            strokeW = f > 0 ? 1 + Math.min(5, f * 0.5) : 1.5;
          } else {
            const f = MIN_COST_FLOW.arcFlow[key] || 0;
            highlight = f > 0;
            label = `${f}/${a.cap} @${a.cost}`;
            strokeColor = f > 0 ? "#1f4e3d" : "#aaa";
            strokeW = f > 0 ? 1 + Math.min(5, f * 0.5) : 1.5;
          }

          // Hitung ujung panah tepat sebelum lingkaran simpul.
          const r = 22;
          const dx = v.x - u.x, dy = v.y - u.y;
          const len = Math.hypot(dx, dy);
          const ux = dx / len, uy = dy / len;
          const x1 = u.x + ux * r;
          const y1 = u.y + uy * r;
          const x2 = v.x - ux * r;
          const y2 = v.y - uy * r;
          // Letakkan label di titik tengah, sedikit bergeser tegak lurus.
          const mx = (x1 + x2) / 2;
          const my = (y1 + y2) / 2;
          const px = -uy, py = ux;
          const labelX = mx + px * 12;
          const labelY = my + py * 12;
          // Kepala panah.
          const ahSize = 9;
          const ax = -ux, ay = -uy;
          const axe1 = x2 + ax * ahSize - uy * (ahSize * 0.6);
          const aye1 = y2 + ay * ahSize + ux * (ahSize * 0.6);
          const axe2 = x2 + ax * ahSize + uy * (ahSize * 0.6);
          const aye2 = y2 + ay * ahSize - ux * (ahSize * 0.6);

          return (
            <g key={i}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={strokeColor} strokeWidth={strokeW} />
              <polygon points={`${x2},${y2} ${axe1},${aye1} ${axe2},${aye2}`} fill={strokeColor} />
              <rect
                x={labelX - 18}
                y={labelY - 9}
                width={36}
                height={18}
                fill="rgba(255,255,255,0.92)"
                stroke="rgba(0,0,0,0.06)"
                rx={3}
              />
              <text
                x={labelX}
                y={labelY + 4}
                textAnchor="middle"
                fontSize={10}
                fontFamily="monospace"
                fill={highlight ? "#222" : "#666"}
                fontWeight={highlight ? 700 : 400}
              >
                {label}
              </text>
            </g>
          );
        })}

        {/* simpul */}
        {Object.entries(NODES).map(([id, n]) => {
          const isTerm = id === "s" || id === "t";
          return (
            <g key={id}>
              <circle
                cx={n.x}
                cy={n.y}
                r={22}
                fill={isTerm ? "#c8311c" : "#1f4e3d"}
                stroke="#fff"
                strokeWidth={2.5}
              />
              <text
                x={n.x}
                y={n.y + 5}
                textAnchor="middle"
                fontSize={16}
                fontFamily="monospace"
                fontWeight={700}
                fill="#fff"
              >
                {n.label}
              </text>
            </g>
          );
        })}

        {/* legenda */}
        <g transform={`translate(10, ${H - 100})`}>
          <rect x={0} y={0} width={205} height={92} fill="rgba(255,255,255,0.92)" stroke="#ccc" />
          <text x={6} y={14} fontSize={11} fontWeight={700}>
            Label busur
          </text>
          {problem === "shortest" && (
            <text x={6} y={32} fontSize={11} fill="#444">bobot w</text>
          )}
          {problem === "maxflow" && (
            <>
              <text x={6} y={32} fontSize={11} fill="#444">aliran / kapasitas</text>
              <text x={6} y={50} fontSize={11} fill="#c8311c">merah = jenuh</text>
            </>
          )}
          {problem === "mincost" && (
            <>
              <text x={6} y={32} fontSize={11} fill="#444">aliran / kap. @ biaya satuan</text>
              <text x={6} y={50} fontSize={11} fill="#1f4e3d">hijau = busur aktif</text>
            </>
          )}
          <text x={6} y={70} fontSize={11} fill="#666">garis tebal = aliran tak nol</text>
          <circle cx={14} cy={86} r={6} fill="#c8311c" />
          <text x={26} y={90} fontSize={11}>simpul sumber/tujuan</text>
        </g>
      </svg>
    </div>
  );
}

// ============================================================
// Panel hasil
// ============================================================
function ResultPanel({ problem }) {
  return (
    <div style={{ ...panel, marginTop: 14 }}>
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: "#888",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        Hasil
      </div>
      {problem === "shortest" && (
        <table aria-label="Hasil lintasan terpendek" style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}>
          <tbody>
            <KV k="lintasan" v={SHORTEST_PATH.join(" → ")} />
            <KV k="bobot total" v={SHORTEST_LEN} highlight />
            <KV k="algoritma" v="Dijkstra (NetworkX) / simpleks jaringan (OR-Tools)" />
          </tbody>
        </table>
      )}
      {problem === "maxflow" && (
        <table aria-label="Hasil aliran maksimum" style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}>
          <tbody>
            <KV k="nilai aliran maksimum" v={MAX_FLOW.value} highlight />
            <KV k="potongan minimum" v="{s, a, b, c, d, e, f} | {t}" />
            <KV k="algoritma" v="preflow-push (bawaan NetworkX) / push-relabel (OR-Tools)" />
          </tbody>
        </table>
      )}
      {problem === "mincost" && (
        <table aria-label="Hasil aliran biaya minimum" style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}>
          <tbody>
            <KV k="aliran terkirim" v={MIN_COST_FLOW.value} />
            <KV k="biaya total" v={MIN_COST_FLOW.totalCost} highlight />
            <KV k="algoritma" v="simpleks jaringan (NetworkX) / SSP (OR-Tools)" />
          </tbody>
        </table>
      )}
    </div>
  );
}

function KV({ k, v, highlight }) {
  return (
    <tr style={{ borderBottom: "1px dotted #eee" }}>
      <td style={{ padding: "3px 6px", color: "#666" }}>{k}</td>
      <td style={{ padding: "3px 6px", color: highlight ? "#c8311c" : "#222", fontWeight: highlight ? 700 : 400, textAlign: "right" }}>{v}</td>
    </tr>
  );
}

// ============================================================
// Tabel perbandingan
// ============================================================
function ComparisonTable() {
  return (
    <div style={{ ...panel, marginTop: 18 }}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>
        Kapan sebaiknya memakai masing-masing pustaka?
      </div>
      <table aria-label="Perbandingan NetworkX dan OR-Tools" style={{ width: "100%", fontFamily: "monospace", fontSize: 12, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#f0f0f0" }}>
            <th style={th}>aspek</th>
            <th style={th}>NetworkX</th>
            <th style={th}>OR-Tools</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["skala umum", "10² – 10⁵ simpul", "10³ – 10⁸ simpul"],
            ["bahasa", "Python murni", "inti C++, antarmuka Python"],
            ["dependensi", "pip install networkx", "pip install ortools"],
            ["penyuntingan graf", "mudah — akses penuh melalui kamus G[u][v]", "pemecah harus dibangun ulang setelah perubahan"],
            ["algoritma", "banyak: Dijkstra, Bellman–Ford, A*, Edmonds–Karp, Dinic, preflow-push, network-simplex, MCMF, Hungarian, …", "satu pemecah per kategori: SimpleMaxFlow, SimpleMinCostFlow, LinearSumAssignment"],
            ["kecepatan", "sangat baik untuk pembuatan prototipe", "10×–100× lebih cepat pada graf besar"],
            ["penggunaan terbaik", "riset, kueri graf ad hoc, pendidikan", "kode produksi, instans yang sangat besar"],
          ].map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px dotted #eee" }}>
              {row.map((cell, j) => (
                <td key={j} style={{ padding: 6, fontWeight: j === 0 ? 700 : 400 }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
const th = { padding: 6, textAlign: "left", borderBottom: "1px solid #ccc" };

// ============================================================
// Blok kode
// ============================================================
function CodeBlock({ code }) {
  return (
    <pre
      aria-label="Contoh kode Python"
      style={{
        background: "#1f1d1a",
        color: "#e8e2d4",
        padding: 14,
        borderRadius: 8,
        fontSize: 12,
        fontFamily: "'JetBrains Mono', Menlo, monospace",
        lineHeight: 1.55,
        whiteSpace: "pre",
        overflowX: "auto",
        margin: 0,
        maxHeight: 520,
        overflowY: "auto",
      }}
    >
      {code}
    </pre>
  );
}

// ============================================================
// Catatan pedagogis
// ============================================================
function PedagogicalNotes() {
  return (
    <div style={{ marginTop: 28, padding: 16, background: "#fff8e1", borderRadius: 10, border: "1px solid #f5d68d" }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>
        <Terminal size={14} aria-hidden="true" style={{ verticalAlign: "middle", marginRight: 6 }} />
        Catatan untuk kelas
      </div>
      <ul style={{ margin: 0, paddingLeft: 22, lineHeight: 1.6, fontSize: 14, color: "#3d2f00" }}>
        <li>
          <b>Masalah jaringan adalah LP yang tersamar.</b> Matriks kendalanya
          adalah matriks insidensi simpul–busur dan bersifat{" "}
          <i>totally unimodular</i>. Karena itu, jika kapasitas dan neraca
          simpul semuanya bilangan bulat, polihedron aliran memiliki titik
          ekstrem bilangan bulat dan terdapat solusi optimum bilangan bulat.
          Tanpa data ruas kanan yang bulat, kesimpulan keintegralan itu tidak
          berlaku.
        </li>
        <li>
          <b>Aliran maksimum–potongan minimum.</b> Nilai aliran maksimum sama
          dengan kapasitas potongan minimum, yakni himpunan busur yang
          penghapusannya memutus <i>s</i> dari <i>t</i>. Ini adalah contoh
          utama dualitas LP; harga bayangan pada kendala konservasi berkaitan
          dengan variabel potongan.
        </li>
        <li>
          <b>Simpleks jaringan.</b> Ini adalah metode simpleks khusus untuk
          masalah aliran, dengan basis yang direpresentasikan oleh pohon
          rentang. Struktur tersebut memungkinkan implementasi yang jauh lebih
          efisien daripada simpleks LP umum pada banyak instans jaringan.
          NetworkX menyediakan implementasi Python, sedangkan OR-Tools
          menyediakan pemecah C++ melalui antarmuka Python.
        </li>
        <li>
          <b>Melampaui graf mainan.</b> Penerapannya mencakup penjadwalan awak
          maskapai, perutean angkutan, protokol perutean internet (OSPF),
          pencocokan bipartit untuk penempatan iklan, penjemputan dan
          pengantaran dalam rantai pasok, segmentasi citra melalui aliran
          maksimum, serta inferensi jaringan regulasi gen.
        </li>
        <li>
          <b>Yang memerlukan model lebih umum.</b> Rutinitas aliran komoditas
          tunggal yang ditampilkan di sini tidak langsung memodelkan beberapa
          pasangan sumber–tujuan yang berbagi kapasitas. Aliran multikomoditas
          perlu dirumuskan sebagai LP atau MIP umum, misalnya dengan Pyomo dan
          pemecah LP/MIP terbuka seperti HiGHS. Fungsi aliran biaya minimum
          NetworkX tetap merupakan model satu komoditas.
        </li>
      </ul>
    </div>
  );
}

// ============================================================
// Atom gaya
// ============================================================
const panel = {
  background: "#fafafa",
  border: "1px solid #ddd",
  borderRadius: 8,
  padding: 12,
};
const problemBox = {
  marginBottom: 16,
  padding: "12px 16px",
  background: "#f6f4ee",
  border: "1px solid #ece8dd",
  borderRadius: 8,
};

const wordsStyle = {
  fontSize: 13.5,
  color: "#333",
  lineHeight: 1.55,
  maxWidth: 860,
  margin: "2px 0 10px",
};

// ============================================================
// Penerapan
// ============================================================
const APPLICATIONS = [
  {
    title: "Lintasan terpendek",
    color: "#0b3da0",
    items: [
      "GPS dan peta: rute tercepat antara dua alamat pada jaringan jalan.",
      "Perutean internet: paket mengikuti lintasan berbiaya terendah yang dipilih protokol perutean.",
      "Rencana perjalanan maskapai dan angkutan umum: waktu atau biaya terkecil dari satu kota ke kota lain.",
      "Penggantian peralatan: simpul menyatakan tahun, busur menyatakan 'pertahankan sampai tahun j lalu ganti', dan lintasan terpendek memberikan jadwal penggantian termurah.",
    ],
  },
  {
    title: "Aliran maksimum",
    color: "#c8311c",
    items: [
      "Kapasitas pipa dan jaringan listrik: banyaknya minyak, gas, atau listrik yang dapat disalurkan jaringan.",
      "Perencanaan evakuasi: jumlah orang per jam yang dapat keluar dari gedung atau wilayah, serta pintu keluar yang menjadi leher botol.",
      "Penugasan pekerja ke pekerjaan: pencocokan bipartit dapat dirumuskan sebagai masalah aliran maksimum.",
      "Segmentasi citra: pemisahan citra menjadi latar depan dan latar belakang merupakan potongan minimum, dual aliran maksimum.",
    ],
  },
  {
    title: "Aliran biaya minimum",
    color: "#1f4e3d",
    items: [
      "Logistik dan rantai pasok: mengirim barang dari pabrik melalui gudang kepada pelanggan dengan biaya terendah, seperti model transportasi dan transshipment dalam bab pemodelan buku ini.",
      "Penugasan armada maskapai: merutekan pesawat dalam jaringan ruang–waktu agar seluruh penerbangan tercakup dengan murah.",
      "Pengelolaan kas: memindahkan dana antar rekening dan periode waktu dengan batas serta biaya transaksi.",
      "Penjadwalan pekerjaan pada mesin dengan biaya peralihan.",
    ],
  },
];

function ApplicationsPanel() {
  return (
    <div style={{ marginTop: 26 }}>
      <h2 style={{ fontSize: 19, fontWeight: 700, marginBottom: 10 }}>
        Di mana masalah-masalah ini muncul?
      </h2>
      <p style={{ fontSize: 13.5, color: "#444", maxWidth: 860, marginBottom: 12 }}>
        Model aliran jaringan termasuk kelas program linear yang paling banyak
        digunakan dalam praktik. Matriks kendalanya sangat terstruktur sehingga
        algoritma khusus seperti simpleks jaringan dapat menyelesaikan instans
        besar dengan cepat. Selain itu, jika kapasitas dan kebutuhan berupa
        bilangan bulat, terdapat aliran optimum bilangan bulat tanpa harus
        memakai pemrograman bilangan bulat.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 14,
        }}
      >
        {APPLICATIONS.map((a) => (
          <div
            key={a.title}
            style={{
              border: "1px solid #ddd",
              borderTop: `3px solid ${a.color}`,
              borderRadius: 8,
              padding: "12px 14px",
              background: "#fff",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6, color: a.color }}>
              {a.title}
            </div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#333", lineHeight: 1.5 }}>
              {a.items.map((it, i) => (
                <li key={i} style={{ marginBottom: 5 }}>{it}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
