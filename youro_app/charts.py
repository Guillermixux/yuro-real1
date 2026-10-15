"""Gráficas SVG puras para Yuro (sin librerías externas)."""


def grafica_lineas(valores, etiquetas=None, color="#f59e0b", alto=200, ancho=600):
    """Gráfico de líneas con área sombreada."""
    if not valores or len(valores) < 2:
        return '<div class="sub">Sin datos suficientes</div>'

    n = len(valores)
    max_v = max(valores)
    min_v = min(valores)
    rango = max_v - min_v if max_v != min_v else 1

    # Calcular puntos
    puntos = []
    area = []
    for i, v in enumerate(valores):
        x = (i / (n - 1)) * (ancho - 40) + 20
        y = alto - 30 - ((v - min_v) / rango) * (alto - 60)
        puntos.append(f"{x:.1f},{y:.1f}")
        area.append(f"{x:.1f},{y:.1f}")

    # Área cerrada
    area_str = " ".join(area)
    area_str += f" {ancho-20:.1f},{alto-30} 20,{alto-30}"

    # Etiquetas X
    labels = ""
    if etiquetas:
        for i, et in enumerate(etiquetas):
            if i % max(1, n // 5) == 0:
                x = (i / (n - 1)) * (ancho - 40) + 20
                labels += f'<text x="{x:.0f}" y="{alto-8}" fill="#596174" font-size="10" text-anchor="middle">{et}</text>'

    # Valores Y
    y_labels = ""
    for frac in [0, 0.5, 1]:
        v = min_v + rango * frac
        y = alto - 30 - frac * (alto - 60)
        y_labels += f'<text x="4" y="{y:.0f}" fill="#596174" font-size="9">{v:.0f}</text>'

    return f"""
    <svg viewBox="0 0 {ancho} {alto}" style="width:100%;height:auto;max-height:{alto}px">
      <defs>
        <linearGradient id="grad-{color[1:]}" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:{color};stop-opacity:0.3"/>
          <stop offset="100%" style="stop-color:{color};stop-opacity:0"/>
        </linearGradient>
      </defs>
      <!-- Grid -->
      <line x1="20" y1="{alto-30}" x2="{ancho-20}" y2="{alto-30}" stroke="#232a3a" stroke-width="1"/>
      <line x1="20" y1="{alto/2}" x2="{ancho-20}" y2="{alto/2}" stroke="#232a3a" stroke-width="1" stroke-dasharray="4"/>
      <!-- Área -->
      <polygon points="{area_str}" fill="url(#grad-{color[1:]})"/>
      <!-- Línea -->
      <polyline points="{' '.join(puntos)}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <!-- Puntos -->
      {' '.join(f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3" fill="{color}" stroke="#12161f" stroke-width="2"/>' for p in puntos[-3:])}
      {labels}
      {y_labels}
    </svg>"""


def grafica_barras(datos, color="#f59e0b", alto=200, ancho=600):
    """Gráfico de barras horizontales. datos = [(etiqueta, valor), ...]"""
    if not datos:
        return '<div class="sub">Sin datos</div>'

    max_v = max(v for _, v in datos) if datos else 1
    n = len(datos)
    barra_alto = min(36, (alto - 20) // max(1, n))
    gap = 8

    barras = ""
    for i, (etiqueta, valor) in enumerate(datos):
        y = i * (barra_alto + gap) + 10
        ancho_barra = (valor / max_v) * (ancho - 150) if max_v else 0
        # Truncar etiqueta
        et_corta = etiqueta[:15] + "…" if len(etiqueta) > 15 else etiqueta
        barras += f'''
        <text x="0" y="{y + barra_alto/2 + 4}" fill="#8b94a8" font-size="11">{et_corta}</text>
        <rect x="100" y="{y}" width="{ancho_barra:.0f}" height="{barra_alto}" rx="4" fill="{color}" opacity="0.8">
          <animate attributeName="width" from="0" to="{ancho_barra:.0f}" dur="0.6s" fill="freeze"/>
        </rect>
        <text x="{100 + ancho_barra + 8:.0f}" y="{y + barra_alto/2 + 4}" fill="#e8ebf2" font-size="11" font-weight="600">{valor:.2f}</text>
        '''

    total_alto = n * (barra_alto + gap) + 20
    return f'''
    <svg viewBox="0 0 {ancho} {total_alto}" style="width:100%;height:auto">
      {barras}
    </svg>'''


def grafica_donut(porcentajes, colores=None, centro_texto="", centro_valor="", alto=200):
    """Gráfico donut/chart circular."""
    if not porcentajes:
        return '<div class="sub">Sin datos</div>'

    if colores is None:
        colores = ["#f59e0b", "#34d399", "#7dd3fc", "#f87171", "#a78bfa", "#fb923c"]

    total = sum(p for p, _ in porcentajes) if isinstance(porcentajes[0], tuple) else sum(porcentajes)
    if total == 0:
        return '<div class="sub">Sin datos</div>'

    cx, cy, r = 100, 100, 70
    grosor = 24

    # Calcular ángulos
    angulo_actual = -90  # empezar arriba
    circles = ""
    for i, item in enumerate(porcentajes):
        if isinstance(item, tuple):
            pct, etiqueta = item
        else:
            pct, etiqueta = item, f"Item {i+1}"

        angulo = (pct / total) * 360
        circunferencia = 2 * 3.14159 * r
        dash = (angulo / 360) * circunferencia
        gap = circunferencia - dash

        color = colores[i % len(colores)]
        circles += f'''
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{grosor}"
          stroke-dasharray="{dash:.1f} {gap:.1f}"
          transform="rotate({angulo_actual} {cx} {cy})"
          opacity="0.9">
          <animate attributeName="stroke-dasharray" from="0 {circunferencia}" to="{dash:.1f} {gap:.1f}" dur="0.8s" fill="freeze"/>
        </circle>'''
        angulo_actual += angulo

    # Texto central
    texto = ""
    if centro_texto:
        texto += f'<text x="{cx}" y="{cy-8}" fill="#8b94a8" font-size="12" text-anchor="middle">{centro_texto}</text>'
    if centro_valor:
        texto += f'<text x="{cx}" y="{cy+12}" fill="#f59e0b" font-size="18" font-weight="900" text-anchor="middle">{centro_valor}</text>'

    # Leyenda
    leyenda = ""
    x_leyenda = 200
    for i, item in enumerate(porcentajes):
        if isinstance(item, tuple):
            pct, etiqueta = item
        else:
            pct, etiqueta = item, f"Item {i+1}"
        color = colores[i % len(colores)]
        y = 30 + i * 24
        leyenda += f'''
        <rect x="{x_leyenda}" y="{y-10}" width="12" height="12" rx="3" fill="{color}"/>
        <text x="{x_leyenda + 18}" y="{y}" fill="#8b94a8" font-size="11">{etiqueta}</text>
        <text x="{x_leyenda + 140}" y="{y}" fill="#e8ebf2" font-size="11" font-weight="600" text-anchor="end">{pct:.1f}%</text>
        '''

    return f'''
    <svg viewBox="0 0 400 {max(200, len(porcentajes) * 24 + 40)}" style="width:100%;height:auto">
      {circles}
      {texto}
      {leyenda}
    </svg>'''


def heatmap_actividad(datos, ancho=600, alto=120):
    """Mapa de calor: datos = lista de (hora, dia, valor)."""
    if not datos:
        return '<div class="sub">Sin datos de actividad</div>'

    horas = 24
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    celda_w = (ancho - 60) / horas
    celda_h = (alto - 30) / len(dias)

    max_v = max(v for _, _, v in datos) if datos else 1

    # Crear matriz
    matriz = {}
    for h, d, v in datos:
        matriz[(d, h)] = v

    cells = ""
    for di, dia in enumerate(dias):
        y = 20 + di * celda_h
        cells += f'<text x="0" y="{y + celda_h/2 + 4}" fill="#596174" font-size="9">{dia}</text>'
        for h in range(horas):
            v = matriz.get((di, h), 0)
            intensidad = v / max_v if max_v else 0
            # Color: de oscuro a dorado/rojo
            if intensidad > 0.7:
                color = "#f87171"
            elif intensidad > 0.4:
                color = "#f59e0b"
            elif intensidad > 0.1:
                color = "#92700c"
            else:
                color = "#1a1f2e"
            x = 55 + h * celda_w
            cells += f'''<rect x="{x:.1f}" y="{y:.1f}" width="{celda_w-2:.1f}" height="{celda_h-2:.1f}" 
                          rx="2" fill="{color}" opacity="{0.3 + intensidad * 0.7:.2f}"/>'''

    return f'''
    <svg viewBox="0 0 {ancho} {alto}" style="width:100%;height:auto">
      {cells}
      <text x="{55 + 12 * celda_w}" y="{alto - 4}" fill="#596174" font-size="9" text-anchor="middle">Hora del día</text>
    </svg>'''


def barra_progreso(valor, maximo=100, color="#f59e0b", etiqueta=""):
    """Barra de progreso horizontal."""
    pct = min(100, (valor / maximo * 100) if maximo else 0)
    return f'''
    <div style="margin:8px 0">
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#8b94a8;margin-bottom:4px">
        <span>{etiqueta}</span>
        <span style="color:#e8ebf2;font-weight:600">{valor:.0f}/{maximo:.0f}</span>
      </div>
      <div style="background:#1a1f2e;border-radius:8px;height:12px;overflow:hidden">
        <div style="background:linear-gradient(90deg,{color},{color}cc);height:100%;width:{pct:.0f}%;border-radius:8px;transition:width 0.6s ease"></div>
      </div>
    </div>'''


def stat_card(valor, etiqueta, icono="📊", color="#f59e0b", tendencia=None):
    """Tarjeta de estadística con animación."""
    tendencia_html = ""
    if tendencia is not None:
        if tendencia > 0:
            tendencia_html = f'<span style="color:#34d399;font-size:12px">▲ +{tendencia:.0f}%</span>'
        elif tendencia < 0:
            tendencia_html = f'<span style="color:#f87171;font-size:12px">▼ {tendencia:.0f}%</span>'
        else:
            tendencia_html = '<span style="color:#8b94a8;font-size:12px">— 0%</span>'

    return f'''
    <div class="panel" style="margin:0;position:relative;overflow:hidden">
      <div style="position:absolute;top:-10px;right:-10px;font-size:60px;opacity:0.08">{icono}</div>
      <div class="sub" style="font-size:12px;text-transform:uppercase;letter-spacing:0.5px">{etiqueta}</div>
      <div style="font-size:28px;font-weight:900;color:{color};margin:4px 0">{valor}</div>
      {tendencia_html}
    </div>'''
