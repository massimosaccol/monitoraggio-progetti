import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Monitoraggio Progetti",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_main_data(uploaded_file):
  df = None
  if uploaded_file is not None:
    try:
      df = pd.read_csv(
          uploaded_file, encoding="utf-8-sig", sep=None, engine="python"
      )
    except Exception:
      uploaded_file.seek(0)
      df = pd.read_csv(
          uploaded_file,
          encoding="utf-8-sig",
          sep=";",
          engine="python",
          on_bad_lines="skip",
      )
  else:
    file_name = "Vista Monitoraggio Progetti.csv"
    if os.path.exists(file_name):
      try:
        df = pd.read_csv(
            file_name, encoding="utf-8-sig", sep=None, engine="python"
        )
      except Exception:
        df = pd.read_csv(
            file_name,
            encoding="utf-8-sig",
            sep=";",
            engine="python",
            on_bad_lines="skip",
        )

  if df is None or df.empty:
    return None

  df.columns = df.columns.str.strip().str.replace("\ufeff", "")

  for c in ["Codice Commessa", "Codice Progetto", "Codice Azione"]:
    if c in df.columns:
      df[c] = (
          df[c]
          .astype(str)
          .str.replace(".0", "", regex=False)
          .str.strip()
      )

  numeric_cols = [
      "Ore",
      "Pianificato",
      "Erogato",
      "Partecipanti Attesi",
      "Partecipanti Finali",
      "Costo Standard 1",
      "Costo Standard 2",
      "Budget",
      "Ore Finali",
      "Totale rendicontato",
      "Decurtazione",
  ]
  for col in numeric_cols:
    if col in df.columns:
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

  return df


@st.cache_data
def load_ore_mese_data(uploaded_ore_file):
  df_ore = None
  if uploaded_ore_file is not None:
    try:
      df_ore = pd.read_csv(
          uploaded_ore_file, encoding="utf-8-sig", sep=None, engine="python"
      )
    except Exception:
      uploaded_ore_file.seek(0)
      df_ore = pd.read_csv(
          uploaded_ore_file,
          encoding="utf-8-sig",
          sep=";",
          engine="python",
          on_bad_lines="skip",
      )
  else:
    file_name = "Ore_Mese_Modulo.csv"
    if os.path.exists(file_name):
      try:
        df_ore = pd.read_csv(
            file_name, encoding="utf-8-sig", sep=None, engine="python"
        )
      except Exception:
        df_ore = pd.read_csv(
            file_name,
            encoding="utf-8-sig",
            sep=";",
            engine="python",
            on_bad_lines="skip",
        )

  if df_ore is not None and not df_ore.empty:
    df_ore.columns = df_ore.columns.str.strip().str.replace("\ufeff", "")

    if "le_codcorso" in df_ore.columns:
      df_ore["le_codcorso"] = (
          df_ore["le_codcorso"]
          .astype(str)
          .str.replace(".0", "", regex=False)
          .str.strip()
      )
    if "le_codmod" in df_ore.columns:
      df_ore["le_codmod"] = (
          df_ore["le_codmod"]
          .astype(str)
          .str.replace(".0", "", regex=False)
          .str.strip()
      )
    if "HH_MESE" in df_ore.columns:
      df_ore["HH_MESE"] = pd.to_numeric(
          df_ore["HH_MESE"], errors="coerce"
      ).fillna(0)

  return df_ore


# --- SIDEBAR ---
st.sidebar.title("🛠️ Selezione Progetto")
uploaded_file = st.sidebar.file_uploader(
    "1. Carica CSV Monitoraggio", type=["csv"], key="main_csv"
)
uploaded_ore_file = st.sidebar.file_uploader(
    "2. Carica CSV Ore Mese Modulo", type=["csv"], key="ore_csv"
)

df_raw = load_main_data(uploaded_file)
df_ore_raw = load_ore_mese_data(uploaded_ore_file)

if df_raw is not None and not df_raw.empty:
  commesse = (
      df_raw["Codice Commessa"].dropna().unique().tolist()
      if "Codice Commessa" in df_raw.columns
      else []
  )

  if commesse:
    selected_commessa = st.sidebar.selectbox(
        "Seleziona Progetto/Commessa", commesse
    )
    df_proj = df_raw[df_raw["Codice Commessa"] == selected_commessa].copy()
  else:
    df_proj = df_raw.copy()

  # --- HEADER MONITORAGGIO PROGETTO ---
  st.title("📌 Vista Monitoraggio Progetto")

  titolo_comm = (
      df_proj["Titolo"].iloc[0]
      if "Titolo" in df_proj.columns and not df_proj.empty
      else ""
  )
  st.markdown(f"### **Commessa:** {selected_commessa} — *{titolo_comm}*")

  st.divider()

  # --- KPI TOP BAR ---
  k1, k2, k3, k4, k5, k6 = st.columns(6)

  tot_azioni = len(df_proj)
  tot_ore_prev = df_proj["Ore"].sum() if "Ore" in df_proj.columns else 0
  tot_ore_fin = (
      df_proj["Ore Finali"].sum() if "Ore Finali" in df_proj.columns else 0
  )
  tot_budget = df_proj["Budget"].sum() if "Budget" in df_proj.columns else 0
  tot_rendicontato = (
      df_proj["Totale rendicontato"].sum()
      if "Totale rendicontato" in df_proj.columns
      else 0
  )
  tot_decurtazione = (
      df_proj["Decurtazione"].sum()
      if "Decurtazione" in df_proj.columns
      else 0
  )

  k1.metric("N. Azioni", f"{tot_azioni}")
  k2.metric("Ore Previste", f"{tot_ore_prev:,.0f}".replace(",", "."))
  k3.metric("Ore Finali", f"{tot_ore_fin:,.0f}".replace(",", "."))
  k4.metric(
      "Budget Totale",
      f"€ {tot_budget:,.2f}".replace(",", "X")
      .replace(".", ",")
      .replace("X", "."),
  )
  k5.metric(
      "Rendicontato",
      f"€ {tot_rendicontato:,.2f}".replace(",", "X")
      .replace(".", ",")
      .replace("X", "."),
  )
  k6.metric(
      "Decurtazione",
      f"€ {tot_decurtazione:,.2f}".replace(",", "X")
      .replace(".", ",")
      .replace("X", "."),
  )

  st.divider()

  # --- TABS ---
  tab1, tab2, tab3 = st.tabs([
      "📋 Stato Avanzamento Progetto",
      "📊 Grafici Avanzamento",
      "📅 Distribuzione Mensile Rendiconto",
  ])

  with tab1:
    st.subheader("Dettaglio Azioni")

    cols_excel_mapping = {
        "Codice Azione": "COD. AZIONE",
        "Descrizione Azione": "DESCRIZIONE AZIONE",
        "ID Azione (FIMA-A39)": "ID AZIONE",
        "HUB": "HUB",
        "Riferimento - Note": "AZIENDA",
        "Partecipanti Attesi": "PART. PREVISTI",
        "Ore": "ORE",
        "Pianificato": "PIANIFICATO",
        "Erogato": "EROGATO",
        "Stato azione": "STATO",
        "Data Inizio": "DATA INIZIO",
        "Data Fine": "DATA FINE",
        "Costo Standard 1": "COSTO STD 1",
        "Costo Standard 2": "COSTO STD 2",
        "Budget": "BUDGET",
        "Ore Finali": "ORE FINALI",
        "Partecipanti Finali": "PART. FINALI",
        "Totale rendicontato": "TOT. RENDICONTATO",
        "Decurtazione": "DECURTAZIONE",
    }

    cols_exist = [c for c in cols_excel_mapping.keys() if c in df_proj.columns]
    df_disp = df_proj[cols_exist].rename(columns=cols_excel_mapping).copy()

    df_out = pd.DataFrame()

    for col in df_disp.columns:
      if col in [
          "COD. AZIONE",
          "ORE",
          "ORE FINALI",
          "PART. PREVISTI",
          "PART. FINALI",
      ]:
        df_out[col] = df_disp[col].apply(
            lambda x: f"{int(x)}"
            if pd.notnull(x) and str(x).replace(".", "").isdigit()
            else ("" if pd.isnull(x) else str(x))
        )
      elif col in ["PIANIFICATO", "EROGATO"]:
        df_out[col] = df_disp[col].apply(
            lambda x: f"{x:.0f}%" if pd.notnull(x) else ""
        )
      elif col in [
          "COSTO STD 1",
          "COSTO STD 2",
          "BUDGET",
          "TOT. RENDICONTATO",
          "DECURTAZIONE",
      ]:
        df_out[col] = df_disp[col].apply(
            lambda x: f"€ {x:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
            if pd.notnull(x)
            else "€ 0,00"
        )
      elif col in ["DATA INIZIO", "DATA FINE"]:
        df_out[col] = (
            pd.to_datetime(df_disp[col], errors="coerce")
            .dt.strftime("%d/%m/%Y")
            .fillna("")
        )
      else:
        df_out[col] = df_disp[col].astype(str).replace("nan", "").fillna("")

    st.dataframe(
        df_out,
        use_container_width=True,
        hide_index=True,
        height=550,
    )

  with tab2:
    col_g1, col_g2 = st.columns(2)

    with col_g1:
      st.subheader("Budget vs Rendicontato per Azione")
      if (
          "Descrizione Azione" in df_proj.columns
          and "Budget" in df_proj.columns
      ):
        fig_b = px.bar(
            df_proj,
            x="Descrizione Azione",
            y=["Budget", "Totale rendicontato"],
            barmode="group",
            labels={"value": "Euro (€)", "variable": "Voce"},
            color_discrete_map={
                "Budget": "#2b5c8f",
                "Totale rendicontato": "#2ca02c",
            },
        )
        fig_b.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_b, use_container_width=True)

    with col_g2:
      st.subheader("Stato Avanzamento Azioni")
      if "Stato azione" in df_proj.columns:
        fig_s = px.pie(
            df_proj,
            names="Stato azione",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_s, use_container_width=True)

  with tab3:
    st.subheader("Ripartizione Mensile dell'Importo Rendicontato")

    if df_ore_raw is not None and not df_ore_raw.empty:
      df_ore_proj = df_ore_raw[
          df_ore_raw["le_codcorso"] == str(selected_commessa)
      ].copy()

      if not df_ore_proj.empty:
        tot_hh_mod = (
            df_ore_proj.groupby("le_codmod")["HH_MESE"]
            .sum()
            .reset_index()
            .rename(columns={"HH_MESE": "TOT_HH_MOD"})
        )

        df_dist = pd.merge(df_ore_proj, tot_hh_mod, on="le_codmod")

        df_dist = pd.merge(
            df_dist,
            df_proj[
                ["Codice Azione", "Descrizione Azione", "Totale rendicontato"]
            ],
            left_on="le_codmod",
            right_on="Codice Azione",
            how="inner",
        )

        df_dist["RENDICONTO_MESE"] = df_dist["Totale rendicontato"] * (
            df_dist["HH_MESE"] / df_dist["TOT_HH_MOD"].replace(0, 1)
        )

        pivot_rend = df_dist.pivot_table(
            index=["Codice Azione", "Descrizione Azione"],
            columns="DATA",
            values="RENDICONTO_MESE",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()

        month_cols = [c for c in pivot_rend.columns if c not in [
            "Codice Azione",
            "Descrizione Azione",
        ]]
        month_cols = sorted(month_cols)

        pivot_rend["TOTALE RENDICONTATO"] = pivot_rend[month_cols].sum(axis=1)

        df_rend_disp = pd.DataFrame()
        df_rend_disp["COD. AZIONE"] = pivot_rend["Codice Azione"]
        df_rend_disp["DESCRIZIONE AZIONE"] = pivot_rend["Descrizione Azione"]

        for m in month_cols:
          df_rend_disp[m] = pivot_rend[m].apply(
              lambda x: f"€ {x:,.2f}".replace(",", "X")
              .replace(".", ",")
              .replace("X", ".")
          )

        df_rend_disp["TOT. RENDICONTATO"] = pivot_rend[
            "TOTALE RENDICONTATO"
        ].apply(
            lambda x: f"€ {x:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        tot_row = {
            "COD. AZIONE": "TOTALE",
            "DESCRIZIONE AZIONE": "Totale Progetto",
        }
        for m in month_cols:
          tot_m = pivot_rend[m].sum()
          tot_row[m] = (
              f"€ {tot_m:,.2f}".replace(",", "X")
              .replace(".", ",")
              .replace("X", ".")
          )

        tot_gen = pivot_rend["TOTALE RENDICONTATO"].sum()
        tot_row["TOT. RENDICONTATO"] = (
            f"€ {tot_gen:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        df_rend_disp = pd.concat(
            [df_rend_disp, pd.DataFrame([tot_row])], ignore_index=True
        )

        st.dataframe(
            df_rend_disp,
            use_container_width=True,
            hide_index=True,
            height=500,
        )

        st.markdown("#### **Andamento Mensile Rendicontato (€)**")
        df_chart_monthly = (
            df_dist.groupby("DATA")["RENDICONTO_MESE"].sum().reset_index()
        )
        fig_m = px.bar(
            df_chart_monthly,
            x="DATA",
            y="RENDICONTO_MESE",
            text_auto=".2f",
            labels={"DATA": "Mese", "RENDICONTO_MESE": "Importo (€)"},
            color_discrete_sequence=["#1f77b4"],
        )
        st.plotly_chart(fig_m, use_container_width=True)

      else:
        st.info(
            "Nessun dato sulle ore mensili trovato per la commessa selezionata"
            f" ({selected_commessa})."
        )
    else:
      st.warning(
          "⚠️ File 'Ore_Mese_Modulo.csv' non trovato o non caricato. Caricalo"
          " dalla sidebar per abilitare la vista mensile."
      )

else:
  st.error(
      "⚠️ Carica il file CSV dalla sidebar o verifica che il file 'Vista"
      " Monitoraggio Progetti.csv' sia presente nella cartella principale."
  )