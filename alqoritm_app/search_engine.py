# alqoritm_app/search_engine.py

import pandas as pd
import re
from fuzzywuzzy import fuzz
import advertools as adv
from datetime import datetime
import os

# Master və test sütunları
MASTER_SERVICE_COLUMN = 'Malların (işlərin və xidmətlərin) adı'
TEST_QUERY_COLUMN = 'Malların (işlərin və xidmətlərin) adı'

# Sinonim bazası
SYNONYM_KNOWLEDGE_BASE = {
    "boya": "boya", "rənglənmə": "boya", "kraska": "boya", "ağardılması": "boya", "təmir": "təmir", "remont": "təmir", "təmiri": "təmir", "təmirin": "təmir", "təmırı": "təmir", "təmırın": "təmir", "bərpa": "təmir", "dəyişdirilməsi": "təmir",
    "alçipan": "alçipan", "alcipan": "alçipan", "alcıpanl": "alçipan", "gipsokarton": "alçipan", "alçıpanla": "alçipan",
    "divar": "divar", "divarlar": "divar", "divarın": "divar", "divarların": "divar", "dıvar": "divar", "arakəsmə": "divar", "divarlarının": "divar",
    "kafel": "kafel", "metlax": "kafel", "kafe": "kafel", "kafelinin": "kafel", "metlaxın": "kafel",
    "döşəmə": "döşəmə", "döşənmə": "döşəmə", "döşəməsinin": "döşəmə", "laminat": "döşəmə", "parket": "döşəmə", "pol": "döşəmə", "laminatdan": "döşəmə",
    "quraşdırma": "quraşdırma", "quraşdırılması": "quraşdırma", "montaj": "quraşdırma", "montaji": "quraşdırma", "qurulması": "quraşdırma",
    "çəkilmə": "quraşdırma", "çəkilməsi": "quraşdırma", "vurulma": "quraşdırma", "yığılma": "quraşdırma",
    "yığıl": "quraşdırma", "qurul": "quraşdırma", "qoyulması": "quraşdırma",
    "sökülmə": "sökülmə", "sökülməsi": "sökülmə", "söküntü": "sökülmə", "söküntüsü": "sökülmə",
    "təmizlənmə": "təmizlənmə", "təmizlənməsi": "təmizlənmə",
    "daşınması": "daşınma", "daşınma": "daşınma",
    "izolyasiya": "izolyasiya", "hidroizolyasiya": "izolyasiya", "izolyasiyalı": "izolyasiya",
    "suvaq": "suvaq", "suvağı": "suvaq", "şpatlyovka": "suvaq", "səthinin": "suvaq", "səthin": "suvaq",
    "beton": "beton", "betonlanması": "beton",
    "tavan": "tavan", "tavanın": "tavan", "tavanların": "tavan", "asma tavan": "tavan",
    "boru": "boru", "boruların": "boru",
    "sistem": "sistem", "sisteminin": "sistem",
    "drenaj": "drenaj", "havalandırma": "havalandırma",
    "metal": "metal", "dəmir": "metal",
    "çən": "çən", "çəni": "çən",
    "pəncərə": "pəncərə", "pəncərələrin": "pəncərə", "pvc": "pəncərə", "plastik": "pəncərə",
    "qapı": "qapı", "qapıların": "qapı", "mdf qapıların": "qapı",
    "taxta": "taxta", "plitə": "plitə", "şüşə": "şüşə",
    "şifer": "şifer", "polikarbonat": "polikarbonat",
    "elektrik": "elektrik", "santexnik": "santexnik", "santexnika": "santexnik",
    "aboy": "aboy", "divar kağızı": "aboy", "divar kagizi": "aboy", "paduqa": "paduqa",
    "işləri": "", "işi": "", "qiyməti": "", "neçəyədir": "", "axtarıram": "", "lazımdır": "", "olunması": "",
    "otağın": "otaq", "evin": "ev", "mənzildə": "ev", "hamam": "hamam", "mətbəx": "mətbəx",
    "isti pol": "isti pol", "ustasi": "usta", "profilsiz": "profilsiz",
}

RAW_CRITICAL_FEATURES = {"profilsiz", "izolyasiyalı", "sökülmə", "quraşdırma"}
NORMALIZED_CRITICAL_FEATURES = {word.lower().replace('g', 'ğ').replace('i', 'ı') for word in RAW_CRITICAL_FEATURES}
azerbaijani_stopwords = adv.stopwords['azerbaijani']

def preprocess_and_standardize(text, knowledge_base):
    if not isinstance(text, str): return ""
    for phrase, canonical in knowledge_base.items():
        if len(phrase.split()) > 1: text = text.replace(phrase, canonical)
    text = text.lower().replace('g', 'ğ').replace('i', 'ı')
    text = re.sub(r'[^\w\s]', '', text)
    tokens = text.split()
    tokens = [word for word in tokens if word not in azerbaijani_stopwords]
    suffixes = [
        'lanması', 'lənməsi', 'lanma', 'lənmə', 'nması', 'nməsi', 'ması', 'məsi', 'ların', 'lərin', 'ları', 'ləri', 'lar', 'lər', 'dan', 'dən', 'ın', 'in', 'un', 'ün',
        'da', 'də', 'a', 'ə', 'ı', 'u', 'ü', 'ma', 'mə', 'sı', 'si', 'la', 'lə'
    ]
    suffixes.sort(key=len, reverse=True)
    final_tokens = []
    for token in tokens:
        if token in knowledge_base:
            final_tokens.append(knowledge_base[token])
            continue
        stripped_token = token
        for suffix in suffixes:
            if stripped_token.endswith(suffix):
                stripped_token = stripped_token[:-len(suffix)]
                break
        if stripped_token in knowledge_base:
            final_tokens.append(knowledge_base[stripped_token])
        else:
            final_tokens.append(stripped_token)
    final_tokens = [token for token in final_tokens if token]
    return " ".join(final_tokens)

def find_top_matches(user_query, service_list, knowledge_base, top_n=5, min_score=65):
    canonical_query = preprocess_and_standardize(user_query, knowledge_base)
    query_tokens = set(canonical_query.split())
    all_matches = []
    for service in service_list:
        canonical_service = preprocess_and_standardize(service, knowledge_base)
        service_tokens = set(canonical_service.split())
        score = fuzz.token_set_ratio(canonical_query, canonical_service)
        for feature in NORMALIZED_CRITICAL_FEATURES:
            if (feature in query_tokens and feature not in service_tokens) or \
               (feature not in query_tokens and feature in service_tokens):
                score *= 0.70
                break
        if score >= min_score:
            all_matches.append({"match": service, "score": int(score)})
    sorted_matches = sorted(all_matches, key=lambda x: x['score'], reverse=True)
    return sorted_matches[:top_n]

def run_analysis(master_path, test_path, output_dir):
    print(f"📥 Master fayl yüklənir: {master_path}")
    master_db_df = pd.read_excel(master_path)
    MASTER_SERVICES_LIST = master_db_df[MASTER_SERVICE_COLUMN].dropna().tolist()
    print(f"✅ {len(MASTER_SERVICES_LIST)} xidmət master-dən oxundu.")

    print(f"📥 Test fayl yüklənir: {test_path}")
    test_df = pd.read_excel(test_path)
    test_queries = test_df[TEST_QUERY_COLUMN].dropna().tolist()
    print(f"✅ {len(test_queries)} test sorğusu oxundu.")

    print("🔍 Analizə başlanıldı...\n")
    report_data = []

    for idx, query in enumerate(test_queries):
        if not query:
            continue
        print(f"➡️ ({idx + 1}/{len(test_queries)}) Sorğu: {query}")
        top_results = find_top_matches(query, MASTER_SERVICES_LIST, SYNONYM_KNOWLEDGE_BASE, top_n=5)
        print(f"   🔸 Ən yaxın nəticə(lər): {[r['match'] for r in top_results]}")

        row_data = {"Test Query": query}
        for j, result in enumerate(top_results):
            row_data[f"Match {j+1}"] = result['match']
            row_data[f"Score {j+1}"] = result['score']
        report_data.append(row_data)

    report_df = pd.DataFrame(report_data)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"Customer_Analysis_Report_{timestamp}.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    print(f"\n💾 Excel faylı saxlanılır: {output_path}")
    report_df.to_excel(output_path, index=False)
    print("✅ Bitdi! Fayl hazırdı və brovserə göndəriləcək.\n")

    return output_path
