"use client";
import { useMemo, useState } from "react";
import type { Promocion } from "@/lib/types";

const CONF = {
  sitio_oficial: { t: "Sitio oficial", c: "good" },
  red_social: { t: "Red social oficial", c: "good" },
  prensa: { t: "Prensa · confirmar bases", c: "warn" },
} as const;
const CANAL: Record<string, string> = { web: "🌐 Web", facebook: "📘 Facebook", instagram: "📸 Instagram", prensa: "📰 Prensa" };
const fecha = (d: string | null) => (d ? new Date(d + "T12:00:00").toLocaleDateString("es-SV", { day: "numeric", month: "short", year: "numeric" }) : null);

export default function PromoList({ promos, hoy }: { promos: Promocion[]; hoy: string }) {
  const [entidad, setEntidad] = useState("todas");
  const [tipo, setTipo] = useState("todos");
  const [soloVigentes, setSoloVigentes] = useState(true);
  const [q, setQ] = useState("");

  const entidades = useMemo(() => Array.from(new Set(promos.map((p) => p.entidad))).sort(), [promos]);
  const tipos = useMemo(() => Array.from(new Set(promos.map((p) => p.tipo))).sort(), [promos]);
  const list = promos.filter(
    (p) =>
      (entidad === "todas" || p.entidad === entidad) &&
      (tipo === "todos" || p.tipo === tipo) &&
      (!soloVigentes || !p.hasta || p.hasta >= hoy) &&
      (!q || (p.titulo + p.descripcion + p.tarjetas.join(" ")).toLowerCase().includes(q.toLowerCase()))
  );

  return (
    <>
      <div className="card" style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))" }}>
        <div><label>Buscar</label>
          <input style={{ width: "100%", padding: "8px 10px", border: "1px solid var(--line)", borderRadius: 8, background: "var(--bg)", color: "var(--ink)" }}
            placeholder="restaurante, millas, Black…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <div><label>Banco</label>
          <select value={entidad} onChange={(e) => setEntidad(e.target.value)}><option value="todas">Todos</option>{entidades.map((x) => <option key={x}>{x}</option>)}</select></div>
        <div><label>Tipo</label>
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="todos">Todos</option>{tipos.map((x) => <option key={x}>{x}</option>)}</select></div>
        <div><label>Vigencia</label>
          <label style={{ fontWeight: 400 }}><input type="checkbox" checked={soloVigentes} onChange={(e) => setSoloVigentes(e.target.checked)} /> Solo vigentes hoy</label></div>
      </div>
      <p className="muted small">{list.length} promociones</p>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))" }}>
        {list.map((p) => {
          const vencida = p.hasta && p.hasta < hoy;
          return (
            <article className="card" key={p.id} style={vencida ? { opacity: 0.6 } : undefined}>
              <div className="row" style={{ alignItems: "flex-start" }}>
                <span className="chip">{p.entidad}</span>
                <span className={`chip ${CONF[p.confianza].c}`}>{CONF[p.confianza].t}</span>
              </div>
              <h3 style={{ marginTop: 8 }}>{p.titulo}</h3>
              <p className="muted small" style={{ margin: "4px 0 8px" }}>{p.descripcion}</p>
              {p.tarjetas.length > 0 && <div className="small"><b>Tarjetas:</b> {p.tarjetas.join(", ")}</div>}
              <div className="small muted" style={{ marginTop: 6 }}>
                {CANAL[p.canal] ?? p.canal} · {p.tipo}
                {" · "}
                {p.desde || p.hasta ? <>Vigencia: {fecha(p.desde) ?? "—"} → {fecha(p.hasta) ?? "sin fecha publicada"}</> : "Vigencia no publicada"}
                {vencida && <span className="chip bad" style={{ marginLeft: 6 }}>Vencida</span>}
              </div>
              <div className="small" style={{ marginTop: 8 }}>
                <a href={p.url} target="_blank" rel="noreferrer">Ver fuente</a> <span className="muted">· verificada {fecha(p.verificado)}</span>
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
