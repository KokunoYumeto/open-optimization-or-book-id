import fs from "node:fs/promises";
import path from "node:path";
import { Workbook } from "@oai/artifact-tool";

const laneRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:[A-Za-z]:)/, (m) => m.slice(1))), "..");
const csvDir = path.join(laneRoot, "backend", "dist", "csv");
const names = (await fs.readdir(csvDir)).filter((name) => name.endsWith(".csv")).sort();
const results = [];

for (const name of names) {
  const text = await fs.readFile(path.join(csvDir, name), "utf8");
  const workbook = await Workbook.fromCSV(text, { sheetName: "Data" });
  const sheet = workbook.worksheets.getItem("Data");
  const used = sheet.getUsedRange(true);
  const values = used?.values ?? [];
  const width = values.length ? values[0].length : 0;
  if (!values.length || !width) throw new Error(`${name}: empty imported range`);
  for (let row = 0; row < values.length; row += 1) {
    if (values[row].length !== width) throw new Error(`${name}: ragged row ${row + 1}`);
  }
  const inspection = await workbook.inspect({
    kind: "table",
    sheetId: "Data",
    range: `A1:${columnName(Math.min(width, 8))}${Math.min(values.length, 4)}`,
    tableMaxRows: 4,
    tableMaxCols: 8,
    tableMaxCellChars: 60,
    maxChars: 1800,
  });
  results.push({ name, rows: values.length - 1, columns: width, inspect_ok: Boolean(inspection?.ndjson) });
}

function columnName(number) {
  let value = number;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
}

console.log(JSON.stringify({ csv_files: results.length, results }, null, 2));
