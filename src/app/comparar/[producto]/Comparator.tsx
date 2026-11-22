"use client";
import { useMemo, useState } from "react";
import type { Oferta, Producto } from "@/lib/types";
import { CRITERIOS, CRITERIOS_POR_PRODUCTO, PESOS_DEFECTO, puntuar, tasaTarjeta, type CriterioId } from "@/lib/scoring";

const colorScore = (s: number) => (s >= 75 ? "var(--good)" : s >= 50 ? "var(--brand)" : s >= 30 ? "var(--warn)" : "var(--bad)");
const money = (n: number) => n.toLocaleString("es-SV", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const money2 = (n: number) => n.toLocaleString("es-SV", { style: "currency", currency: "USD" });
const TIPOS: Record<string, string> = { banco: "Banco", estatal: "Banco estatal", financiera: "Financiera / SAC", cooperativa: "Cooperativa / banco de trabajadores" };

export default function Comparator({ producto, ofertas, periodo }: { producto: Producto; ofertas: Oferta[]; periodo: string }) {
  const esTarjeta = producto === "tarjeta";
  const [pesos, setPesos] = useState<Partial<Record<CriterioId, number>>>(PESOS_DEFECTO[producto]);
  const [limite, setLimite] = useState(1500);
  const [monto, setMonto] = useState(producto === "vivienda" ? 80000 : producto === "vehiculo" ? 15000 : 5000);
  const [meses, setMeses] = useState(producto === "vivienda" ? 240 : producto === "vehiculo" ? 60 : 36);
  const [tipo, setTipo] = useState("todos");

  const filtradas = useMemo(() => ofertas.filter((o) => tipo === "todos" || o.tipo_entidad === tipo), [ofertas, tipo]);
  const res = useMemo(() => puntuar(filtradas, { producto, pesos, limite, monto, meses }), [filtradas, producto, pesos, limite, monto, meses]);
  const excluidas = esTarjeta ? filtradas.length - res.length : 0;
  const tipos = Array.from(new Set(ofertas.map((o) => o.tipo_entidad)));

  return (
    <div className="panel">
      <aside className="card">
        <h3>Tu necesidad</h3>
        {esTarjeta ? (
          <>
            <label>Límite de crédito que esperas: <b>{money(limite)}</b></label>
            <input type="range" min={200} max={10000} step={100} value={limite} onChange={(e) => setLimite(+e.target.value)} />
            <div className="muted small">Las tasas de tarjetas dependen del límite aprobado (tramos oficiales SSF).</div>
          </>
        ) : (
          <>
            <label>Monto a financiar (USD)</label>
            <input type="number" min={500} step={500} value={monto} onChange={(e) => setMonto(+e.target.value || 0)} />
            <label>Plazo: <b>{meses} meses ({(meses / 12).toFixed(1)} años)</b></label>
            <input type="range" min={6} max={producto === "vivienda" ? 360 : 120} step={6} value={meses} onChange={(e) => setMeses(+e.target.value)} />
          </>
        )}
        <label>Tipo de entidad</label>
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="todos">Todas</option>
          {tipos.map((t) => <option key={t} value={t}>{TIPOS[t] ?? t}</option>)}
        </select>

        <h3 style={{ marginTop: 18 }}>¿Qué te importa más?</h3>
        {CRITERIOS_POR_PRODUCTO[producto].map((id) => (
          <div key={id}>
            <label title={CRITERIOS[id].ayuda}>{CRITERIOS[id].label}: <b>{pesos[id] ?? 0}</b></label>
            <input type="range" min={0} max={100} step={5} value={pesos[id] ?? 0} onChange={(e) => setPesos({ ...pesos, [id]: +e.target.value })} />
          </div>
        ))}
        <button className="tab" style={{ marginTop: 10 }} onClick={() => setPesos(PESOS_DEFECTO[producto])}>Restablecer pesos</button>
      </aside>

      <section>
        <div className="muted small" style={{ marginBottom: 8 }}>
          {res.length} opciones ordenadas por calificación · tasas SSF vigencia {periodo}
          {excluidas > 0 && ` · ${excluidas} entidades sin tarjetas reportadas para un límite de ${money(limite)}`}
        </div>
        {res.map((r, i) => {
          const o = r.oferta;
          const t = esTarjeta ? tasaTarjeta(o, limite) : null;
          return (
            <article className="offer" key={o.id} style={i === 0 ? { borderColor: "var(--brand)" } : undefined}>
              <div className="score" style={{ background: colorScore(r.score) }} title="Calificación 0–100">{Math.round(r.score)}</div>
              <div>
                <h3>{i === 0 && "🏆 "}{o.entidad} <span className="chip">{TIPOS[o.tipo_entidad] ?? o.tipo_entidad}</span></h3>
                <div className="muted small">{o.nombre}</div>
                {(o.n_promos ?? 0) > 0 && esTarjeta && <span className="chip good">🔥 {o.n_promos} promo(s) vigente(s)</span>}
                {o.efectiva_es_max && !esTarjeta && <span className="chip warn">Tasa «hasta» (máxima)</span>}
                <details>
                  <summary>Ver detalle y calificación</summary>
                  <table style={{ marginTop: 8 }}>
                    <tbody>
                      {r.detalle.map((d) => (
                        <tr key={d.id}>
                          <td style={{ width: "42%" }}>{CRITERIOS[d.id].label} <span className="muted">({d.peso})</span></td>
                          <td>{d.dato}{d.faltante && <span className="chip warn" style={{ marginLeft: 6 }}>dato faltante</span>}</td>
                          <td style={{ width: 90 }}><div className="bar"><i style={{ width: `${d.puntos}%` }} /></div></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {esTarjeta ? <CardDetail o={o} limite={limite} /> : <LoanDetail o={o} />}
                  <div className="muted small" style={{ marginTop: 8 }}>
                    Fuente: <a href={o.fuente_url} target="_blank" rel="noreferrer">SSF · {o.periodo}</a>
                    {o.web && <> · <a href={o.web} target="_blank" rel="noreferrer">Sitio de la entidad</a></>}
                  </div>
                </details>
              </div>
              <div className="metrics">
                <div><b>{r.tea != null ? `${r.tea.toFixed(2)}%` : "—"}</b><span>TEA{o.efectiva_es_max && !esTarjeta ? " (máx.)" : ""}</span></div>
                {esTarjeta ? (
                  <div><b>{o.membresia_max != null ? money(o.membresia_max) : "—"}</b><span>membresía máx.</span></div>
                ) : (
                  <>
                    <div><b>{o.tasa_nominal != null ? `${o.tasa_nominal.toFixed(2)}%` : "—"}</b><span>nominal</span></div>
                    <div><b>{r.cuota ? money2(r.cuota) : "—"}</b><span>cuota/mes (est.)</span></div>
                    <div><b>{r.totalIntereses != null ? money(r.totalIntereses) : "—"}</b><span>intereses totales</span></div>
                  </>
                )}
              </div>
            </article>
          );
        })}
        {!res.length && <div className="card">No hay opciones con esos filtros.</div>}
        {!esTarjeta && ofertas[0]?.nota && <div className="banner">{ofertas[0].nota}</div>}
        <div className="muted small">
          La cuota estimada usa la TEA reportada y sistema de cuota nivelada; no incluye comisiones ni seguros. Si la tasa es «hasta», el costo real puede ser menor.
        </div>
      </section>
    </div>
  );
}

function CardDetail({ o, limite }: { o: Oferta; limite: number }) {
  const t = tasaTarjeta(o, limite);
  return (
    <div style={{ marginTop: 10 }}>
      {t.tier && <div className="small">Tramo aplicado: límite desde {money(t.tier.limite_min)} → nominal {t.tier.nominal ?? "—"}% · efectiva {t.tier.efectiva ?? "—"}%</div>}
      {o.mora_texto && <div className="small muted">Recargo moratorio: {o.mora_texto}</div>}
      {o.tarjetas && o.tarjetas.length > 0 && (
        <>
          <h4 style={{ margin: "12px 0 4px" }}>Tarjetas disponibles</h4>
          <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
            {o.tarjetas.map((c) => (
              <li key={c.nombre}><a href={c.url} target="_blank" rel="noreferrer">{c.nombre}</a> — {c.beneficios.join("; ")}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function LoanDetail({ o }: { o: Oferta }) {
  return (
    <div style={{ marginTop: 10 }} className="small">
      {o.comision_texto && <div><b>Comisiones reportadas:</b> <span className="muted">{o.comision_texto.slice(0, 420)}{o.comision_texto.length > 420 ? "…" : ""}</span></div>}
      {o.seguro_texto && <div style={{ marginTop: 6 }}><b>Seguros:</b> <span className="muted">{o.seguro_texto.slice(0, 320)}</span></div>}
      {o.productos && o.productos.length > 0 && (
        <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
          {o.productos.map((p) => <li key={p.nombre}><a href={p.url} target="_blank" rel="noreferrer">{p.nombre}</a> — {p.descripcion}</li>)}
        </ul>
      )}
    </div>
  );
}
