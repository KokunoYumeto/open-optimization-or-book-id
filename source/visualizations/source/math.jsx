import React from "react";
import katex from "katex";

/* Komponen KaTeX kecil untuk rumus sebaris dan rumus pajang. */
export function Tex({ children, block = false }) {
  const html = katex.renderToString(String(children ?? ""), {
    displayMode: block,
    throwOnError: false,
    errorColor: "#c8311c",
    strict: "ignore",
  });
  const Tag = block ? "div" : "span";
  return (
    <Tag
      style={block ? { margin: "8px 0", textAlign: "center" } : undefined}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
