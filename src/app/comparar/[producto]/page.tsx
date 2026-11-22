import { notFound } from "next/navigation";
import { getMeta, getOfertas } from "@/lib/db";
import { PRODUCTOS, type Producto } from "@/lib/types";
import Comparator from "./Comparator";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ producto: string }> }) {
  const { producto } = await params;
  if (!(producto in PRODUCTOS)) notFound();
  const p = producto as Producto;
  const ofertas = getOfertas(p);
  const meta = getMeta();
  return (
    <>
      <h1>{PRODUCTOS[p].icono} {PRODUCTOS[p].titulo}</h1>
      <p className="lead">{PRODUCTOS[p].descr} Ajusta tus datos y la importancia de cada criterio: el ranking se recalcula al instante.</p>
      <Comparator producto={p} ofertas={ofertas} periodo={meta.periodo} />
    </>
  );
}
