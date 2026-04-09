import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import BytesIO

# Configuration de la page
st.set_page_config(page_title="Terminal Analyse Financière", page_icon="📊", layout="wide")

st.title("📊 Terminal d'Analyse Financière")
st.markdown("Outil complet pour le diagnostic d'entreprise : fondamentaux, valorisation, dividendes et comparables.")

# Fonction pour trouver le ticker à partir d'un nom (ex: "LVMH" -> "MC.PA")
def get_ticker_from_name(query):
    if not query:
        return ""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            return data['quotes'][0]['symbol']
    except:
        pass
    return query # Si ça échoue, on garde ce que l'utilisateur a tapé

# Barre de recherche intuitive
search_input = st.text_input("🔍 Entrez le Nom de l'entreprise ou son Ticker (ex: LVMH, Apple, AI.PA) :", "LVMH")

if search_input:
    with st.spinner('Recherche de l\'entreprise et extraction des données financières...'):
        # On traduit le nom en Ticker
        ticker_input = get_ticker_from_name(search_input).upper()
        
        ticker = yf.Ticker(ticker_input)
        info = ticker.info
        
        # Vérification si l'entreprise existe
        if 'shortName' not in info and 'longName' not in info:
            st.error(f"Impossible de trouver les données pour '{search_input}'. Essayez avec le Ticker direct.")
            st.stop()
            
        company_name = info.get('shortName', info.get('longName', ticker_input))
        industry = info.get('industry', 'Secteur non défini')
        sector = info.get('sector', 'Non défini')
        currency = info.get('financialCurrency', 'Devise non définie')
        website = info.get('website', '')
        
        st.subheader(f"🏢 {company_name} ({ticker_input}) | Secteur : {sector} - {industry}")
        
        # Création des 5 onglets
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📖 Profil & Consensus", 
            "📈 Bourse & Dividendes", 
            "⚖️ Ratios & Santé Financière", 
            "🧮 Valo & Comparables", 
            "📂 Actus & AMF"
        ])
        
        # ---------------- ONGLET 1 : PROFIL ----------------
        with tab1:
            st.markdown("### Présentation de l'entreprise")
            with st.expander("Voir la description complète (Business Summary)"):
                st.write(info.get('longBusinessSummary', 'Description non disponible.'))
            
            st.markdown("### Consensus des Analystes")
            col1, col2, col3 = st.columns(3)
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            target_price = info.get('targetMeanPrice', 0)
            upside = ((target_price / current_price) - 1) * 100 if current_price and target_price else 0
            
            col1.metric("Cours Actuel", f"{current_price} {currency}")
            col2.metric("Objectif Moyen (Target Price)", f"{target_price} {currency}" if target_price else "N/A", f"{upside:.1f}% potentiel" if target_price else None)
            reco = info.get('recommendationKey', 'N/A').replace('_', ' ').title()
            col3.metric("Recommandation Globale", reco)

        # ---------------- ONGLET 2 : BOURSE ET DIVIDENDES ----------------
        with tab2:
            # Sélecteur de période dynamique
            st.markdown("### Paramètres d'affichage")
            period_choice = st.radio("Sélectionnez la période à analyser :", ["1 An", "3 Ans", "5 Ans", "Maximum"], horizontal=True)
            period_dict = {"1 An": "1y", "3 Ans": "3y", "5 Ans": "5y", "Maximum": "max"}
            
            st.markdown(f"### Performance Boursière ({period_choice})")
            try:
                hist = ticker.history(period=period_dict[period_choice])
                if not hist.empty:
                    st.line_chart(hist['Close'], use_container_width=True)
            except:
                st.warning("Historique des cours indisponible.")
                
            st.markdown("---")
            st.markdown("### 💶 Historique et Politique de Dividendes")
            st.info(f"💡 **Comment lire ce graphique et ces chiffres ?** \n\nLes valeurs représentent le montant brut versé en espèces pour **UNE action** détenue. Par exemple, une valeur de '2.50' signifie que l'entreprise a versé 2,50 {currency} à l'actionnaire pour chaque action qu'il possédait à cette date. \n\nLe *Dividend Yield* (Rendement) indique combien ce dividende rapporte en pourcentage par rapport au prix actuel de l'action. C'est un indicateur clé pour identifier une valeur de 'Rendement' (orientée rente) face à une valeur de 'Croissance'.")
            
            raw_yield = info.get('dividendYield', 0)
            
            # Logique intelligente : si le chiffre brut est supérieur à 1 (ex: 2.61), 
            # c'est qu'il est déjà en %. S'il est inférieur (ex: 0.0261), on fait x100.
            # (On part du principe très rare qu'une entreprise verse plus de 100% de rendement)
            if raw_yield and raw_yield > 1:
                div_yield = raw_yield
            elif raw_yield:
                div_yield = raw_yield * 100
            else:
                div_yield = 0
                
            st.metric("Rendement Actuel (Dividend Yield)", f"{div_yield:.2f}%" if div_yield else "Pas de dividende")
            
            try:
                dividends = ticker.dividends
                if not dividends.empty:
                    # Filtre intelligent selon la période choisie (approximatif)
                    if period_choice == "1 An": div_show = dividends.tail(4)
                    elif period_choice == "3 Ans": div_show = dividends.tail(12)
                    elif period_choice == "5 Ans": div_show = dividends.tail(20)
                    else: div_show = dividends
                    st.bar_chart(div_show, use_container_width=True)
            except:
                st.write("Données de dividendes indisponibles.")

        # ---------------- ONGLET 3 : SANTÉ FINANCIÈRE ET RATIOS ----------------
        with tab3:
            st.markdown("### 🚦 Diagnostic de la Santé Financière")
            st.write("Passez votre souris sur le nom du ratio (le petit '?' apparaîtra) pour lire son explication métier et la façon de l'interpréter.")
            
            # 1. RENTABILITÉ
            st.markdown("#### 1. Rentabilité")
            r_col1, r_col2, r_col3 = st.columns(3)
            
            op_margin = info.get('operatingMargins', 0) * 100
            net_margin = info.get('profitMargins', 0) * 100
            roe = info.get('returnOnEquity', 0) * 100
            
            # Logique d'évaluation visuelle (Vert = Sain, Rouge = Risqué)
            r_col1.metric("Marge Opérationnelle", f"{op_margin:.1f}%", 
                          delta="Excellente" if op_margin > 15 else ("Critique" if op_margin < 5 else "Moyenne"), 
                          delta_color="normal" if op_margin > 15 else ("inverse" if op_margin < 5 else "off"),
                          help="Mesure la rentabilité de l'activité principale. Supérieur à 15% démontre souvent un avantage concurrentiel (pricing power).")
                          
            r_col2.metric("Marge Nette", f"{net_margin:.1f}%",
                          delta="Très rentable" if net_margin > 10 else "-Faible rentabilité",
                          help="Le profit final pour 100€ de chiffre d'affaires. Très variable selon les secteurs (la tech est haute, la grande distribution est basse).")
                          
            r_col3.metric("ROE (Return on Equity)", f"{roe:.1f}%",
                          delta="Générateur de valeur" if roe > 12 else "-Destructeur de valeur",
                          help="Rentabilité des capitaux propres. Combine la rentabilité nette, la rotation des actifs et le levier financier. On cherche idéalement > 12-15%.")

            # 2. RISQUE ET LIQUIDITÉ
            st.markdown("#### 2. Risque & Liquidité")
            r2_col1, r2_col2, r2_col3 = st.columns(3)
            
            current_ratio = info.get('currentRatio', 0)
            debt_equity = info.get('debtToEquity', 0)
            beta = info.get('beta', 1)
            
            r2_col1.metric("Current Ratio (Liquidité)", f"{current_ratio:.2f}",
                           delta="Très Solide" if current_ratio > 1.5 else ("-Risque de liquidité" if current_ratio < 1 else "Correct"),
                           help="Capacité à payer ses dettes à court terme. S'il est < 1, l'entreprise n'a pas assez d'actifs liquides pour rembourser ses obligations immédiates.")
                           
            r2_col2.metric("Debt to Equity (Endettement)", f"{debt_equity:.1f}%",
                           delta="Peu endetté" if debt_equity < 100 else "-Fort levier / Risqué",
                           delta_color="inverse", # Inversé car une dette haute est négative
                           help="Dette par rapport aux capitaux propres. > 100% signifie que l'entreprise est davantage financée par les banques que par ses actionnaires.")
                           
            r2_col3.metric("Bêta (Volatilité vs Marché)", f"{beta:.2f}",
                           delta="Défensif" if beta < 1 else "Volatil / Agressif",
                           delta_color="off", # Pas forcément rouge ou vert, dépend de la stratégie
                           help="Indique le risque de marché. Bêta = 1 : suit le marché. Bêta < 1 : moins volatil (défensif, ex: utilities). Bêta > 1 : amplifie le marché (agressif, ex: tech).")

            # 3. ETATS FINANCIERS 
            st.markdown("---")
            st.markdown("### États Financiers Annuels Simplifiés")
            try:
                financials = ticker.financials
                if not financials.empty:
                    # Extraction du CA et Résultat net
                    revenues = financials.loc['Total Revenue'] if 'Total Revenue' in financials.index else None
                    net_income = financials.loc['Net Income'] if 'Net Income' in financials.index else None
                   
                    if revenues is not None and net_income is not None:
                        fin_df = pd.DataFrame({"Chiffre d'Affaires": revenues, "Résultat Net": net_income})
                        fin_df.index = pd.to_datetime(fin_df.index).year
                        # Affichage en format graphique lisible
                        st.bar_chart(fin_df, use_container_width=True)
                else:
                    st.write("États financiers indisponibles pour ce ticker.")
            except:
                st.write("Erreur lors de la récupération des états financiers.")

        # ---------------- ONGLET 4 : VALORISATION ET COMPARABLES ----------------
        with tab4:
            st.markdown("### 1. Bridge Enterprise Value (EV)")
            market_cap = info.get('marketCap', 0)
            total_debt = info.get('totalDebt', 0)
            total_cash = info.get('totalCash', 0)
            ev = info.get('enterpriseValue', market_cap + total_debt - total_cash)
           
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Market Cap", f"{market_cap / 1e6:,.0f} M")
            col2.metric("Total Debt (+)", f"{total_debt / 1e6:,.0f} M")
            col3.metric("Cash (-)", f"{total_cash / 1e6:,.0f} M")
            col4.metric("Enterprise Value (=)", f"{ev / 1e6:,.0f} M")
           
            st.markdown("---")
            st.markdown("### 2. Multiples de Valorisation")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("EV / Revenue", info.get('enterpriseToRevenue', 'N/A'))
            m_col2.metric("EV / EBITDA", info.get('enterpriseToEbitda', 'N/A'))
            m_col3.metric("P / E (Trailing)", info.get('trailingPE', 'N/A'))
            m_col4.metric("Price to Book", info.get('priceToBook', 'N/A'))
           
            st.markdown("---")
            st.markdown("### 3. Matrice des Comparables (Peer Set)")
            default_peers = "RMS.PA, KER.PA, CDI.PA" if ticker_input == "MC.PA" else ""
            peers_input = st.text_input("Saisissez les Tickers des concurrents (séparés par des virgules) :", default_peers)
           
            if peers_input:
                peer_tickers = [p.strip() for p in peers_input.split(',')]
                comps_data = []
                progress_bar = st.progress(0)
                total_peers = len(peer_tickers) + 1
               
                for i, pt in enumerate([ticker_input] + peer_tickers):
                    try:
                        pt_info = yf.Ticker(pt).info
                        comps_data.append({
                            "Entreprise (Ticker)": f"{pt_info.get('shortName', pt)} ({pt})",
                            "Market Cap (M)": round(pt_info.get('marketCap', 0) / 1e6, 1) if pt_info.get('marketCap') else None,
                            "EV / EBITDA": pt_info.get('enterpriseToEbitda', None),
                            "P / E": pt_info.get('trailingPE', None),
                            "EV / Revenue": pt_info.get('enterpriseToRevenue', None),
                            "ROE (%)": round(pt_info.get('returnOnEquity', 0)*100, 1) if pt_info.get('returnOnEquity') else None
                        })
                    except:
                        pass
                    progress_bar.progress((i + 1) / total_peers)
                       
                comps_df = pd.DataFrame(comps_data)
                st.dataframe(comps_df, use_container_width=True)
               
                export_col1, export_col2 = st.columns(2)
               
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    comps_df.to_excel(writer, index=False, sheet_name='Comps')
                excel_data = output.getvalue()
               
                with export_col1:
                    st.download_button(
                        label="📊 Exporter au format Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"{ticker_input}_comps.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
               
                csv_data = comps_df.to_csv(index=False).encode('utf-8')
                with export_col2:
                    st.download_button(
                        label="🌐 Exporter pour Google Sheets (.csv)",
                        data=csv_data,
                        file_name=f"{ticker_input}_comps.csv",
                        mime="text/csv"
                    )


        # ---------------- ONGLET 5 : ACTUS & AMF ----------------
        with tab5:
            st.markdown("### Actions sur Titres & Régulateurs")
            st.write("Accédez directement aux documents réglementaires :")
            safe_name = company_name.replace(' ', '%20')
            st.link_button("📚 Base de données AMF (URD, prospectus)", f"https://bdif.amf-france.org/fr?motsCles={safe_name}")
            st.link_button("🏛️ Euronext Live (Calendrier financier)", f"https://live.euronext.com/en/search_instruments/{company_name}")
            
            st.markdown("---")
            st.markdown("### Dernières Actualités")
            
            # --- NOUVEAU SYSTÈME D'ACTUALITÉS VIA GOOGLE NEWS RSS ---
            import urllib.request
            import xml.etree.ElementTree as ET
            
            # On crée une recherche ciblée sur Google News avec le nom de l'entreprise
            news_query = urllib.parse.quote(f"{company_name} action finance")
            rss_url = f"https://news.google.com/rss/search?q={news_query}&hl=fr&gl=FR&ceid=FR:fr"
            
            try:
                # Récupération et analyse du flux RSS
                req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    
                    # Extraction des 5 premiers articles (items)
                    items = root.findall('./channel/item')[:5]
                    
                    if items:
                        for item in items:
                            title = item.find('title').text
                            link = item.find('link').text
                            pub_date = item.find('pubDate').text
                            
                            # Formatage propre de la date (pour enlever le fuseau horaire complexe)
                            clean_date = " ".join(pub_date.split(" ")[:4])
                            
                            st.markdown(f"📰 **[{title}]({link})**")
                            st.caption(f"🕒 Publié le : {clean_date}")
                    else:
                        st.info("Aucune actualité pertinente trouvée pour cette entreprise.")
            except Exception as e:
                st.error("Impossible de charger le flux d'actualités pour le moment.")