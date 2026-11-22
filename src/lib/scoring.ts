import type { Oferta, Producto, Tier } from "./types";

export type CriterioId = "tasa" | "comisiones" | "seguros" | "certeza" | "info" | "membresia" | "retiro" | "beneficios" | "promos";

export interface Criterio { id: CriterioId; label: string; ayuda: string }

export const CRITERIOS: Record<CriterioId, Criterio> = {
  tasa: { id: "tasa", label: "Tasa de interés efectiva (TEA)", ayuda: "Costo anual real del dinero según la SSF. Menor es mejor." },
  comisiones: { id: "comisiones", label: "Comisión de apertura / otorgamiento", ayuda: "Porcentaje máximo cobrado al contratar. Menor es mejor." },
  seguros: { id: "seguros", label: "Seguros adicionales", ayuda: "Si el banco reporta seguros cargados al crédito, puntúa menos." },
  certeza: { id: "certeza", label: "Certeza de la tasa", ayuda: "Tasa fija reportada vs. tasa 'hasta' (tope máximo, puede ser menor o igual)." },
  info: { id: "info", label: "Producto documentado", ayuda: "Hay productos concretos publicados por la entidad." },
  membresia: { id: "membresia", label: "Membresía anual (máx.)", ayuda: "Cuota anual máxima del titular. Menor es mejor." },
  retiro: { id: "retiro", label: "Comisión por retiro de efectivo", ayuda: "% sobre el monto retirado. Menor es mejor." },
  beneficios: { id: "beneficios", label: "Variedad de tarjetas y beneficios", ayuda: "Cantidad de tarjetas/beneficios documentados (millas, cashback, descuentos)." },
  promos: { id: "promos", label: "Promociones exclusivas vigentes", ayuda: "Ofertas activas para tarjetahabientes de la entidad." },
};

export const CRITERIOS_POR_PRODUCTO: Record<Producto, CriterioId[]> = {
  tarjeta: ["tasa", "membresia", "retiro", "beneficios", "promos"],
  personal: ["tasa", "comisiones", "seguros", "certeza", "info"],
  consolidacion: ["tasa", "comisiones", "seguros", "certeza", "info"],
  vehiculo: ["tasa", "comisiones", "seguros", "certeza", "info"],
  vivienda: ["tasa", "comisiones", "seguros", "certeza", "info"],
};

export const PESOS_DEFECTO: Record<Producto, Partial<Record<CriterioId, number>>> = {
  tarjeta: { tasa: 40, membresia: 20, retiro: 10, beneficios: 15, promos: 15 },
  personal: { tasa: 45, comisiones: 20, seguros: 10, certeza: 10, info: 15 },
  consolidacion: { tasa: 50, comisiones: 20, seguros: 10, certeza: 10, info: 10 },
  vehiculo: { tasa: 45, comisiones: 20, seguros: 10, certeza: 10, info: 15 },
  vivienda: { tasa: 50, comisiones: 20, seguros: 10, certeza: 10, info: 10 },
};

/** Tasa efectiva de una tarjeta para un límite de crédito dado (tramos oficiales SSF). null = el banco no reporta tarjetas para ese límite. */
export function tasaTarjeta(o: Oferta, limite: number): { efectiva: number | null; nominal: number | null; tier: Tier | null } {
  const tiers = (o.tiers ?? []).filter((t) => t.limite_min <= limite);
  if (!tiers.length) return { efectiva: null, nominal: null, tier: null };
  // El tramo aplicable es el de mayor límite mínimo que no exceda el límite pedido.
  const t = tiers.reduce((a, b) => (b.limite_min >= a.limite_min ? b : a));
  return { efectiva: t.efectiva ?? t.nominal, nominal: t.nominal, tier: t };
}

export function cuotaMensual(monto: number, tea: number, meses: number): number {
  const r = Math.pow(1 + tea / 100, 1 / 12) - 1;
  if (r === 0) return monto / meses;
  return (monto * r) / (1 - Math.pow(1 + r, -meses));
}

export interface Resultado {
  oferta: Oferta;
  tea: number | null;
  score: number;
  detalle: { id: CriterioId; puntos: number; peso: number; dato: string; faltante: boolean }[];
  cuota?: number;
  totalIntereses?: number;
}

interface Ctx { producto: Producto; pesos: Partial<Record<CriterioId, number>>; limite?: number; monto?: number; meses?: number }

const norm = (v: number, min: number, max: number, menorMejor = true) =>
  max === min ? 100 : Math.max(0, Math.min(100, (100 * (menorMejor ? max - v : v - min)) / (max - min)));

export function puntuar(ofertas: Oferta[], ctx: Ctx): Resultado[] {
  const ids = CRITERIOS_POR_PRODUCTO[ctx.producto];
  const esTarjeta = ctx.producto === "tarjeta";
  const base = ofertas
    .map((o) => ({ o, tea: esTarjeta ? tasaTarjeta(o, ctx.limite ?? 1500).efectiva : o.tasa_efectiva }))
    .filter((x) => !esTarjeta || x.tea != null);

  const range = (vals: (number | null | undefined)[]) => {
    const v = vals.filter((x): x is number => typeof x === "number");
    return v.length ? ([Math.min(...v), Math.max(...v)] as const) : ([0, 0] as const);
  };
  const [tMin, tMax] = range(base.map((x) => x.tea));
  const [cMin, cMax] = range(base.map((x) => x.o.comision_pct_max));
  const [mMin, mMax] = range(base.map((x) => x.o.membresia_max));
  const [rMin, rMax] = range(base.map((x) => x.o.retiro_pct));
  const [bMin, bMax] = range(base.map((x) => (x.o.tarjetas ?? []).length));
  const [pMin, pMax] = range(base.map((x) => x.o.n_promos));
  const totalPeso = ids.reduce((s, id) => s + (ctx.pesos[id] ?? 0), 0) || 1;

  const res = base.map(({ o, tea }): Resultado => {
    const det: Resultado["detalle"] = ids.map((id) => {
      const peso = ctx.pesos[id] ?? 0;
      let puntos = 50, dato = "Sin dato", faltante = true;
      switch (id) {
        case "tasa": if (tea != null) { puntos = norm(tea, tMin, tMax); dato = `${tea.toFixed(2)}%`; faltante = false; } break;
        case "comisiones":
          if (o.comision_pct_max != null) { puntos = norm(o.comision_pct_max, cMin, cMax); dato = `hasta ${o.comision_pct_max}%`; faltante = false; }
          else if (!o.comision_texto) { puntos = 100; dato = "No reporta comisión"; faltante = false; }
          break;
        case "seguros": puntos = o.tiene_seguro ? 60 : 100; dato = o.tiene_seguro ? "Reporta seguros" : "Sin seguro reportado"; faltante = false; break;
        case "certeza": puntos = o.efectiva_es_max ? 55 : 100; dato = o.efectiva_es_max ? "Tasa 'hasta' (tope)" : "Tasa fija reportada"; faltante = false; break;
        case "info": { const n = o.productos?.length ?? 0; puntos = n ? 100 : 40; dato = n ? `${n} producto(s)` : "Sin detalle publicado"; faltante = false; break; }
        case "membresia": if (o.membresia_max != null) { puntos = norm(o.membresia_max, mMin, mMax); dato = `hasta $${o.membresia_max}`; faltante = false; } break;
        case "retiro": if (o.retiro_pct != null) { puntos = norm(o.retiro_pct, rMin, rMax); dato = `${o.retiro_pct}%`; faltante = false; } break;
        case "beneficios": {
          const n = (o.tarjetas ?? []).length;
          puntos = n === 0 ? 30 : norm(n, bMin, bMax, false);
          dato = n ? `${n} tarjeta(s) documentadas` : "Sin catálogo"; faltante = n === 0; break;
        }
        case "promos": { const n = o.n_promos ?? 0; puntos = norm(n, pMin, pMax, false); dato = `${n} vigente(s)`; faltante = false; break; }
      }
      return { id, puntos, peso, dato, faltante };
    });
    const score = det.reduce((s, d) => s + d.puntos * d.peso, 0) / totalPeso;
    const r: Resultado = { oferta: o, tea, score, detalle: det };
    if (!esTarjeta && tea != null && ctx.monto && ctx.meses) {
      r.cuota = cuotaMensual(ctx.monto, tea, ctx.meses);
      r.totalIntereses = r.cuota * ctx.meses - ctx.monto;
    }
    return r;
  });
  return res.sort((a, b) => b.score - a.score);
}
