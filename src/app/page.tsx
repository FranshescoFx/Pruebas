import Link from "next/link";
import { getEntidades, getMeta, getPromociones } from "@/lib/db";
import { PRODUCTOS, type Producto } from "@/lib/types";

export const dynamic = "force-dynamic";

export default function Home() {
  const meta = getMeta();
  const n = getEntidades().length;
  const hoy = new Date().toISOString().slice(0, 10);
  const promos = getPromociones().filter((p) => !p.hasta || p.hasta >= hoy).length;
  return (
    <>
      <h1>Encuentra el financiamiento que mejor te conviene en El Salvador</h1>
      <p className="lead">
        Comparamos {n} entidades (bancos, financieras y cooperativas) con las tasas que reportan oficialmente a la
        Superintendencia del Sistema Financiero (SSF), y calificamos cada opción de 0 a 100 según tasa efectiva, comisiones,
        seguros y más. Tú decides cuánto pesa cada criterio.
      </p>
      <div className="grid" style={{ marginTop: 18 }}>
        {(Object.keys(PRODUCTOS) as Producto[]).map((k) => (
          <Link key={k} href={`/comparar/${k}`} className="card">
            <div style={{ fontSize: 28 }}>{PRODUCTOS[k].icono}</div>
            <h3>{PRODUCTOS[k].titulo}</h3>
            <div className="muted small">{PRODUCTOS[k].descr}</div>
          </Link>
        ))}
        <Link href="/promociones" className="card" style={{ borderColor: "var(--brand)" }}>
          <div style={{ fontSize: 28 }}>🔥</div>
          <h3>Promociones exclusivas de tarjetas</h3>
          <div className="muted small">{promos} vigentes hoy: descuentos, cuotas sin interés, sorteos y millas.</div>
        </Link>
      </div>
      <div className="banner">
        <b>Transparencia de datos:</b> las tasas provienen del reporte oficial de la SSF (vigencia {meta.periodo}). Muchas
        entidades reportan tasas <i>«hasta»</i> (máximas); la tasa que recibas depende de tu perfil. Las promociones se
        recopilan de sitios web de los bancos y prensa; las de redes sociales se cargan manualmente (ver{" "}
        <Link href="/metodologia">metodología</Link>).
      </div>
    </>
  );
}
