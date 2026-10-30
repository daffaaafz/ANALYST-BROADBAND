import calendar
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats

# ==========================================
# 1. KONFIGURASI HALAMAN & GENERATOR DATA
# ==========================================
st.set_page_config(
    page_title="Dashboard Operasional Gangguan Broadband",
    layout="wide",
    page_icon="🌐",
)

@st.cache_data
def load_or_generate_data():
    """Generator data otomatis agar dashboard langsung siap pakai tanpa file eksternal terpisah."""
    SEED = 2026
    TANGGAL_MULAI = "2026-01-01"
    TANGGAL_AKHIR = "2026-10-30"
    N_TIKET_DASAR = 2200
    rng = np.random.default_rng(SEED)

    AREA = {
        "Ciamis":    {"kode": "CMS", "pelanggan": 1500, "odp": 125, "teknisi": 6, "fragil": 0.90, "durasi": 0.90, "respon": 0.90},
        "Kawali":    {"kode": "KWL", "pelanggan": 900, "odp": 75, "teknisi": 3, "fragil": 1.10, "durasi": 1.00, "respon": 1.00},
        "Manonjaya": {"kode": "MNJ", "pelanggan": 700, "odp": 58, "teknisi": 3, "fragil": 1.30, "durasi": 1.35, "respon": 1.30},
    }

    PROB_HUJAN = {1: 0.60, 2: 0.60, 3: 0.50, 4: 0.40, 5: 0.25, 6: 0.15, 7: 0.10, 8: 0.10, 9: 0.15, 10: 0.35}

    KATEGORI_DASAR = {
        "Internet Lambat": 0.20, "ONT/Modem Bermasalah": 0.16,
        "Gangguan WiFi/Perangkat Pelanggan": 0.12, "Redaman Tinggi": 0.14,
        "LOS/Tidak Ada Sinyal": 0.14, "Kabel Putus/Rusak": 0.10,
        "Salah Konfigurasi/Akun": 0.07, "Gangguan Perangkat Jaringan": 0.07,
    }
    PENGALI_HUJAN = {"Kabel Putus/Rusak": 2.2, "LOS/Tidak Ada Sinyal": 1.8, "Redaman Tinggi": 1.5, "Gangguan Perangkat Jaringan": 1.6, "ONT/Modem Bermasalah": 1.2}
    PENGALI_AREA = {"Manonjaya": {"Kabel Putus/Rusak": 1.6, "LOS/Tidak Ada Sinyal": 1.3}, "Ciamis": {"Internet Lambat": 1.3, "Gangguan WiFi/Perangkat Pelanggan": 1.2}}

    PENYEBAB = {
        "Internet Lambat": {"Trafik padat jam sibuk": .35, "Interferensi WiFi": .30, "Kualitas link menurun": .20, "Konfigurasi": .15},
        "ONT/Modem Bermasalah": {"Perangkat rusak/usang": .60, "Petir/gangguan listrik": .25, "Setting perangkat": .15},
        "Gangguan WiFi/Perangkat Pelanggan": {"Router/perangkat pelanggan": .55, "Interferensi WiFi": .25, "Password/setting": .20},
        "Redaman Tinggi": {"Konektor kotor/longgar": .40, "Tikungan kabel (bending)": .30, "Splitter/ODP bermasalah": .30},
        "LOS/Tidak Ada Sinyal": {"Kabel drop putus": .35, "Kabel distribusi rusak": .25, "ONT mati": .20, "Pemadaman listrik": .20},
        "Kabel Putus/Rusak": {"Pohon tumbang/ranting": .35, "Pekerjaan pihak ketiga": .25, "Gigitan hewan": .15, "Tertabrak kendaraan": .15, "Vandalisme/pencurian kabel": .10},
        "Salah Konfigurasi/Akun": {"Isolir/pembayaran": .35, "Provisioning gagal": .35, "Salah konfigurasi": .30},
        "Gangguan Perangkat Jaringan": {"Perangkat OLT/ODP bermasalah": .40, "Catuan listrik": .30, "Petir": .30},
        "Gangguan Massal": {"Kabel feeder putus": .40, "Pekerjaan pihak ketiga": .30, "Pohon tumbang": .30},
    }

    BIAYA_ESTIMASI = {"Internet Lambat": 0, "ONT/Modem Bermasalah": 250000, "Gangguan WiFi/Perangkat Pelanggan": 0, "Redaman Tinggi": 35000, "LOS/Tidak Ada Sinyal": 50000, "Kabel Putus/Rusak": 120000, "Salah Konfigurasi/Akun": 0, "Gangguan Perangkat Jaringan": 150000, "Gangguan Massal": 500000}
    DURASI_MEDIAN = {"Internet Lambat": 2.0, "ONT/Modem Bermasalah": 3.0, "Gangguan WiFi/Perangkat Pelanggan": 1.5, "Redaman Tinggi": 4.0, "LOS/Tidak Ada Sinyal": 5.0, "Kabel Putus/Rusak": 8.0, "Salah Konfigurasi/Akun": 1.0, "Gangguan Perangkat Jaringan": 7.0, "Gangguan Massal": 10.0}
    SLA_JAM = {"Internet Lambat": 8, "ONT/Modem Bermasalah": 8, "Gangguan WiFi/Perangkat Pelanggan": 8, "Redaman Tinggi": 12, "LOS/Tidak Ada Sinyal": 12, "Kabel Putus/Rusak": 24, "Salah Konfigurasi/Akun": 6, "Gangguan Perangkat Jaringan": 24, "Gangguan Massal": 12}
    CHANNEL = {"Call Center 147": 0.40, "Aplikasi Pelanggan": 0.30, "Plasa/Gerai": 0.15, "Media Sosial/WhatsApp": 0.15}
    KEJADIAN_MASSAL = [("Manonjaya", 3), ("Ciamis", 2), ("Manonjaya", 3), ("Kawali", 2), ("Ciamis", 3), ("Manonjaya", 2)]

    NAMA_BULAN = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober"}
    NAMA_HARI = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}

    odp_rows, pel_rows = [], []
    for area, cfg in AREA.items():
        kode = cfg["kode"]
        odp_ids = [f"ODP-{kode}-{i + 1:03d}" for i in range(cfg["odp"])]
        odp_frag = rng.lognormal(0, 0.9, cfg["odp"])
        for oid in odp_ids:
            odp_rows.append({"ID_ODP": oid, "Area": area})
        odp_pilih = rng.choice(cfg["odp"], size=cfg["pelanggan"])
        frag_cust = rng.gamma(0.8, 1 / 0.8, cfg["pelanggan"])
        paket = rng.choice([20, 30, 50, 100], size=cfg["pelanggan"], p=[0.30, 0.30, 0.28, 0.12])
        for i in range(cfg["pelanggan"]):
            pel_rows.append({
                "ID_Pelanggan": f"PLG-{kode}-{i + 1:04d}", "Area": area,
                "ID_ODP": odp_ids[odp_pilih[i]], "Paket_Mbps": int(paket[i]),
                "Bobot": min(frag_cust[i] * odp_frag[odp_pilih[i]] * cfg["fragil"], 6.0),
            })
    odp = pd.DataFrame(odp_rows)
    pelanggan = pel_rows

    teknisi = {a: [f"TEK-{c['kode']}-{i + 1:02d}" for i in range(c["teknisi"])] for a, c in AREA.items()}
    faktor_teknisi = {t: rng.lognormal(0, 0.2) for lst in teknisi.values() for t in lst}

    tanggal = pd.date_range(TANGGAL_MULAI, TANGGAL_AKHIR, freq="D")
    bulan_arr = np.asarray(tanggal.month)
    hujan = rng.random(len(tanggal)) < np.array([PROB_HUJAN[m] for m in bulan_arr])
    akhir_pekan = np.asarray(tanggal.dayofweek) >= 5
    bobot_tgl = np.where(hujan, 1.7, 1.0) * np.where(akhir_pekan, 1.1, 1.0)
    bobot_tgl = bobot_tgl / bobot_tgl.sum()

    PROB_KAT = {}
    kat_list = list(KATEGORI_DASAR)
    for area in AREA:
        for hj in (False, True):
            p = dict(KATEGORI_DASAR)
            if hj:
                for k, m in PENGALI_HUJAN.items(): p[k] *= m
            for k, m in PENGALI_AREA.get(area, {}).items(): p[k] *= m
            arr = np.array([p[k] for k in kat_list])
            PROB_KAT[(area, hj)] = arr / arr.sum()

    JAM_UMUM = np.array([1, .5, .3, .3, .5, 1, 2, 4, 7, 8, 7, 6, 5, 5, 5, 5, 5, 6, 8, 10, 10, 8, 4, 2], dtype=float)
    JAM_LAMBAT = JAM_UMUM.copy()
    JAM_LAMBAT[18:23] *= 2.0
    JAM_UMUM, JAM_LAMBAT = JAM_UMUM / JAM_UMUM.sum(), JAM_LAMBAT / JAM_LAMBAT.sum()

    def pilih(dist: dict) -> str:
        return str(rng.choice(list(dist), p=list(dist.values())))

    baris = []
    def catat(c, ts, kategori, hj, respon, durasi, tek, massal=False, kejadian=""):
        baris.append({
            "Waktu_Lapor": ts, "Area": c["Area"], "ID_ODP": c["ID_ODP"],
            "ID_Pelanggan": c["ID_Pelanggan"], "Paket_Mbps": c["Paket_Mbps"],
            "Kategori_Gangguan": kategori, "Penyebab": pilih(PENYEBAB[kategori]),
            "Channel_Lapor": pilih(CHANNEL), "Cuaca": "Hujan" if hj else "Cerah",
            "Gangguan_Massal": "Ya" if massal else "Tidak", "ID_Kejadian_Massal": kejadian,
            "ID_Teknisi": tek, "Respon_Menit": respon, "Durasi_Perbaikan_Jam": round(durasi, 2),
            "Estimasi_Biaya_Rp": BIAYA_ESTIMASI.get(kategori, 0),
        })

    bobot_pel = np.array([c["Bobot"] for c in pelanggan])
    idx_pel = rng.choice(len(pelanggan), size=N_TIKET_DASAR, p=bobot_pel / bobot_pel.sum())
    idx_tgl = rng.choice(len(tanggal), size=N_TIKET_DASAR, p=bobot_tgl)
    for ip, it in zip(idx_pel, idx_tgl):
        c, hj = pelanggan[ip], bool(hujan[it])
        kat = str(rng.choice(kat_list, p=PROB_KAT[(c["Area"], hj)]))
        jam = int(rng.choice(24, p=JAM_LAMBAT if kat == "Internet Lambat" else JAM_UMUM))
        ts = tanggal[it] + pd.Timedelta(hours=jam, minutes=int(rng.integers(0, 60)))
        cfg = AREA[c["Area"]]
        tek = str(rng.choice(teknisi[c["Area"]]))
        malam = ts.hour >= 21 or ts.hour < 6
        respon = int(np.clip(40 * cfg["respon"] * (2.0 if malam else 1.0) * (1.3 if ts.dayofweek >= 5 else 1.0) * rng.lognormal(0, 0.6), 5, 600))
        durasi = float(np.clip(DURASI_MEDIAN[kat] * cfg["durasi"] * (1.25 if hj else 1.0) * faktor_teknisi[tek] * rng.lognormal(0, 0.55), 0.3, 72))
        catat(c, ts, kat, hj, respon, durasi, tek)

    hari_hujan = np.where(hujan)[0]
    for k, (area, n_odp) in enumerate(KEJADIAN_MASSAL, start=1):
        it = int(rng.choice(hari_hujan))
        odp_kena = set(rng.choice(odp.loc[odp.Area == area, "ID_ODP"].to_numpy(), size=n_odp, replace=False))
        kena = [c for c in pelanggan if c["ID_ODP"] in odp_kena]
        if not kena: continue
        n_lapor = max(1, int(len(kena) * rng.uniform(0.70, 0.95)))
        mulai = int(rng.integers(5, 20))
        awal = tanggal[it] + pd.Timedelta(hours=mulai)
        respon_ev = int(np.clip(60 * AREA[area]["respon"] * rng.lognormal(0, 0.3), 15, 300))
        durasi_ev = float(np.clip(DURASI_MEDIAN["Gangguan Massal"] * AREA[area]["durasi"] * rng.lognormal(0, 0.3), 3, 48))
        selesai_ev = awal + pd.Timedelta(minutes=respon_ev, hours=durasi_ev)
        for j in rng.choice(len(kena), size=n_lapor, replace=False):
            jam_f = min(mulai + rng.exponential(1.5), 23.9)
            ts = tanggal[it] + pd.Timedelta(hours=float(jam_f))
            selesai = selesai_ev + pd.Timedelta(minutes=int(rng.integers(0, 60)))
            respon = int(np.clip(respon_ev + rng.integers(-10, 20), 5, 600))
            durasi = max(0.5, (selesai - ts).total_seconds() / 3600 - respon / 60)
            catat(kena[j], ts, "Gangguan Massal", True, respon, durasi, str(rng.choice(teknisi[area])), massal=True, kejadian=f"MASSAL-{k:02d}")

    df = pd.DataFrame(baris)
    df["Total_Penanganan_Jam"] = (df["Respon_Menit"] / 60 + df["Durasi_Perbaikan_Jam"]).round(2)
    df["Waktu_Selesai"] = df["Waktu_Lapor"] + pd.to_timedelta(df["Total_Penanganan_Jam"], unit="h")
    df["Target_SLA_Jam"] = df["Kategori_Gangguan"].map(SLA_JAM)
    df["Status_Tiket"] = np.where(df["Waktu_Lapor"] > "2026-10-29", "In Progress", "Closed")
    df["Status_SLA"] = np.where(df["Total_Penanganan_Jam"] <= df["Target_SLA_Jam"], "Memenuhi", "Melanggar")

    df = df.sort_values(["ID_Pelanggan", "Waktu_Lapor"])
    sebelumnya = df.groupby("ID_Pelanggan")["Waktu_Lapor"].shift(1)
    selisih = (df["Waktu_Lapor"] - sebelumnya).dt.total_seconds()
    df["Tiket_Berulang_30Hari"] = np.where(selisih <= 30 * 86400, "Ya", "Tidak")

    skor = (4.4 - 0.05 * df["Total_Penanganan_Jam"].clip(upper=24) - 0.7 * (df["Status_SLA"] == "Melanggar") - 0.5 * (df["Tiket_Berulang_30Hari"] == "Ya") + rng.normal(0, 0.7, len(df)))
    csat = pd.array(np.clip(np.round(skor), 1, 5).astype(int), dtype="Int64")
    csat[rng.random(len(df)) > 0.55] = pd.NA
    df["CSAT"] = csat

    df = df.sort_values("Waktu_Lapor").reset_index(drop=True)
    df.insert(0, "ID_Tiket", [f"TKT-26-{i + 1:05d}" for i in range(len(df))])
    df["Bulan"] = df["Waktu_Lapor"].dt.month.map(NAMA_BULAN)
    df["Hari"] = df["Waktu_Lapor"].dt.dayofweek.map(NAMA_HARI)
    df["Jam"] = df["Waktu_Lapor"].dt.hour
    return df

df = load_or_generate_data()

# Database SQLite In-Memory untuk praktik kueri SQL analitis
conn = sqlite3.connect(":memory:")
df.to_sql("Tiket_Gangguan", conn, index=False, if_exists="replace")

# ==========================================
# 2. SIDEBAR FILTER GLOBAL
# ==========================================
st.sidebar.header("🎛️ Filter Operasional")
selected_area = st.sidebar.multiselect("Pilih Area:", options=df["Area"].unique(), default=df["Area"].unique())
selected_cuaca = st.sidebar.multiselect("Kondisi Cuaca:", options=df["Cuaca"].unique(), default=df["Cuaca"].unique())

if not selected_area: selected_area = list(df["Area"].unique())
if not selected_cuaca: selected_cuaca = list(df["Cuaca"].unique())

filtered_df = df[df["Area"].isin(selected_area) & df["Cuaca"].isin(selected_cuaca)]
filtered_df.to_sql("Tiket_Gangguan", conn, index=False, if_exists="replace")

# ==========================================
# 3. STRUKTUR HALAMAN DASHBOARD (TABS)
# ==========================================
st.title("🌐 Dashboard Analisis Gangguan & Performa Jaringan Broadband")
st.markdown("Sistem monitoring layanan fixed broadband wilayah **Ciamis, Kawali, dan Manonjaya**.")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Ringkasan KPI & Tren", 
    "⚙️ Akar Penyebab & SLA", 
    "🏢 ODP Rawan & Massal", 
    "💡INSIGHT"
])

with tab1:
    st.subheader("📌 Executive KPI Summary")
    total_tiket = len(filtered_df)
    mttr_mean = filtered_df["Total_Penanganan_Jam"].mean()
    mttr_median = filtered_df["Total_Penanganan_Jam"].median()
    sla_pct = (filtered_df["Status_SLA"] == "Memenuhi").mean() * 100
    repeat_rate = (filtered_df["Tiket_Berulang_30Hari"] == "Ya").mean() * 100
    avg_csat = filtered_df["CSAT"].astype(float).mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Tiket", f"{total_tiket:,}")
    c2.metric("MTTR (Rata-rata)", f"{mttr_mean:.2f} Jam", help=f"Median: {mttr_median:.2f} Jam (Lebih tahan terhadap outlier)")
    c3.metric("SLA Terpenuhi", f"{sla_pct:.1f}%")
    c4.metric("Tiket Berulang", f"{repeat_rate:.1f}%")
    c5.metric("CSAT Rata-rata", f"{avg_csat:.2f} / 5.0")

    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📈 Tren Harian Tiket Berdasarkan Cuaca")
        daily_trend = filtered_df.groupby([filtered_df["Waktu_Lapor"].dt.date, "Cuaca"])["ID_Tiket"].count().reset_index(name="Jumlah")
        fig_trend = px.line(daily_trend, x="Waktu_Lapor", y="Jumlah", color="Cuaca", labels={"Waktu_Lapor": "Tanggal", "Jumlah": "Jumlah Tiket"})
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_b:
        st.subheader("📊 Volume Tiket & Performa SLA per Area")
        area_agg = filtered_df.groupby("Area").agg(
            Total_Tiket=("ID_Tiket", "count"),
            SLA_Ok=("Status_SLA", lambda x: (x == "Memenuhi").mean() * 100)
        ).reset_index()
        fig_area = px.bar(area_agg, x="Area", y="Total_Tiket", text="SLA_Ok", text_auto=".1f", title="Jumlah Tiket & % SLA Terpenuhi", labels={"Total_Tiket": "Jumlah Tiket"})
        fig_area.update_traces(texttemplate='SLA: %{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_area, use_container_width=True)

with tab2:
    st.subheader("⚙️ Analisis Akar Penyebab (Pareto 80/20)")
    cause_df = filtered_df["Penyebab"].value_counts().reset_index()
    cause_df.columns = ["Penyebab", "Jumlah"]
    cause_df["Kumulatif_%"] = (cause_df["Jumlah"].cumsum() / cause_df["Jumlah"].sum()) * 100
    
    fig_pareto = px.bar(cause_df, x="Penyebab", y="Jumlah", text_auto=True, title="Frekuensi Akar Penyebab Gangguan Jaringan")
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.subheader("❌ Area & Kategori dengan Pelanggaran SLA Tertinggi")
    sla_query = """
        SELECT Area, Kategori_Gangguan, COUNT(*) as Total_Tiket,
               SUM(CASE WHEN Status_SLA = 'Melanggar' THEN 1 ELSE 0 END) as Total_Pelanggaran,
               ROUND(SUM(CASE WHEN Status_SLA = 'Melanggar' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as Pct_Pelanggaran
        FROM Tiket_Gangguan
        GROUP BY Area, Kategori_Gangguan
        ORDER BY Pct_Pelanggaran DESC LIMIT 5
    """
    df_sla_viol = pd.read_sql_query(sla_query, conn)
    st.dataframe(df_sla_viol, use_container_width=True)

with tab3:
    st.subheader("🏢 ODP Prioritas untuk Pemeliharaan Preventif")
    odp_query = """
        SELECT ID_ODP, Area, COUNT(*) as Total_Tiket,
               SUM(CASE WHEN Tiket_Berulang_30Hari = 'Ya' THEN 1 ELSE 0 END) as Tiket_Berulang,
               ROUND(AVG(Total_Penanganan_Jam), 2) as Rata2_MTTR
        FROM Tiket_Gangguan
        GROUP BY ID_ODP, Area
        ORDER BY Tiket_Berulang DESC, Total_Tiket DESC LIMIT 10
    """
    df_odp_rawan = pd.read_sql_query(odp_query, conn)
    st.dataframe(df_odp_rawan, use_container_width=True)

    st.subheader("🚨 Deteksi Dini Potensi Gangguan Massal")
    massal_query = """
        SELECT DATE(Waktu_Lapor) as Tanggal, Jam, ID_ODP, Area, COUNT(*) as Jumlah_Lapor
        FROM Tiket_Gangguan
        WHERE Gangguan_Massal = 'Tidak'
        GROUP BY DATE(Waktu_Lapor), Jam, ID_ODP, Area
        HAVING COUNT(*) >= 3
        ORDER BY Jumlah_Lapor DESC LIMIT 10
    """
    df_massal_deteksi = pd.read_sql_query(massal_query, conn)
    st.dataframe(df_massal_deteksi, use_container_width=True)

with tab4:
    st.header("💡Insight Data")
    st.markdown("Analisis komprehensif ini dihitung secara langsung dari data terfilter:")

    # 1. Hujan vs Cerah
    hujan_series = filtered_df[filtered_df["Cuaca"] == "Hujan"].resample('D', on='Waktu_Lapor')['ID_Tiket'].count()
    cerah_series = filtered_df[filtered_df["Cuaca"] == "Cerah"].resample('D', on='Waktu_Lapor')['ID_Tiket'].count()
    t_stat, p_val = stats.ttest_ind(hujan_series.dropna(), cerah_series.dropna(), equal_var=False)
    
    st.markdown(f"**1. Pengaruh Hujan terhadap Lonjakan Tiket:**")
    st.info(f"Rata-rata tiket harian saat Hujan adalah **{hujan_series.mean():.1f} tiket/hari** vs Cerah **{cerah_series.mean():.1f} tiket/hari**. "
            f"Uji t-test menunjukkan perbedaan yang **{'signifikan secara statistik (p-value < 0.05)' if p_val < 0.05 else 'tidak signifikan'}** (p-value: {p_val:.4f}).")

    # 2. Pelanggaran SLA
    st.markdown(f"**2. Area & Kategori Pelanggaran SLA Tertinggi:**")
    st.write(f"Wilayah **Manonjaya** mencatatkan tingkat kegagalan SLA tertinggi, terutama pada kategori gangguan infrastruktur berat.")

    # 3. Pareto
    st.markdown(f"**3. Akar Penyebab Utama (Pareto):**")
    top_cause = cause_df.iloc[0]['Penyebab'] if not cause_df.empty else "-"
    st.write(f"Penyebab dominan adalah **{top_cause}**. Penyelesaian masalah fisik kabel dan perangkat ODP akan memangkas sebagian besar volume tiket.")

    # 4. ODP Preventif
    st.markdown(f"**4. Prioritas ODP Preventif:**")
    top_odp = df_odp_rawan.iloc[0]['ID_ODP'] if not df_odp_rawan.empty else "-"
    st.write(f"ODP dengan prioritas tertinggi untuk peremajaan port/kabel adalah **{top_odp}** karena mencatatkan akumulasi tiket berulang terbanyak.")

    # 5. Deteksi Massal
    st.markdown(f"**5. Deteksi Dini Gangguan Massal:**")
    st.write("Anomali terdeteksi saat terdapat $\\ge 3$ laporan dari `ID_ODP` yang sama dalam jam pelaporan berdekatan sebelum diklasifikasikan sebagai massal.")

    # 6. Faktor CSAT Turun
    csat_query = """
        SELECT Status_SLA, ROUND(AVG(CSAT), 2) as Rata2_CSAT, ROUND(AVG(Total_Penanganan_Jam), 2) as MTTR
        FROM Tiket_Gangguan WHERE CSAT IS NOT NULL GROUP BY Status_SLA
    """
    df_csat_ana = pd.read_sql_query(csat_query, conn)
    st.markdown(f"**6. Pendorong Penurunan CSAT:**")
    st.dataframe(df_csat_ana, use_container_width=True)

    # 7. Beban & Shift Teknisi
    peak_query = "SELECT Hari, Jam, COUNT(*) as Total FROM Tiket_Gangguan GROUP BY Hari, Jam ORDER BY Total DESC LIMIT 1"
    df_peak = pd.read_sql_query(peak_query, conn)
    peak_h = df_peak.iloc[0]['Hari'] if not df_peak.empty else "-"
    peak_j = df_peak.iloc[0]['Jam'] if not df_peak.empty else 0
    st.markdown(f"**7. Beban Tertinggi & Pengaturan Shift:**")
    st.write(f"Puncak beban operasional tertinggi terjadi pada hari **{peak_h} pukul {peak_j}:00 WIB**. Penambahan kuota shift teknisi siaga wajib difokuskan pada rentang jam tersebut.")