// Construye data/app.db (SQLite) a partir de los JSON en data/.
// Uso: node scripts/seed.mjs
import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const D = (...p) => path.join(ROOT, "data", ...p);
const read = (f) => JSON.parse(fs.readFileSync(f, "utf8"));

const norm = (s) =>
  (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");

const entities = read(D("entities.json"));
const entityFor = (name) => {
  const n = norm(name);
  return entities.find((e) => e.ssf.some((p) => n.includes(p)))?.id ?? null;
};

// --- período SSF más reciente
const ssfFiles = fs.readdirSync(D("ssf")).filter((f) => /^\d{4}-\d{2}\.json$/.test(f)).sort();
if (!ssfFiles.length) throw new Error("No hay JSON de la SSF. Ejecuta: npm run ssf");
const ssf = read(D("ssf", ssfFiles.at(-1)));

const num = (s) => {
  const m = String(s ?? "").match(/(\d+(?:\.\d+)?)/);
  return m ? parseFloat(m[1]) : null;
};
const hasText = (s) => !!s && s.trim() !== "*" && s.trim() !== "";
const maxPct = (s, cap = 8) => {
  const all = [...String(s ?? "").matchAll(/(\d+(?:\.\d+)?)\s*%/g)].map((m) => parseFloat(m[1])).filter((v) => v <= cap);
  return all.length ? Math.max(...all) : null;
};
const byEntity = (obj) => {
  const out = {};
  for (const [name, v] of Object.entries(obj)) {
    const id = entityFor(name);
    if (id) out[id] = { ...(out[id] ?? {}), ...(Array.isArray(v) ? { _arr: [...(out[id]?._arr ?? []), ...v] } : v) };
  }
  return out;
};

const activas = byEntity(ssf.tasas_activas);
const tarjTasas = {};
for (const [name, rows] of Object.entries(ssf.tarjetas_tasas)) {
  const id = entityFor(name);
  if (!id) continue;
  const seen = new Set((tarjTasas[id] ??= []).map((r) => r.limite_min));
  for (const r of rows) if (!seen.has(r.limite_min)) tarjTasas[id].push(r);
}
const tarjCom = byEntity(ssf.tarjetas_comisiones);
const comCred = byEntity(ssf.comisiones_creditos);
const seguros = byEntity(ssf.seguros_recargos);
const cards = read(D("cards.json")).tarjetas;
const loanProducts = read(D("loan-products.json")).productos;
const promos = read(D("promotions.json")).promociones;

// --- DB
const dbPath = D("app.db");
for (const f of [dbPath, dbPath + "-wal", dbPath + "-shm"]) if (fs.existsSync(f)) fs.rmSync(f);
const db = new DatabaseSync(dbPath);
db.exec(`
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE entidades (id TEXT PRIMARY KEY, nombre TEXT, tipo TEXT, web TEXT, facebook TEXT, instagram TEXT);
CREATE TABLE ofertas (
  id TEXT PRIMARY KEY, entidad_id TEXT, producto TEXT, nombre TEXT,
  tasa_nominal REAL, tasa_efectiva REAL, nominal_es_max INTEGER, efectiva_es_max INTEGER,
  comision_texto TEXT, comision_pct_max REAL, seguro_texto TEXT, tiene_seguro INTEGER,
  nota TEXT, fuente_url TEXT, periodo TEXT, extra TEXT
);
CREATE TABLE tarjetas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, entidad_id TEXT, nombre TEXT, red TEXT, nivel TEXT,
  categoria TEXT, beneficios TEXT, url TEXT, verificado TEXT
);
CREATE TABLE productos_credito (
  id INTEGER PRIMARY KEY AUTOINCREMENT, entidad_id TEXT, categoria TEXT, nombre TEXT,
  descripcion TEXT, url TEXT, verificado TEXT
);
CREATE TABLE promociones (
  id TEXT PRIMARY KEY, entidad_id TEXT, titulo TEXT, descripcion TEXT, tarjetas TEXT, tipo TEXT,
  categoria TEXT, exclusiva_tarjeta INTEGER, canal TEXT, desde TEXT, hasta TEXT, url TEXT,
  confianza TEXT, verificado TEXT
);
`);

const put = (sql, ...a) => db.prepare(sql).run(...a);

put("INSERT INTO meta VALUES (?,?)", "ssf_periodo", ssf.periodo);
put("INSERT INTO meta VALUES (?,?)", "ssf_fuente", ssf.fuente);
put("INSERT INTO meta VALUES (?,?)", "generado", new Date().toISOString());

for (const e of entities) put("INSERT INTO entidades VALUES (?,?,?,?,?,?)", e.id, e.nombre, e.tipo, e.web, e.facebook, e.instagram);

const rate = (r) => (r && typeof r.v === "number" ? r : null);
const baseLoan = (id, key) => {
  const a = activas[id];
  return a?.[`${key} | Mas de 1 año plazo`] ?? a?.[`${key} | A 1 año plazo`] ?? null;
};

let n = 0;
const insertOffer = (o) =>
  put(
    "INSERT INTO ofertas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    o.id, o.entidad_id, o.producto, o.nombre, o.tasa_nominal, o.tasa_efectiva,
    o.nominal_es_max ? 1 : 0, o.efectiva_es_max ? 1 : 0, o.comision_texto, o.comision_pct_max,
    o.seguro_texto, o.tiene_seguro ? 1 : 0, o.nota, o.fuente_url, o.periodo, o.extra ? JSON.stringify(o.extra) : null
  );

const SSF_NOTE_CONSUMO =
  "La SSF publica una sola categoría 'Consumo' (incluye personal, consolidación y vehículo). La tasa mostrada es la de esa categoría; confirma la tasa final con el banco según tu perfil.";

for (const e of entities) {
  const id = e.id;
  const com = comCred[id]?.contratacion_otorgamiento ?? "";
  const seg = seguros[id] ?? {};
  const base = { entidad_id: id, periodo: ssf.periodo, fuente_url: ssf.fuente, comision_texto: hasText(com) ? com : null, comision_pct_max: maxPct(com) };

  // Vivienda
  const viv = baseLoan(id, "Créditos de Vivienda");
  if (viv && (rate(viv.efectiva) || rate(viv.nominal))) {
    insertOffer({ ...base, id: `${id}-vivienda`, producto: "vivienda", nombre: "Crédito de vivienda (más de 1 año plazo)",
      tasa_nominal: rate(viv.nominal)?.v ?? null, tasa_efectiva: rate(viv.efectiva)?.v ?? null,
      nominal_es_max: rate(viv.nominal)?.max, efectiva_es_max: rate(viv.efectiva)?.max,
      seguro_texto: [seg.seguro_danos_vehiculos, seg.seguro_vida].filter(hasText).join(" · ") || null,
      tiene_seguro: hasText(seg.seguro_danos_vehiculos) || hasText(seg.seguro_vida),
      nota: "Tasa de referencia para crédito de vivienda reportada a la SSF (adquisición, ampliación y lotes).", extra: null });
    n++;
  }

  // Consumo → personal / consolidación / vehículo
  const con = baseLoan(id, "Consumo");
  if (con && (rate(con.efectiva) || rate(con.nominal))) {
    const common = { ...base, tasa_nominal: rate(con.nominal)?.v ?? null, tasa_efectiva: rate(con.efectiva)?.v ?? null,
      nominal_es_max: rate(con.nominal)?.max, efectiva_es_max: rate(con.efectiva)?.max, nota: SSF_NOTE_CONSUMO };
    const prods = loanProducts.filter((p) => p.entidad === id);
    const pickName = (cat, dflt) => prods.filter((p) => p.categoria === cat).map((p) => p.nombre).join(" · ") || dflt;
    insertOffer({ ...common, id: `${id}-personal`, producto: "personal", nombre: pickName("personal", "Crédito de consumo / personal"),
      seguro_texto: hasText(seg.seguro_vida) ? seg.seguro_vida : null, tiene_seguro: hasText(seg.seguro_vida), extra: { productos: prods.filter((p) => p.categoria === "personal") } });
    insertOffer({ ...common, id: `${id}-consolidacion`, producto: "consolidacion", nombre: pickName("consolidacion", "Crédito de consumo (uso: consolidación de deudas)"),
      seguro_texto: hasText(seg.seguro_vida) ? seg.seguro_vida : null, tiene_seguro: hasText(seg.seguro_vida), extra: { productos: prods.filter((p) => p.categoria === "consolidacion") } });
    insertOffer({ ...common, id: `${id}-vehiculo`, producto: "vehiculo", nombre: pickName("vehiculo", "Crédito de consumo (uso: vehículo)"),
      seguro_texto: [seg.seguro_danos_vehiculos].filter(hasText).join(" · ") || null, tiene_seguro: hasText(seg.seguro_danos_vehiculos), extra: { productos: prods.filter((p) => p.categoria === "vehiculo") } });
    n += 3;
  }

  // Tarjetas
  const tiers = (tarjTasas[id] ?? [])
    .map((r) => ({ limite_min: r.limite_min, nominal: rate(r.nominal)?.v ?? null, efectiva: rate(r.efectiva)?.v ?? null }))
    .filter((r) => r.efectiva != null || r.nominal != null)
    // Descarta cifras imposibles en el reporte (p.ej. efectiva < nominal o < 8% en tarjetas): errores de transcripción de la fuente.
    .filter((r) => (r.efectiva ?? r.nominal) >= 8 && !(r.efectiva != null && r.nominal != null && r.efectiva < r.nominal - 0.01))
    .sort((a, b) => a.limite_min - b.limite_min);
  if (tiers.length) {
    const eff = tiers.map((t) => t.efectiva ?? t.nominal);
    const c = tarjCom[id] ?? {};
    insertOffer({ entidad_id: id, periodo: ssf.periodo, fuente_url: ssf.fuente, id: `${id}-tarjeta`, producto: "tarjeta",
      nombre: "Tarjetas de crédito",
      tasa_nominal: Math.min(...tiers.map((t) => t.nominal ?? t.efectiva)), tasa_efectiva: Math.min(...eff),
      nominal_es_max: false, efectiva_es_max: false,
      comision_texto: c.membresia_titular || null, comision_pct_max: null,
      seguro_texto: hasText(c.plan_seguro_robo_fraude) ? c.plan_seguro_robo_fraude : null, tiene_seguro: hasText(c.plan_seguro_robo_fraude),
      nota: "Tasas oficiales por rango de límite de crédito reportadas a la SSF. La tasa que te aplicará depende del límite aprobado.",
      extra: { tiers, tasa_max: Math.max(...eff), comisiones: c, membresia_max: hasText(c.membresia_titular) ? num(c.membresia_titular) : null, retiro_pct: maxPct(c.retiro_efectivo, 15) } });
    n++;
  }
}

for (const c of cards)
  put("INSERT INTO tarjetas (entidad_id,nombre,red,nivel,categoria,beneficios,url,verificado) VALUES (?,?,?,?,?,?,?,?)",
    c.entidad, c.nombre, c.red, c.nivel, c.categoria, JSON.stringify(c.beneficios), c.url, c.verificado);
for (const p of loanProducts)
  put("INSERT INTO productos_credito (entidad_id,categoria,nombre,descripcion,url,verificado) VALUES (?,?,?,?,?,?)",
    p.entidad, p.categoria, p.nombre, p.descripcion, p.url, p.verificado);
for (const p of promos)
  put("INSERT INTO promociones VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    p.id, p.entidad, p.titulo, p.descripcion, JSON.stringify(p.tarjetas ?? []), p.tipo, p.categoria,
    p.exclusiva_tarjeta ? 1 : 0, p.canal, p.desde, p.hasta, p.url, p.confianza, p.verificado);

db.close();
console.log(`app.db OK · período SSF ${ssf.periodo} · ${n} ofertas · ${cards.length} tarjetas · ${promos.length} promociones`);
