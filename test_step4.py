import pandas as pd

from src.config import KOPIS_KEY
from src.collectors.kopis import get_kopis_facility_list


def run_step4_test():

    hall_keys_df = pd.DataFrame({
        '공연시설ID': [
            'FC001270',
            'FC000774',
            'FC002035',
            'FC001270',
            'FC005053',
            'FC001270',
            'FC000325',
            'FC000824',
            'FC000047',
            'FC001247'
        ]
    })

    print('========================================')
    print('[TEST] Step 4 단독 실행 시작')
    print('========================================')

    facility_list_df = get_kopis_facility_list(
        kopis_key=KOPIS_KEY,
        hall_keys_df=hall_keys_df
    )

    print()
    print(f'[TEST] 수집 결과: {len(facility_list_df)}건')
    print(facility_list_df)

    print()
    print('========================================')
    print('[TEST] Step 4 단독 실행 완료')
    print('========================================')


if __name__ == '__main__':
    run_step4_test()