import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Comparador Financiero El Salvador",
  description: "Compara tarjetas de crédito y préstamos de bancos, financieras y cooperativas de El Salvador con datos oficiales de la SSF.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <header className="top">
          <div className="wrap">
            <Link href="/" className="logo">💱 Comparador SV</Link>
            <nav>
              <Link href="/comparar/tarjeta">Tarjetas</Link>
              <Link href="/comparar/personal">Personal</Link>
              <Link href="/comparar/consolidacion">Consolidación</Link>
              <Link href="/comparar/vehiculo">Vehículo</Link>
              <Link href="/comparar/vivienda">Vivienda</Link>
              <Link href="/promociones">🔥 Promociones exclusivas</Link>
              <Link href="/metodologia">Metodología</Link>
            </nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="wrap">
          Información referencial, no constituye asesoría financiera ni oferta vinculante. Verifica siempre condiciones, aprobación y tasa final con la entidad.
        </footer>
      </body>
    </html>
  );
}
