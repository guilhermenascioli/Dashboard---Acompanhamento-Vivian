import calendar
from datetime import date


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURACAO
# ============================================================
# Link CSV da planilha (veja o README, secao "Publicar na Web").
# Pode definir tambem em Settings > Secrets como SHEET_URL.
def secret(chave, padrao):
    """Le um secret com seguranca, mesmo sem arquivo secrets.toml."""
    try:
        return st.secrets[chave]
    except Exception:
        return padrao



import os as _os
SHEET_URL = "https://docs.google.com/spreadsheets/d/17ebPrcp4yIhQ5CS0qsdIZ4UCpyQoNj5mFdRiPxvg1Sw/export?format=csv"
META_PADRAO = float(secret("META_MENSAL", 3500))  # meta de faturamento do mes


# ---- Paleta GIRASSOL -------------------------------------------------------
AMARELO = "#FDB813"
DOURADO = "#F4A100"
AMBAR = "#FFC72C"
MARROM = "#7A4B1E"
MARROM_ESC = "#4A2C12"
FOLHA = "#6B8E23"
FOLHA_ESC = "#4F7942"
CREME = "#FFF8E7"
SEQ = [AMARELO, DOURADO, MARROM, FOLHA, AMBAR, FOLHA_ESC]


st.set_page_config(page_title="Painel - Acompanhamento de Receita", page_icon="🌻", layout="wide")


# ---- ESTILO (CSS) ----------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp {
        background: radial-gradient(circle at 20% 0%, #FFFCEF 0%, #FFF1C9 55%, #FCE39A 100%);
    }
    .block-container { padding-top: 1.2rem; padding-bottom: 0.5rem; max-width: 100%; }
    /* Cabecalho */
    .titulo {
        font-size: 2.0rem; font-weight: 700; color: #4A2C12; margin: 0;
        display:flex; align-items:center; gap:.5rem;
    }
    .subtitulo { color:#6B3E14; font-weight:600; margin-top:-4px; }
    /* Cartoes de metrica */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #FFFFFF 0%, #FFF6D8 100%);
        border-left: 6px solid #FDB813;
        border-radius: 16px;
        padding: 12px 12px;
        box-shadow: 0 6px 16px rgba(122,75,30,.12);
        overflow: hidden;
    }
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] p,
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] label * {
        color:#4A2C12 !important;
        -webkit-text-fill-color:#4A2C12 !important;
        opacity:1 !important;
        font-weight:700 !important; font-size:.80rem !important;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    /* Valor: menor para caber inteiro nas 6 colunas */
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color:#2C1A08 !important; -webkit-text-fill-color:#2C1A08 !important;
        font-weight:700 !important;
        font-size: 1.25rem !important; line-height: 1.15 !important;
        white-space: nowrap;
    }
    /* Garante que nenhum filho do cartao herde cor branca da sidebar */
    div[data-testid="stMetric"] *:not([data-testid="stMetricDelta"] *) {
        color:#2C1A08 !important;
        -webkit-text-fill-color:#2C1A08 !important;
    }
    /* Delta (vs mes anterior) */
    div[data-testid="stMetricDelta"] {
        font-size: .72rem !important;
    }
    div[data-testid="stMetricDelta"] div { white-space: normal !important; }
    /* Titulos de secao */
    h3 { color:#5A3415 !important; font-weight:600 !important; }
    /* Legendas com bom contraste */
    div[data-testid="stCaptionContainer"], div[data-testid="stCaptionContainer"] p {
        color:#6B3E14 !important; font-weight:500 !important;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] { background:#4A2C12; }
    section[data-testid="stSidebar"] * { color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important; }
    section[data-testid="stSidebar"] h3 { color:#FDB813 !important; -webkit-text-fill-color:#FDB813 !important; }
    section[data-testid="stSidebar"] input { color:#FFFFFF !important; }
    section[data-testid="stSidebar"] [data-baseweb="select"] * { color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important; background:#6B3E14 !important; }
    /* Labels dos filtros fora da sidebar (ex: tabela mensal) */
    .main div[data-testid="stSelectbox"] label,
    .main div[data-testid="stSelectbox"] label p,
    .main div[data-testid="stSelectbox"] label span,
    .main div[data-testid="stSelectbox"] > label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stSelectbox"] label *,
    div[data-testid="column"] div[data-testid="stSelectbox"] label,
    div[data-testid="column"] div[data-testid="stSelectbox"] label * {
        color: #4A2C12 !important;
        -webkit-text-fill-color: #4A2C12 !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# ============================================================
# FUNCOES AUXILIARES
# ============================================================
def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")



@st.cache_data(ttl=300)
def carregar_dados(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in ["data", "nome", "sexo", "idade", "tipo", "valor"]:
        if col not in df.columns:
            df[col] = None
    # Aceita AAAA-MM-DD (ISO, sem dayfirst) e DD/MM/AAAA (br, com dayfirst)
    raw = df["data"].astype(str).str.strip()
    iso = raw.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")
    d_iso = pd.to_datetime(raw[iso], errors="coerce")
    d_br = pd.to_datetime(raw[~iso], errors="coerce", dayfirst=True)
    df["data"] = pd.concat([d_iso, d_br]).reindex(df.index)
    df["valor"] = (
        df["valor"].astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    for col in ["sexo", "idade", "tipo"]:
        df[col] = df[col].astype(str).str.strip().str.lower()
    return df.dropna(subset=["data"])



def layout_plotly(fig, altura=300):
    fig.update_layout(
        height=altura,
        margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins, sans-serif", color=MARROM_ESC, size=13),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.25,
            font=dict(color=MARROM_ESC, size=13),
        ),
    )
    # Forca marrom escuro nos eixos para garantir contraste
    fig.update_xaxes(
        tickfont=dict(color="#2C1A08", size=13),
        title_font=dict(color="#2C1A08", size=13),
        linecolor="#4A2C12", gridcolor="rgba(74,44,18,.20)",
    )
    fig.update_yaxes(
        tickfont=dict(color="#2C1A08", size=13),
        title_font=dict(color="#2C1A08", size=13),
        linecolor="#4A2C12", gridcolor="rgba(74,44,18,.20)",
    )
    return fig



# ============================================================
# CARREGAMENTO
# ============================================================
try:
    df = carregar_dados(SHEET_URL)
except Exception as e:
    st.error("Nao consegui carregar a planilha. Confira o link em SHEET_URL.")
    st.caption(f"Detalhe tecnico: {e}")
    st.stop()


if df.empty:
    st.warning("A planilha esta vazia ou sem datas validas. Adicione atendimentos para comecar.")
    st.stop()


df["mes_ano"] = df["data"].dt.to_period("M")
meses = sorted(df["mes_ano"].unique(), reverse=True)
anos_disp = sorted(df["data"].dt.year.unique(), reverse=True)

DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# ---- Barra lateral (filtro + meta) ----------------------------------------
with st.sidebar:
    st.markdown("### 🌻 Configuracoes")
    aba_sel = st.radio("Visualizacao", ["📅 Mensal", "📊 Anual"], label_visibility="collapsed")
    st.divider()
    if aba_sel == "📅 Mensal":
        mes = st.selectbox("Mes", meses, format_func=lambda p: p.strftime("%m/%Y"))
        meta = st.number_input("Meta de faturamento (R$)", min_value=0.0,
                               value=META_PADRAO, step=100.0)
    else:
        ano_sel = st.selectbox("Ano", anos_disp)
        meta_anual = st.number_input("Meta anual (R$)", min_value=0.0,
                                     value=META_PADRAO * 12, step=500.0)

# ============================================================
# ABA MENSAL
# ============================================================
if aba_sel == "📅 Mensal":
    dfm = df[df["mes_ano"] == mes]

    hoje = date.today()
    ano, mes_num = mes.year, mes.month
    dias_no_mes = calendar.monthrange(ano, mes_num)[1]
    mes_corrente = (ano == hoje.year and mes_num == hoje.month)
    dias_corridos = hoje.day if mes_corrente else dias_no_mes

    total_clientes = len(dfm)
    faturamento = dfm["valor"].sum()
    ticket = dfm["valor"].mean() if total_clientes else 0
    media_diaria = faturamento / dias_corridos if dias_corridos else 0
    projecao_mes = media_diaria * dias_no_mes
    anualizada = faturamento * (12 / mes_num)  # Receita * (12 / mes atual)
    pct_meta = (faturamento / meta * 100) if meta else 0
    ganho_liquido = faturamento * 0.60
    suite_house = faturamento * 0.40

    mes_ant = mes - 1
    fat_ant = df[df["mes_ano"] == mes_ant]["valor"].sum()
    delta = None
    if fat_ant > 0:
        delta = f"{(faturamento - fat_ant) / fat_ant * 100:+.1f}% vs mes anterior"

    por_dia = dfm.groupby(dfm["data"].dt.date)["valor"].sum().sort_index()
    melhor_dia_txt = "—"
    if not por_dia.empty:
        d = por_dia.idxmax()
        melhor_dia_txt = f"{d.strftime('%d/%m')} · {brl(por_dia.max())}"

    st.markdown(
        f"<p class='titulo'>🌻 Painel de Atendimentos</p>"
        f"<p class='subtitulo'>{mes.strftime('%B/%Y').capitalize()} · ritmo de "
        f"{brl(media_diaria)}/dia</p>",
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Clientes atendidas", total_clientes)
    k2.metric("Faturamento no mes", brl(faturamento), delta)
    k3.metric("Projecao do mes", brl(projecao_mes))
    k4.metric("🏆 Melhor dia", melhor_dia_txt)
    k5.metric("💰 Ganho liquido (60%)", brl(ganho_liquido))
    k6.metric("🏠 % Suite House (40%)", brl(suite_house))

    st.write("")

    g1, g2, g3 = st.columns([1, 2, 1])

    with g1:
        st.markdown("### Meta do mes")
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(pct_meta, 1),
            number={"suffix": "%", "font": {"size": 34, "color": MARROM_ESC}},
            gauge={
                "axis": {"range": [0, max(100, pct_meta)], "tickcolor": MARROM},
                "bar": {"color": DOURADO},
                "bgcolor": "rgba(255,255,255,.4)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "#FFF0BF"},
                    {"range": [50, 100], "color": "#FFE08A"},
                ],
                "threshold": {"line": {"color": FOLHA_ESC, "width": 4},
                              "thickness": 0.85, "value": 100},
            },
        ))
        st.plotly_chart(layout_plotly(gauge, 280), use_container_width=True,
                        config={"displayModeBar": False})
        faltam = max(meta - faturamento, 0)

        st.markdown(
            f"""
            <div style="
                background-color:#5C4033;
                color:#FFF8B0;
                padding:12px;
                border-radius:10px;
                font-size:16px;
                font-weight:600;
                text-align:center;
            ">
                🎯 Faltam {brl(faltam)} para atingir a meta de {brl(meta)}
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with g2:
        st.markdown("### Receita acumulada no mes")
        if not por_dia.empty:
            acum = por_dia.cumsum().reset_index()
            acum.columns = ["data", "acumulado"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=acum["data"], y=acum["acumulado"], mode="lines+markers",
                line=dict(color=DOURADO, width=3), fill="tozeroy",
                fillcolor="rgba(253,184,19,.30)", name="Acumulado",
            ))
            fig.add_hline(y=meta, line_dash="dash", line_color=FOLHA_ESC,
                          annotation_text="Meta", annotation_font_color=FOLHA_ESC)
            st.plotly_chart(layout_plotly(fig, 280), use_container_width=True,
                            config={"displayModeBar": False})

    with g3:
        st.markdown("### Mix de servicos")
        por_tipo = dfm.groupby("tipo", as_index=False)["valor"].sum()
        if not por_tipo.empty:
            rosca = px.pie(por_tipo, names="tipo", values="valor", hole=0.55,
                           color_discrete_sequence=SEQ)
            rosca.update_traces(textinfo="percent+label", textfont_size=12,
                                textfont_color=MARROM_ESC,
                                insidetextfont_color=MARROM_ESC,
                                marker=dict(line=dict(color=CREME, width=1)))
            st.plotly_chart(layout_plotly(rosca, 280), use_container_width=True,
                            config={"displayModeBar": False})

    st.caption("🌻 Atualiza a cada 5 min. No celular, gire para o modo paisagem para ver tudo lado a lado.")

    # ----------------------------------------------------------
    # TABELA DE ATENDIMENTOS DO MES
    # ----------------------------------------------------------
    st.write("")
    st.markdown("### 📋 Atendimentos do mes")

    # Prepara copia limpa para exibir
    dfm_tab = dfm[["data", "nome", "sexo", "idade", "tipo", "valor"]].copy()
    dfm_tab["data"] = dfm_tab["data"].dt.strftime("%d/%m/%Y")
    dfm_tab["valor_fmt"] = dfm_tab["valor"].apply(brl)

    # Filtros em linha
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        sexos = ["Todos"] + sorted(dfm_tab["sexo"].dropna().unique().tolist())
        f_sexo = st.selectbox("Sexo", sexos, key="tab_sexo")
    with fc2:
        idades = ["Todos"] + sorted(dfm_tab["idade"].dropna().unique().tolist())
        f_idade = st.selectbox("Faixa etaria", idades, key="tab_idade")
    with fc3:
        tipos = ["Todos"] + sorted(dfm_tab["tipo"].dropna().unique().tolist())
        f_tipo = st.selectbox("Tipo de servico", tipos, key="tab_tipo")
    with fc4:
        nomes = ["Todos"] + sorted(dfm_tab["nome"].dropna().unique().tolist())
        f_nome = st.selectbox("Cliente", nomes, key="tab_nome")

    # Aplica filtros
    df_filtrado = dfm_tab.copy()
    if f_sexo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["sexo"] == f_sexo]
    if f_idade != "Todos":
        df_filtrado = df_filtrado[df_filtrado["idade"] == f_idade]
    if f_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["tipo"] == f_tipo]
    if f_nome != "Todos":
        df_filtrado = df_filtrado[df_filtrado["nome"] == f_nome]

    df_exibir = df_filtrado[["data", "nome", "sexo", "idade", "tipo", "valor_fmt"]].rename(columns={
        "data": "Data",
        "nome": "Cliente",
        "sexo": "Sexo",
        "idade": "Faixa Etaria",
        "tipo": "Servico",
        "valor_fmt": "Valor",
    }).reset_index(drop=True)

    total_filtrado = df_filtrado["valor"].sum()
    n_filtrado = len(df_filtrado)

    # CSS da tabela girassol
    st.markdown(
        f"""
        <style>
        .tabela-girassol {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Poppins', sans-serif;
            font-size: 0.88rem;
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 6px 18px rgba(122,75,30,.15);
        }}
        .tabela-girassol thead tr {{
            background: linear-gradient(90deg, {DOURADO} 0%, {AMARELO} 100%);
            color: {MARROM_ESC};
        }}
        .tabela-girassol thead th {{
            padding: 10px 14px;
            text-align: left;
            font-weight: 700;
            letter-spacing: .03em;
        }}
        .tabela-girassol tbody tr:nth-child(odd) {{
            background: {CREME};
        }}
        .tabela-girassol tbody tr:nth-child(even) {{
            background: #FFF1C2;
        }}
        .tabela-girassol tbody tr:hover {{
            background: #FFE08A;
            transition: background .15s;
        }}
        .tabela-girassol tbody td {{
            padding: 8px 14px;
            color: {MARROM_ESC};
            border-bottom: 1px solid rgba(244,161,0,.25);
        }}
        .tabela-girassol tfoot tr {{
            background: linear-gradient(90deg, {MARROM} 0%, {MARROM_ESC} 100%);
            color: {AMARELO};
            font-weight: 700;
        }}
        .tabela-girassol tfoot td {{
            padding: 9px 14px;
            color: {AMARELO};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Monta HTML da tabela
    cabecalho = "".join(f"<th>{col}</th>" for col in df_exibir.columns)
    linhas = ""
    for _, row in df_exibir.iterrows():
        linhas += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values) + "</tr>"

    rodape = (
        f"<tr><td colspan='5'><b>Total ({n_filtrado} atendimento{'s' if n_filtrado != 1 else ''})</b></td>"
        f"<td><b>{brl(total_filtrado)}</b></td></tr>"
    )

    html_tabela = f"""
    <table class="tabela-girassol">
        <thead><tr>{cabecalho}</tr></thead>
        <tbody>{linhas}</tbody>
        <tfoot>{rodape}</tfoot>
    </table>
    """

    if df_exibir.empty:
        st.info("Nenhum atendimento encontrado para os filtros selecionados.")
    else:
        st.markdown(html_tabela, unsafe_allow_html=True)

    st.write("")

# ============================================================
# ABA ANUAL
# ============================================================
else:
    dfa = df[df["data"].dt.year == ano_sel].copy()

    st.markdown(
        f"<p class='titulo'>🌻 Visao Anual — {ano_sel}</p>"
        f"<p class='subtitulo'>Panorama completo do ano</p>",
        unsafe_allow_html=True,
    )

    if dfa.empty:
        st.warning("Sem dados para o ano selecionado.")
        st.stop()

    fat_anual = dfa["valor"].sum()
    clientes_anual = len(dfa)
    meses_com_dados = dfa["data"].dt.to_period("M").nunique()
    media_mes = fat_anual / meses_com_dados if meses_com_dados else 0
    pct_meta_anual = (fat_anual / meta_anual * 100) if meta_anual else 0

    # Anualiza pelo mes corrente do ano selecionado (meses ja decorridos)
    mes_atual_do_ano = date.today().month if ano_sel == date.today().year else 12
    anualizada_proj = (fat_anual / mes_atual_do_ano) * 12
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Clientes no ano", clientes_anual)
    k2.metric("Faturamento anual", brl(fat_anual))
    k3.metric("Receita anualizada", brl(anualizada_proj))
    k4.metric("Media mensal", brl(media_mes))
    k5.metric("% Meta anual", f"{pct_meta_anual:.1f}%")

    st.write("")

    r1a, r1b = st.columns(2)

    with r1a:
        st.markdown("### Faturamento por mes")
        fat_mes = (dfa.groupby(dfa["data"].dt.to_period("M"))["valor"]
                   .sum().reset_index())
        fat_mes["mes_label"] = fat_mes["data"].dt.strftime("%b/%y")
        fig_fat = px.bar(fat_mes, x="mes_label", y="valor",
                         color_discrete_sequence=[DOURADO])
        fig_fat.add_hline(y=meta_anual / 12, line_dash="dash", line_color=FOLHA_ESC,
                          annotation_text="Meta mensal", annotation_font_color=FOLHA_ESC)
        fig_fat.update_traces(marker_line_color=MARROM, marker_line_width=1,
                              text=fat_mes["valor"].apply(brl), textposition="outside",
                              textfont=dict(color="#2C1A08", size=11))
        st.plotly_chart(layout_plotly(fig_fat, 300), use_container_width=True,
                        config={"displayModeBar": False})

    with r1b:
        st.markdown("### Atendimentos por mes")
        atend_mes = (dfa.groupby(dfa["data"].dt.to_period("M"))
                     .size().reset_index(name="atendimentos"))
        atend_mes["mes_label"] = atend_mes["data"].dt.strftime("%b/%y")
        fig_atend = px.bar(atend_mes, x="mes_label", y="atendimentos",
                           color_discrete_sequence=[AMBAR])
        fig_atend.update_traces(marker_line_color=MARROM, marker_line_width=1,
                                text=atend_mes["atendimentos"], textposition="outside",
                                textfont=dict(color="#2C1A08", size=11))
        st.plotly_chart(layout_plotly(fig_atend, 300), use_container_width=True,
                        config={"displayModeBar": False})

    st.write("")

    r2a, r2b = st.columns(2)

    with r2a:
        st.markdown("### Atendimentos por dia da semana")
        dfa["dia_sem"] = dfa["data"].dt.dayofweek
        dsem = dfa.groupby("dia_sem").size().reset_index(name="atendimentos")
        dsem["dia_label"] = dsem["dia_sem"].map(lambda x: DIAS_SEMANA[x])
        fig_dsem = px.bar(dsem, x="dia_label", y="atendimentos",
                          color_discrete_sequence=[DOURADO])
        fig_dsem.update_traces(marker_line_color=MARROM, marker_line_width=1,
                              text=dsem["atendimentos"], textposition="outside",
                              textfont=dict(color="#2C1A08", size=11))
        st.plotly_chart(layout_plotly(fig_dsem, 300), use_container_width=True,
                        config={"displayModeBar": False})

    with r2b:
        st.markdown("### Faturamento por tipo de servico")
        fat_tipo = (dfa.groupby("tipo")["valor"]
                    .sum().reset_index().sort_values("valor", ascending=True))
        fig_fat_tipo = px.bar(fat_tipo, x="valor", y="tipo", orientation="h",
                              color_discrete_sequence=[MARROM])
        fig_fat_tipo.update_traces(marker_line_color=MARROM_ESC, marker_line_width=1,
                                   text=fat_tipo["valor"].apply(brl), textposition="outside",
                                   textfont=dict(color="#2C1A08", size=11))
        st.plotly_chart(layout_plotly(fig_fat_tipo, 300), use_container_width=True,
                        config={"displayModeBar": False})

    st.write("")

    r3a, r3b = st.columns([2, 1])

    with r3a:
        st.markdown("### Faturamento por servico ao longo do ano")
        fat_tipo_mes = (dfa.groupby([dfa["data"].dt.to_period("M"), "tipo"])["valor"]
                        .sum().reset_index())
        fat_tipo_mes["mes_label"] = fat_tipo_mes["data"].dt.strftime("%b/%y")
        fig_stk = px.bar(fat_tipo_mes, x="mes_label", y="valor", color="tipo",
                         barmode="stack", color_discrete_sequence=SEQ)
        fig_stk.update_traces(marker_line_color=CREME, marker_line_width=0.5,
                              texttemplate="%{value:,.0f}", textposition="inside",
                              textfont=dict(color=CREME, size=10))
        st.plotly_chart(layout_plotly(fig_stk, 300), use_container_width=True,
                        config={"displayModeBar": False})

    with r3b:
        st.markdown("### Mix anual de servicos")
        mix_anual = dfa.groupby("tipo", as_index=False)["valor"].sum()
        rosca_anual = px.pie(mix_anual, names="tipo", values="valor", hole=0.55,
                             color_discrete_sequence=SEQ)
        rosca_anual.update_traces(textinfo="label+value", textfont_size=12,
                                  textfont_color=MARROM_ESC,
                                  insidetextfont_color=MARROM_ESC,
                                  marker=dict(line=dict(color=CREME, width=1)))
        st.plotly_chart(layout_plotly(rosca_anual, 300), use_container_width=True,
                        config={"displayModeBar": False})

    st.caption("🌻 Visao consolidada do ano. Use o filtro na barra lateral para trocar o ano.")
