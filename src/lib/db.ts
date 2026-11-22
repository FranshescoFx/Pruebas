import "server-only";
import path from "node:path";
import type { Entidad, Oferta, Producto, Promocion } from "./types";

type Row = Record<string, any>;
let _db: any;
function db() {
  if (!_db) {
    // node:sqlite es nativo de Node ≥22.5; se carga así para que el bundler no lo intente resolver.
    const sqlite = (process as any).getBuiltinModule("node:sqlite");
    _db = new sqlite.DatabaseSync(path.join(process.cwd(), "data", "app.db"), { readOnly: true });
  }
  return _db;
}
const all = (sql: string, ...p: any[]): Row[] => db().prepare(sql).all(...p);

export function getMeta(): { periodo: string; fuente: string; generado: string } {
  const m = Object.fromEntries(all("SELECT k,v FROM meta").map((r) => [r.k, r.v]));
  return { periodo: m.ssf_periodo, fuente: m.ssf_fuente, generado: m.generado };
}
export const getEntidades = (): Entidad[] => all("SELECT * FROM entidades") as Entidad[];

export function getOfertas(producto: Producto): Oferta[] {
  const rows = all(
    `SELECT o.*, e.nombre AS entidad, e.tipo AS tipo_entidad, e.web FROM ofertas o JOIN entidades e ON e.id=o.entidad_id WHERE o.producto=?`,
    producto
  );
  const today = new Date().toISOString().slice(0, 10);
  const promoCount = Object.fromEntries(
    all(`SELECT entidad_id, COUNT(*) c FROM promociones WHERE exclusiva_tarjeta=1 AND (hasta IS NULL OR hasta>=?) GROUP BY entidad_id`, today).map((r) => [r.entidad_id, r.c])
  );
  return rows.map((r) => {
    const x = r.extra ? JSON.parse(r.extra) : {};
    const o: Oferta = {
      id: r.id, entidad_id: r.entidad_id, entidad: r.entidad, tipo_entidad: r.tipo_entidad, producto: r.producto, nombre: r.nombre,
      tasa_nominal: r.tasa_nominal, tasa_efectiva: r.tasa_efectiva, nominal_es_max: !!r.nominal_es_max, efectiva_es_max: !!r.efectiva_es_max,
      comision_texto: r.comision_texto, comision_pct_max: r.comision_pct_max, seguro_texto: r.seguro_texto, tiene_seguro: !!r.tiene_seguro,
      nota: r.nota, fuente_url: r.fuente_url, periodo: r.periodo, web: r.web,
      n_promos: promoCount[r.entidad_id] ?? 0,
    };
    if (producto === "tarjeta") {
      o.tiers = x.tiers; o.membresia_max = x.membresia_max; o.retiro_pct = x.retiro_pct;
      o.mora_texto = x.comisiones?.recargo_moratorio ?? null;
      o.tarjetas = all("SELECT * FROM tarjetas WHERE entidad_id=?", r.entidad_id).map((t) => ({
        nombre: t.nombre, red: t.red, nivel: t.nivel, categoria: t.categoria, beneficios: JSON.parse(t.beneficios), url: t.url,
      }));
    } else {
      o.productos = x.productos;
    }
    return o;
  });
}

export function getPromociones(): Promocion[] {
  return all(`SELECT p.*, e.nombre AS entidad FROM promociones p JOIN entidades e ON e.id=p.entidad_id ORDER BY p.hasta IS NULL, p.hasta`).map((r) => ({
    ...(r as any), tarjetas: JSON.parse(r.tarjetas), exclusiva_tarjeta: !!r.exclusiva_tarjeta,
  }));
}
