import os
import glob
import json
import pandas as pd

PROTECTED_AREAS = {
    0 : 'محمية أشتوم الجميل',
    1 : 'محمية البرلس',
    2 : 'محمية الجزر الشمالية للبحر الأحمر',
    3 : 'محمية الجلف الكبير',
    4 : 'محمية الدبابية',
    5 : 'محمية الزرانيق',
    6 : 'محمية الصحراء البيضاء',
    7 : 'محمية العميد',
    8 : 'محمية الغابة المتحجرة',
    9 : 'محمية الواحات البحرية – الجزء الشرقي',
    10: 'محمية الواحات البحرية – الجزء الغربي',
    11: 'محمية الواحات البحرية – الجزء الوسطي',
    12: 'محمية رأس محمد',
    13: 'محمية سالوجا وغزال',
    14: 'محمية سانت كاثرين',
    15: 'محمية سيوة – القطاع الأوسط الجنوبي',
    16: 'محمية سيوة – القطاع الغربي',
    17: 'محمية سيوة – القطاع الشرقي',
    18: 'محمية طابا',
    19: 'محمية علبة',
    20: 'محمية قارون',
    21: 'محمية قبة الحسنة',
    22: 'محمية كهف سنور',
    23: 'محمية نبق',
    24: 'محمية نيزك جبل كامل',
    25: 'محمية وادي الأسيوطي',
    26: 'محمية وادي الجمال',
    27: 'محمية وادي الريان',
    28: 'محمية وادي العلاقي',
    29: 'محمية وادي دجلة',
    30: 'محمية أبو جالوم',
}

def main():
    data_path = os.path.join(os.path.dirname(__file__), "data_EWS", "data")
    csv_files = sorted(glob.glob(os.path.join(data_path, '*.csv')))
    
    if not csv_files:
        print(f"No CSV files found at {data_path}")
        return
        
    print(f"Found {len(csv_files)} CSV files. Computing baselines...")
    
    precip_baselines = {}
    precip_stds = {}
    soilmoist_p20 = {}
    
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        try:
            area_id = int(fname.replace('.csv', '').replace('subject_', '').strip())
        except ValueError:
            print(f"Could not parse area_id from: {fname} — skipping")
            continue
            
        df = pd.read_csv(fpath)
        
        p = df['total_precipitation_sum'].dropna()
        s = df['volumetric_soil_water_layer_1'].dropna()
        
        # We need to save the keys as strings for JSON compatibility
        area_id_str = str(area_id)
        precip_baselines[area_id_str] = float(p.median()) if len(p) > 0 else 1.0
        precip_stds[area_id_str] = float(p.std()) if len(p) > 1 else 1e-6
        soilmoist_p20[area_id_str] = float(s.quantile(0.20)) if len(s) > 0 else 0.05

    output = {
        "precip_baselines": precip_baselines,
        "precip_stds": precip_stds,
        "soilmoist_p20": soilmoist_p20
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "baselines.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        
    print(f"Baselines successfully saved to {out_path}")

if __name__ == "__main__":
    main()
