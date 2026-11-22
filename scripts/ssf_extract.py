#!/usr/bin/env python3
"""Descarga el PDF mensual de tasas de la SSF (Superintendencia del Sistema Financiero
de El Salvador) y lo convierte a JSON estructurado.

Uso:  python3 scripts/ssf_extract.py [MMYY]      (por defecto: mes actual)
Salida: data/ssf/AAAA-MM.json

Fuente oficial: https://ssf.gob.sv/descargas/tasas_int/tasas_MMYY.pdf
Requiere: pdfplumber  (pip install pdfplumber)
"""
import json, re, sys, os, datetime, urllib.request, tempfile

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_rate(s):
    """'Hasta 18.50%' -> {'v':18.5,'max':True}; '*' -> None; 'TIBP+1%' -> {'raw':...}"""
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip().strip('"')
    if s in ("", "*"):
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m and re.fullmatch(r"(Hasta\s*)?\d+(\.\d+)?\s*%", s, re.I):
        return {"v": float(m.group(1)), "max": s.lower().startswith("hasta")}
    return {"raw": s}


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def norm_bank(n):
    n = clean(n)
    return n.rstrip(",")


def main():
    mmyy = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%m%y")
    url = f"https://ssf.gob.sv/descargas/tasas_int/tasas_{mmyy}.pdf"
    tmp = os.path.join(tempfile.gettempdir(), f"ssf_tasas_{mmyy}.pdf")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        f.write(r.read())
    pdf = pdfplumber.open(tmp)

    out = {
        "fuente": url,
        "periodo": f"20{mmyy[2:]}-{mmyy[:2]}",
        "nota": "Tasas máximas/vigentes reportadas por cada entidad a la SSF. 'max' = la entidad reporta 'Hasta'.",
        "tasas_activas": {},   # banco -> {categoria: {nominal, efectiva}}
        "tarjetas_tasas": {},  # banco -> [{limite_min, nominal, efectiva}]
        "tarjetas_comisiones": {},
        "comisiones_creditos": {},
        "seguros_recargos": {},
    }

    # --- Página 3: tasas activas por categoría de crédito
    cats = None
    p3 = [t for t in pdf.pages[2].extract_tables() if len(t) > 5]
    for t in p3:
        banks = []
        header = t[0]
        for i in range(2, len(header), 2):
            banks.append((norm_bank(header[i]), i))
        group = ""
        for row in t[2:]:
            if clean(row[0]):
                group = clean(row[0])
            desc = clean(row[1])
            key = f"{group} | {desc}"
            for name, i in banks:
                nom, efe = parse_rate(row[i]), parse_rate(row[i + 1])
                if nom is None and efe is None:
                    continue
                out["tasas_activas"].setdefault(name, {})[key] = {"nominal": nom, "efectiva": efe}

    # --- Página 9: tasas de tarjetas de crédito por límite mínimo
    for t in [t for t in pdf.pages[8].extract_tables() if len(t) > 5]:
        header = t[0]
        banks = [(norm_bank(header[i]), i) for i in range(1, len(header), 2)]
        for row in t[2:]:
            lim = clean(row[0]).replace(",", "")
            if not lim:
                continue
            for name, i in banks:
                nom, efe = parse_rate(row[i]), parse_rate(row[i + 1])
                if nom is None and efe is None:
                    continue
                out["tarjetas_tasas"].setdefault(name, []).append(
                    {"limite_min": float(lim), "nominal": nom, "efectiva": efe}
                )

    # --- Página 10: comisiones de tarjetas de crédito
    cols = ["membresia_titular", "membresia_adicional", "retiro_efectivo", "reposicion",
            "sobregiro", "refinanciamiento", "plan_seguro_robo_fraude", "copia_voucher",
            "interes_moratorio", "recargo_moratorio"]
    for t in [t for t in pdf.pages[9].extract_tables() if len(t) > 5]:
        for row in t[2:]:
            name = norm_bank(row[1])
            if not name:
                continue
            out["tarjetas_comisiones"][name] = {c: clean(v) for c, v in zip(cols, row[2:])}

    # --- Página 7: comisiones por operaciones activas (créditos)
    for t in [t for t in pdf.pages[6].extract_tables() if len(t) > 5]:
        for row in t[2:]:
            name = norm_bank(row[0])
            if name and name not in ("Bancos",):
                out["comisiones_creditos"][name] = {
                    "contratacion_otorgamiento": clean(row[1]),
                    "administracion": clean(row[2]),
                    "peritajes_valuos": clean(row[3]),
                }

    # --- Página 8: seguros (daños / vehículos / vida) cargados en créditos
    for t in [t for t in pdf.pages[7].extract_tables() if len(t) > 5]:
        for row in t[2:]:
            name = norm_bank(row[0])
            if name and name not in ("Bancos",):
                out["seguros_recargos"][name] = {
                    "seguro_danos_vehiculos": clean(row[4]) if len(row) > 4 else "",
                    "seguro_vida": clean(row[5]) if len(row) > 5 else "",
                }

    dest = os.path.join(ROOT, "data", "ssf", f"{out['periodo']}.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("OK", dest, {k: len(v) for k, v in out.items() if isinstance(v, dict)})


if __name__ == "__main__":
    main()
