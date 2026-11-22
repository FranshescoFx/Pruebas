import { getPromociones } from "@/lib/db";
import PromoList from "./PromoList";

export const dynamic = "force-dynamic";

export default function Page() {
  const promos = getPromociones();
  return (
    <>
      <h1>🔥 Promociones exclusivas de tarjetas de crédito</h1>
      <p className="lead">
        Descuentos, cuotas sin intereses, sorteos y millas para tarjetahabientes. Cada promoción indica su fuente y nivel de
        confianza; confirma siempre las bases con el banco.
      </p>
      <PromoList promos={promos} hoy={new Date().toISOString().slice(0, 10)} />
    </>
  );
}
