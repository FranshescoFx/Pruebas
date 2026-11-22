# Comparador Financiero El Salvador

Aplicativo web (Next.js 15 + TypeScript + SQLite nativo de Node) que compara tarjetas de crédito y préstamos
(personal, consolidación, vehículo, vivienda) de bancos, financieras y cooperativas de El Salvador, con una
calificación 0–100 configurable y una sección de **promociones exclusivas de tarjetas**.

## Uso
```bash
npm install
npm run dev        # siembra data/app.db y abre http://localhost:3000
npm run build && npm start
```
Requiere Node ≥ 22.5 (usa `node:sqlite`).

## Datos
| Fuente | Qué aporta | Cómo se actualiza |
|---|---|---|
| SSF (PDF mensual oficial) | Tasa nominal/efectiva por entidad, tramos de límite en tarjetas, comisiones, seguros | `npm run ssf -- MMYY` (p. ej. `1226`) y luego `npm run seed` |
| Sitios de los bancos | Catálogo de tarjetas y productos (`data/cards.json`, `data/loan-products.json`) | Revisión manual / `scripts/fetch_text.cjs` |
| Promociones | `data/promotions.json` (campo `canal`: web, prensa, facebook, instagram; `confianza`) | Edición manual tras revisar fuentes |

Ver `docs/FUENTES.md` para limitaciones (redes sociales, "tasas hasta", categoría "Consumo").
