import { getMeta } from "@/lib/db";
import { CRITERIOS, CRITERIOS_POR_PRODUCTO, PESOS_DEFECTO } from "@/lib/scoring";
import { PRODUCTOS, type Producto } from "@/lib/types";

export const dynamic = "force-dynamic";

export default function Page() {
  const meta = getMeta();
  return (
    <>
      <h1>Metodología y fuentes</h1>
      <h2>De dónde salen los datos</h2>
      <ul>
        <li><b>Tasas, comisiones y seguros:</b> reporte mensual obligatorio de la SSF (<a href={meta.fuente}>PDF vigencia {meta.periodo}</a>), con tasa nominal y efectiva por entidad y tramo de límite en tarjetas. Se extrae con <code>scripts/ssf_extract.py</code>.</li>
        <li><b>Catálogo de tarjetas y productos de crédito:</b> sitios web oficiales de cada entidad (columna «verificada» con fecha).</li>
        <li><b>Promociones exclusivas:</b> páginas de promociones de los bancos y prensa. Redes sociales (Facebook/Instagram) no permiten lectura automática sin autorización: se cargan manualmente o vía API oficial de Meta. Cada promo muestra su <i>canal</i> y <i>nivel de confianza</i>.</li>
      </ul>
      <h2>Limitaciones</h2>
      <ul>
        <li>La SSF agrupa personal, consolidación y vehículo en una sola categoría «Consumo»; por eso la tasa base es la misma y se diferencian por seguros, comisiones y productos.</li>
        <li>Muchas entidades reportan tasas «hasta» (máximas). La tasa real depende de tu perfil, ingresos, garantía y plazo.</li>
        <li>El reporte no incluye plazo ni monto mínimo/máximo por producto; usa el simulador con tus propios datos.</li>
        <li>Se descartan valores imposibles del reporte (p. ej. TEA menor a 8% en tarjetas) como errores de transcripción.</li>
      </ul>
      <h2>Cómo se calcula la calificación (0–100)</h2>
      <p>Cada criterio se normaliza entre la mejor y la peor opción del conjunto comparado (0 = peor, 100 = mejor); los datos faltantes reciben 50 y se marcan. La nota final es el promedio ponderado con los pesos que tú eliges.</p>
      {(Object.keys(PESOS_DEFECTO) as Producto[]).map((p) => (
        <div key={p} className="card" style={{ marginBottom: 10 }}>
          <h3>{PRODUCTOS[p].icono} {PRODUCTOS[p].titulo}</h3>
          <table><tbody>
            {CRITERIOS_POR_PRODUCTO[p].map((id) => (
              <tr key={id}><td style={{ width: "34%" }}>{CRITERIOS[id].label}</td><td style={{ width: 60 }}>{PESOS_DEFECTO[p][id]}%</td><td className="muted">{CRITERIOS[id].ayuda}</td></tr>
            ))}
          </tbody></table>
        </div>
      ))}
    </>
  );
}
