import pandas as pd

from src.config import KOPIS_KEY
from src.collectors.kopis import get_kopis_facility_list


def run_step4_test():

    performance_master_df = pd.read_csv(
        'output/performance_master.csv',
        encoding='utf-8-sig'
    )

    hall_keys_df = (
        performance_master_df[
            ['공연시설ID']
        ]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
    )

    print('========================================')
    print('[TEST] Step 4 단독 실행 시작')
    print(f'[TEST] 대상 공연시설ID: {len(hall_keys_df)}개')
    print('========================================')

    facility_list_df = get_kopis_facility_list(
        kopis_key=KOPIS_KEY,
        hall_keys_df=hall_keys_df
    )

    print()
    print(f'[TEST] 수집 결과: {len(facility_list_df)}건')

    print()
    print('========================================')
    print('[TEST] Step 4 단독 실행 완료')
    print('========================================')


if __name__ == '__main__':
    run_step4_test()