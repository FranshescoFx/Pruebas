import { NextResponse } from "next/server";
import { getOfertas } from "@/lib/db";
import { PRODUCTOS, type Producto } from "@/lib/types";

export const dynamic = "force-dynamic";

export function GET(req: Request) {
  const p = new URL(req.url).searchParams.get("producto") ?? "tarjeta";
  if (!(p in PRODUCTOS)) return NextResponse.json({ error: "producto inválido", validos: Object.keys(PRODUCTOS) }, { status: 400 });
  return NextResponse.json(getOfertas(p as Producto));
}
