export type Producto = "tarjeta" | "personal" | "consolidacion" | "vehiculo" | "vivienda";

export interface Entidad {
  id: string; nombre: string; tipo: string; web: string | null; facebook: string | null; instagram: string | null;
}
export interface Tier { limite_min: number; nominal: number | null; efectiva: number | null }
export interface Oferta {
  id: string; entidad_id: string; entidad: string; tipo_entidad: string; producto: Producto; nombre: string;
  tasa_nominal: number | null; tasa_efectiva: number | null; nominal_es_max: boolean; efectiva_es_max: boolean;
  comision_texto: string | null; comision_pct_max: number | null; seguro_texto: string | null; tiene_seguro: boolean;
  nota: string | null; fuente_url: string; periodo: string; web: string | null;
  tiers?: Tier[]; membresia_max?: number | null; retiro_pct?: number | null; mora_texto?: string | null;
  productos?: { nombre: string; descripcion: string; url: string }[];
  tarjetas?: { nombre: string; red: string; nivel: string; categoria: string; beneficios: string[]; url: string }[];
  n_promos?: number;
}
export interface Promocion {
  id: string; entidad_id: string; entidad: string; titulo: string; descripcion: string; tarjetas: string[];
  tipo: string; categoria: string; exclusiva_tarjeta: boolean; canal: string; desde: string | null; hasta: string | null;
  url: string; confianza: "sitio_oficial" | "prensa" | "red_social"; verificado: string;
}
export const PRODUCTOS: Record<Producto, { titulo: string; icono: string; descr: string }> = {
  tarjeta: { titulo: "Tarjeta de crédito", icono: "💳", descr: "Compara tasas por límite, membresía y comisiones." },
  personal: { titulo: "Crédito personal", icono: "🧾", descr: "Libre inversión, con orden de descuento o cargo a cuenta." },
  consolidacion: { titulo: "Consolidación de deudas", icono: "🧩", descr: "Junta tus deudas en una sola cuota." },
  vehiculo: { titulo: "Crédito para vehículo", icono: "🚗", descr: "Financiamiento para auto nuevo o usado." },
  vivienda: { titulo: "Crédito de vivienda", icono: "🏠", descr: "Compra, construcción o traslado de hipoteca." },
};
