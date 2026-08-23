import React, { useState } from "react";
import ExcelSolverDemo from "../excel_solver_demo.jsx";
import NetworkFlowDemo from "../network_flow_demo.jsx";

const DEMOS = {
  excel: {
    label: "Excel Solver",
    Component: ExcelSolverDemo,
  },
  network: {
    label: "Aliran jaringan",
    Component: NetworkFlowDemo,
  },
};

export default function App() {
  const [selected, setSelected] = useState("excel");
  const Demo = DEMOS[selected].Component;

  return (
    <>
      <a href="#demo" style={skipLink}>Langsung ke demonstrasi</a>
      <header style={header}>
        <div>
          <strong>Visualisasi Buku 1</strong>
          <div style={subtitle}>Edisi Bahasa Indonesia</div>
        </div>
        <nav aria-label="Pilih demonstrasi" style={navigation}>
          {Object.entries(DEMOS).map(([key, item]) => (
            <button
              key={key}
              type="button"
              aria-pressed={selected === key}
              onClick={() => setSelected(key)}
              style={selected === key ? activeButton : button}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>
      <main id="demo" tabIndex="-1">
        <Demo />
      </main>
    </>
  );
}

const header = {
  alignItems: "center",
  background: "#12372a",
  color: "white",
  display: "flex",
  flexWrap: "wrap",
  gap: 16,
  justifyContent: "space-between",
  padding: "14px 24px",
};
const subtitle = { fontSize: 13, opacity: 0.85 };
const navigation = { display: "flex", flexWrap: "wrap", gap: 8 };
const button = {
  background: "white",
  border: "1px solid #d9e3dc",
  borderRadius: 6,
  color: "#12372a",
  cursor: "pointer",
  padding: "8px 12px",
};
const activeButton = { ...button, background: "#d8efe2", fontWeight: 700 };
const skipLink = {
  background: "white",
  left: 8,
  padding: 8,
  position: "absolute",
  top: -80,
  zIndex: 10,
};
