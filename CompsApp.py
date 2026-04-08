import streamlit as st
import yfinance as yf
import pandas as pd
from io import BytesIO

# Configuration de la page
st.set_page_config(page_title="Terminal d'Analyse Financière", page_icon="📊", layout="wide")

st.title("📊 Terminal d'Analyse Financière")
st.markdown("Outil complet pour le diagnostic d'entreprise : fondamentaux, valorisation, dividendes et comparables.")

# Barre de recherche intuitive
ticker_input = st.text_input("🔍 Entrez le Ticker de l'entreprise (ex: MC.PA, AI.PA, AAPL) :", "MC.PA").upper()

if ticker_input:
    with st.spinner('Connexion aux bases de données financières et extraction...'):
        ticker = yf.Ticker(ticker_input)
        info = ticker.info
        
        company_name = info.get('shortName', ticker_input)
        industry = info.get('industry', 'Secteur non défini')
        sector = info.get('sector', 'Non défini')
        currency = info.get('financialCurrency', 'Devise')
        
        st.subheader(f"🏢 {company_name} ({ticker_input}) | Secteur : {sector} - {industry}")
        
        # Création de 5 onglets thématiques
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📖 Profil & Consensus", 
            "📈 Bourse & Dividendes", 
            "💰 Santé Financière", 
            "🧮 Valo & Comparables", 
            "📂 Actus & AMF"
        ])
        
        # ---------------- ONGLET 1 : PROFIL ET CONSENSUS ANALYSTES ----------------
        with tab1:
            st.markdown("### Présentation de l'entreprise")
            with st.expander("Voir la description complète (Business Summary)"):
                st.write(info.get('longBusinessSummary', 'Description non disponible pour cette entreprise.'))
            
            st.markdown("### Consensus des Analystes")
            col1, col2, col3 = st.columns(3)
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            target_price = info.get('targetMeanPrice', 0)
            
            # Calcul du potentiel de hausse/baisse
            upside = ((target_price / current_price) - 1) * 100 if current_price and target_price else 0
            
            col1.metric("Cours Actuel", f"{current_price} {currency}")
            col2.metric("Objectif Moyen (Target Price)", f"{target_price} {currency}" if target_price else "N/A", f"{upside:.1f}% potentiel" if target_price else None)
            
            reco = info.get('recommendationKey', 'N/A').replace('_', ' ').title()
            col3.metric("Recommandation Globale", reco)

        # ---------------- ONGLET 2 : BOURSE ET DIVIDENDES ----------------
        with tab2:
            st.markdown("### Performance Boursière (1 an)")
            try:
                hist = ticker.history(period="1y")
                if not hist.empty:
                    st.line_chart(hist['Close'], use_container_width=True)
                else:
                    st.warning("Historique des cours indisponible.")
            except:
                st.warning("Erreur lors du chargement du graphique.")
                
            st.markdown("### Historique des Dividendes")
            st.info("Information clé pour la création de rente en gestion de patrimoine.")
            div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
            st.metric("Dividend Yield (Rendement Actuel)", f"{div_yield:.2f}%" if div_yield else "N/A")
            
            try:
                dividends = ticker.dividends
                if not dividends.empty:
                    # Afficher les 5 dernières années max
                    recent_divs = dividends.tail(20) 
                    st.bar_chart(recent_divs, use_container_width=True)
                else:
                    st.write("Aucun dividende versé récemment ou données indisponibles.")
            except:
                st.write("Données de dividendes indisponibles.")

        # ---------------- ONGLET 3 : SANTÉ FINANCIÈRE ET MARGES ----------------
        with tab3:
            st.markdown("### Marges et Rentabilité (Profitability)")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            gross_margin = info.get('grossMargins', 0) * 100
            op_margin = info.get('operatingMargins', 0) * 100
            roe = info.get('returnOnEquity', 0) * 100
            roa = info.get('returnOnAssets', 0) * 100
            
            col_m1.metric("Marge Brute (Gross Margin)", f"{gross_margin:.1f}%" if gross_margin else "N/A")
            col_m2.metric("Marge Opérationnelle", f"{op_margin:.1f}%" if op_margin else "N/A")
            col_m3.metric("ROE (Return on Equity)", f"{roe:.1f}%" if roe else "N/A")
            col_m4.metric("ROA (Return on Assets)", f"{roa:.1f}%" if roa else "N/A")
            
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

        # ---------------- ONGLET 5 : DOCUMENTS PUBLICS ET ACTUS ----------------
        with tab5:
            st.markdown("### Actions sur Titres & Régulateurs")
            st.write("Gagnez du temps dans vos recherches de rapports annuels et corporate actions :")
            
            safe_name = company_name.replace(' ', '%20')
            st.link_button("📚 Base de données AMF (URD, prospectus)", f"https://bdif.amf-france.org/fr?motsCles={safe_name}")
            st.link_button("🏛️ Euronext Live (Calendrier financier)", f"https://live.euronext.com/en/search_instruments/{company_name}")
            
            st.markdown("---")
            st.markdown("### Dernières Actualités (Fil Yahoo Finance)")
            try:
                news = ticker.news
                if news:
                    for news_item in news[:5]:
                        # Affiche les actus proprement sous forme de liens
                        st.markdown(f"📰 **[{news_item['title']}]({news_item['link']})**")
                else:
                    st.write("Aucune actualité récente trouvée.")
            except:
                st.write("Erreur lors de la récupération des actualités.")