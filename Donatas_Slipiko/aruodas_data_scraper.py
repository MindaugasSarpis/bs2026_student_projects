# %% Bibliotekų diegimas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import random
import re

# %%

# ==========================================
# 1.1. DUOMENŲ SURINKIMAS - DEFINE FUNCTION
# ==========================================
def scrape_aruodas_full_details():
    print("Atidaroma Chrome naršyklė...")
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    base_url = 'https://www.aruodas.lt/butai/vilniuje/puslapis/'
    
    visos_nuorodos = []
    surinkti_duomenys = []
    
    try:
        # --- 1 ETAPAS: Susirenkame tik skelbimų nuorodas ---
        for page in range(1, 3): # Testavimui imame tik 2 puslapius
            print(f"\nIeškoma nuorodų puslapyje: {page}...")
            driver.get(base_url + str(page) + '/')
            
            if page == 1:
                print("Laukiama 10s... PATVIRTINKITE SLAPUKUS/CAPTCHA!")
                time.sleep(10)
            else:
                time.sleep(random.uniform(2, 4))
                
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            skelbimai = soup.find_all('div', class_='list-row-v2')
            
            for skelbimas in skelbimai:
                adresas_el = skelbimas.find('div', class_='list-adress-v2')
                if adresas_el:
                    a_tag = adresas_el.find('a')
                    if a_tag and 'href' in a_tag.attrs:
                        visos_nuorodos.append(a_tag['href'])
        
        print(f"Rasta skelbimų nuorodų: {len(visos_nuorodos)}")
        
        # --- 2 ETAPAS: Einame į kiekvieną skelbimą ir traukiame info ---
        for nuoroda in visos_nuorodos[:10]: # TESTAVIMUI: palikta [:10], norint visų - ištrinti [:10]
            print(f"  > Skaitomas skelbimas: {nuoroda}")
            driver.get(nuoroda)
            time.sleep(random.uniform(2, 4)) # Pauzė tarp skelbimų
            
            vidus_soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Pasiruošiame tuščią žodyną vienam skelbimui
            buto_info = {
                'Mikrorajonas': None, 'Gatvė': None, 'Kaina': None, 
                'Kvadrato_kaina': None, 'Plotas': None, 'Kambariai': None,
                'Aukštas': None, 'Aukštų_sk': None, 'Metai': None,
                'Pastato_tipas': None, 'Įrengimas': None, 'Nuoroda': nuoroda
            }
            
            try:
                # 1 & 2. Mikrorajonas ir Gatvė
                adresas_el = vidus_soup.find('h1', class_='obj-header-text-address')
                if adresas_el:
                    dalys = [d.strip() for d in adresas_el.text.split(',')]
                    if len(dalys) >= 3:
                        buto_info['Mikrorajonas'] = dalys[1]
                        buto_info['Gatvė'] = dalys[2]
                
                # 3. Kaina (PATAISYTA SU REGEX)
                kaina_el = vidus_soup.find('span', class_='price-eur')
                if kaina_el:
                    skaicius = re.sub(r'[^0-9]', '', kaina_el.text)
                    if skaicius: buto_info['Kaina'] = int(skaicius)
                
                # 4. Kvadrato kaina (PATAISYTA SU REGEX)
                kv_kaina_el = vidus_soup.find('span', class_='price-per')
                if kv_kaina_el:
                    skaicius = re.sub(r'[^0-9]', '', kv_kaina_el.text)
                    if skaicius: buto_info['Kvadrato_kaina'] = int(skaicius)
                
                # 5 - 11. Ištraukiame viską iš <dl class="obj-details"> sąrašo
                dt_elements = vidus_soup.find_all('dt')
                for dt in dt_elements:
                    tekstas_dt = dt.text.strip().lower()
                    dd_element = dt.find_next_sibling('dd')
                    
                    if not dd_element: continue
                    tekstas_dd = dd_element.text.strip()
                    
                    # 5. Plotas
                    if 'plotas' in tekstas_dt:
                        skaicius = tekstas_dd.replace('m²', '').replace(',', '.').strip()
                        if skaicius: buto_info['Plotas'] = float(skaicius)
                        
                    # 6. Kambarių skaičius (PATAISYTA SU REGEX)
                    elif 'kambarių sk' in tekstas_dt:
                        skaicius = re.sub(r'[^0-9]', '', tekstas_dd)
                        if skaicius: buto_info['Kambariai'] = int(skaicius)
                        
                    # 7. Aukštas (PATAISYTA SU REGEX)
                    elif 'aukštas:' in tekstas_dt: 
                        skaicius = re.sub(r'[^0-9]', '', tekstas_dd)
                        if skaicius: buto_info['Aukštas'] = int(skaicius)
                        
                    # 8. Aukštų skaičius (PATAISYTA SU REGEX)
                    elif 'aukštų sk' in tekstas_dt:
                        skaicius = re.sub(r'[^0-9]', '', tekstas_dd)
                        if skaicius: buto_info['Aukštų_sk'] = int(skaicius)
                        
                    # 9. Statybos metai (PATAISYTA SU REGEX)
                    elif 'metai' in tekstas_dt:
                        skaiciai = re.sub(r'[^0-9]', '', tekstas_dd)
                        if len(skaiciai) >= 4:
                            buto_info['Metai'] = int(skaiciai[:4])
                            
                    # 10. Pastato tipas
                    elif 'pastato tipas' in tekstas_dt:
                        buto_info['Pastato_tipas'] = tekstas_dd
                        
                    # 11. Įrengimas
                    elif 'įrengimas' in tekstas_dt:
                        buto_info['Įrengimas'] = tekstas_dd

                surinkti_duomenys.append(buto_info)
                print("    [+] Duomenys sėkmingai nuskaityti!")
                
            except Exception as e:
                print(f"    [-] Klaida apdorojant {nuoroda}: {e}")
                continue

    finally:
        print("\nDarbas baigtas. Uždaroma naršyklė.")
        driver.quit()

    return pd.DataFrame(surinkti_duomenys)

# %% 

# ==========================================
# 1.2. DUOMENŲ SURINKIMAS - START FUNCTION
# ==========================================

if __name__ == "__main__":
    df_rezultatas = scrape_aruodas_full_details()
    
    if df_rezultatas.empty:
        print("\nDuomenų nerasta.")


# %%
# ==========================================
# 2.1. DUOMENŲ ANALIZĖ IR VIZUALIZACIJA - LENTELĖ
# ==========================================

# Nustatome, kad rodytų visus stulpelius
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Atvaizduojame pirmas 5 eilutes
df_rezultatas.head()


# %%
# ==========================================
# 2.2. DUOMENŲ ANALIZĖ IR VIZUALIZACIJA - GRAFIKAI
# ==========================================

# %% 1 GRAFIKAS: Kaina vs Statybos metai
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker # Reikalinga formatavimui

# Išvalome eilutes, kuriose trūksta metų arba kainos
df_simple = df_rezultatas.dropna(subset=['Metai', 'Kaina']).copy()

# Sukuriame grafiką ir gauname ašies objektą ('ax'), kad galėtume jį redaguoti
fig, ax = plt.subplots(figsize=(10, 6))

# Paprastas sklaidos grafikas (scatter plot)
ax.scatter(df_simple['Metai'], df_simple['Kaina'], s=50, alpha=0.6, color='steelblue')

ax.set_title('Butų kainos priklausomybė nuo statybos metų', fontsize=14)
ax.set_xlabel('Statybos metai', fontsize=12)
ax.set_ylabel('Kaina (€)', fontsize=12)

# MAGIJA: Priverčiame Y ašį nenaudoti mokslinio (1e6) formato ir atskirti tūkstančius
ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

# Pridedame tinklelį geresniam skaitomumui
ax.grid(True, linestyle=':', alpha=0.5)

plt.tight_layout()
plt.show()


# %% 2 GRAFIKAS: Kvadrato kaina vs Statybos metai
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Išvalome eilutes, kuriose trūksta metų arba kvadrato kainos
df_simple_sq = df_rezultatas.dropna(subset=['Metai', 'Kvadrato_kaina']).copy()

# Sukuriame grafiką
fig, ax = plt.subplots(figsize=(10, 6))

# Sklaidos grafikas (scatter plot) - dabar y ašyje yra 'Kvadrato_kaina'
ax.scatter(df_simple_sq['Metai'], df_simple_sq['Kvadrato_kaina'], s=50, alpha=0.6, color='mediumseagreen')

# Tekstai
ax.set_title('Kvadratinio metro kainos priklausomybė nuo statybos metų', fontsize=14)
ax.set_xlabel('Statybos metai', fontsize=12)
ax.set_ylabel('Kvadrato kaina (€/m²)', fontsize=12)

# Y ašies formatavimas (atskiria tūkstančius, pvz., 3,500)
ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

# Tinklelis
ax.grid(True, linestyle=':', alpha=0.5)

plt.tight_layout()
plt.show()

# %% 3 GRAFIKAS: Šnipiškių ANALIZĖ - Kvadrato kaina vs Statybos metai
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# 1. Filtruojame duomenis: paliekame tik tuos butus, kurių mikrorajonas yra 'Žirmūnai'
# Naudojame .str.contains, kad rastų net jei parašyta "Vilnius, Žirmūnai"
df_snipiskes = df_rezultatas[df_rezultatas['Mikrorajonas'].str.contains('Šnipiškės', case=False, na=False)].copy()

if df_snipiskes.empty:
    print("Šnipiškių duomenų nerasta. Patikrinkite, ar teisingai surinkote mikrorajonų pavadinimus.")
else:
    # 2. Braižome grafiką
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.scatter(df_snipiskes['Metai'], df_snipiskes['Kvadrato_kaina'], s=70, color='orangered', alpha=0.7)
    
    ax.set_title('Šnipiškių kvadrato kainos pagal statybos metus', fontsize=14, fontweight='bold')
    ax.set_xlabel('Statybos metai', fontsize=12)
    ax.set_ylabel('Kvadrato kaina (€/m²)', fontsize=12)
    
    ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.grid(True, linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.show()

# %% 4 GRAFIKAS: Plotas vs Kvadrato kaina
import matplotlib.pyplot as plt
import seaborn as sns

# Išvalome duomenis ir pašaliname ekstremalias anomalijas (pvz., >250 kv.m. butus), kad neiškreiptų vaizdo
df_plotas = df_rezultatas.dropna(subset=['Plotas', 'Kvadrato_kaina']).copy()
df_plotas = df_plotas[df_plotas['Plotas'] < 200] 

plt.figure(figsize=(10, 6))

# Brėžiame taškus
sns.scatterplot(data=df_plotas, x='Plotas', y='Kvadrato_kaina', color='teal', alpha=0.5, s=60)

# Pridedame regresijos (tendencijos) liniją su Seaborn! Tai labai patinka dėstytojams.
sns.regplot(data=df_plotas, x='Plotas', y='Kvadrato_kaina', scatter=False, color='red', line_kws={"linewidth":2})

plt.title('Ekonominė hipotezė: Buto ploto įtaka kvadratinio metro kainai', fontsize=14, fontweight='bold')
plt.xlabel('Buto plotas (m²)', fontsize=12)
plt.ylabel('Kvadrato kaina (€/m²)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.4)

plt.tight_layout()
plt.show()

# %% 5 GRAFIKAS: Vidutinė kaina populiariausiuose rajonuose
import matplotlib.pyplot as plt
import seaborn as sns

# Atrenkame 10 rajonų, kuriuose yra daugiausia skelbimų (kad išvengtume rajonų su 1 butu, kuris iškreipia vidurkį)
top_rajonai = df_rezultatas['Mikrorajonas'].value_counts().head(10).index

# Išfiltruojame lentelę, palikdami tik tuos top 10 rajonų
df_top_rajonai = df_rezultatas[df_rezultatas['Mikrorajonas'].isin(top_rajonai)].copy()

# Apskaičiuojame vidurkį ir surūšiuojame mažėjimo tvarka
vidurkiai = df_top_rajonai.groupby('Mikrorajonas')['Kvadrato_kaina'].mean().sort_values(ascending=False).reset_index()

plt.figure(figsize=(12, 7))

# Horizontalus stulpelinis grafikas (barplot)
# Naudojame spalvų paletę 'magma' arba 'viridis', kad atrodytų moksliškiau
sns.barplot(data=vidurkiai, x='Kvadrato_kaina', y='Mikrorajonas', palette='magma')

plt.title('Top 10 aktyviausių mikrorajonų: Vidutinė kvadrato kaina', fontsize=14, fontweight='bold')
plt.xlabel('Vidutinė kvadrato kaina (€/m²)', fontsize=12)
plt.ylabel('Mikrorajonas', fontsize=12)
plt.grid(axis='x', linestyle='--', alpha=0.6)

plt.tight_layout()
plt.show()


# %% 6 GRAFIKAS: Boxplot pagal kambarių skaičių
import matplotlib.pyplot as plt
import seaborn as sns

# Išvalome trūkstamus duomenis ir paimame tik standartinius butus (1-5 kambariai)
df_kamb = df_rezultatas.dropna(subset=['Kambariai', 'Kvadrato_kaina']).copy()
df_kamb = df_kamb[df_kamb['Kambariai'].isin([1, 2, 3, 4, 5])]

plt.figure(figsize=(10, 6))

# Brėžiame stačiakampę diagramą (Boxplot)
sns.boxplot(data=df_kamb, x='Kambariai', y='Kvadrato_kaina', palette='Set2')

plt.title('Kvadratinio metro kainos pasiskirstymas pagal kambarių skaičių', fontsize=14, fontweight='bold')
plt.xlabel('Kambarių skaičius', fontsize=12)
plt.ylabel('Kvadrato kaina (€/m²)', fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.4)

# Pridedame paaiškinimą apie boxplot elementus, jei dėstytojas paklaustų
plt.figtext(0.99, 0.01, '* Linija dėžutės viduryje rodo medianą. Taškai už ūsų ribų - kainų anomalijos.', 
            horizontalalignment='right', fontsize=9, color='gray')

plt.tight_layout()
plt.show()