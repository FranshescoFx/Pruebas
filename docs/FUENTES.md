# Fuentes, cobertura y pendientes

## Cobertura actual (22-nov-2026)
- **Tasas oficiales SSF (nov-2026):** 21 entidades (bancos, SAC/financieras, cooperativas). 77 ofertas derivadas.
- **Catálogo de tarjetas:** BAC (9) y Banco Agrícola (9) leídos de sus sitios. Pendiente: Cuscatlán, Davivienda, Promerica, Hipotecario, Atlántida, Azul, Industrial, Fedecrédito.
- **Productos de crédito nombrados:** Agrícola y Promerica. Pendiente: resto.
- **Promociones:** 13 (Agrícola 8 vía web, BAC 3, Cuscatlán 1 y Davivienda 1 vía prensa).

## Redes sociales (Facebook / Instagram)
Meta exige sesión iniciada y prohíbe el scraping automatizado; además el entorno de desarrollo bloquea esos dominios.
Opciones para incorporarlas:
1. **Captura manual guiada:** copiar la publicación y agregarla a `data/promotions.json` con `"canal":"facebook"|"instagram"`, `"confianza":"red_social"` y la URL del post.
2. **API oficial de Meta (Graph API / Content Library):** requiere app y permisos; solo accede a páginas que autoricen o a la biblioteca de contenido.
3. **Proveedor de datos autorizado** (p. ej. Apify) con credenciales propias.
Perfiles oficiales ya identificados: ver `data/entities.json` (Agrícola, Promerica, Davivienda).

## Limitaciones de los datos
- La SSF no distingue personal / consolidación / vehículo (todo es "Consumo").
- Muchas tasas son "hasta" (máximas); el reporte no trae plazos ni montos por producto.
- Se descartan tasas de tarjeta imposibles del PDF (<8% efectiva o efectiva < nominal).
- BAC bloquea clientes HTTP simples (requiere navegador real); Banco ABANK y BFA devuelven 403 a bots.
