import time
import pandas as pd

from src.config import KOPIS_KEY
from src.collectors.kopis import (
    get_kopis_performance_ids,
    get_kopis_performance_details,
    get_kopis_facility_list
)


def run_test():

    print('========================================')
    print('[TEST] Step 1~3 → 10분 대기 → Step 4 시작')
    print('========================================')

    # =====================================================
    # Step 1
    # =====================================================

    print()
    print('[1/4] 공연 ID 목록 수집 시작')

    performance_ids = get_kopis_performance_ids(
        kopis_key=KOPIS_KEY
    )

    print(
        f'[1/4] 공연 ID 목록 수집 완료: '
        f'{len(performance_ids)}건'
    )

    # =====================================================
    # Step 2
    # =====================================================

    print()
    print(
        f'[2/4] 공연 상세정보 수집 시작: '
        f'{len(performance_ids)}건'
    )

    performance_detail_df, failed_ids = (
        get_kopis_performance_details(
            kopis_key=KOPIS_KEY,
            performance_ids=performance_ids
        )
    )

    print(
        f'[2/4] 1차 수집 완료 '
        f'- 성공 {len(performance_detail_df)}건 '
        f'- 실패 {len(failed_ids)}건'
    )

    # 실제 전체 실행과 동일하게 실패 건 재시도
    if failed_ids:

        print(
            f'[2/4] 실패 공연 재시도 시작: '
            f'{len(failed_ids)}건'
        )

        retry_df, retry_failed_ids = (
            get_kopis_performance_details(
                kopis_key=KOPIS_KEY,
                performance_ids=failed_ids
            )
        )

        if not retry_df.empty:

            performance_detail_df = (
                pd.concat(
                    [
                        performance_detail_df,
                        retry_df
                    ],
                    ignore_index=True
                )
                .drop_duplicates(
                    subset=['공연ID'],
                    keep='last'
                )
                .reset_index(drop=True)
            )

        failed_ids = retry_failed_ids

        print(
            f'[2/4] 재시도 완료 '
            f'- 최종 실패 {len(failed_ids)}건'
        )

    # =====================================================
    # Step 3
    # =====================================================

    print()
    print('[3/4] 공연시설 / 공연장 키 정리')

    hall_keys_df = (
        performance_detail_df[
            [
                '공연시설ID',
                '공연장ID'
            ]
        ]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
    )

    facility_count = (
        hall_keys_df['공연시설ID']
        .nunique()
    )

    print(
        f'[3/4] 키 정리 완료 '
        f'- 공연장 키 {len(hall_keys_df)}개 '
        f'- 공연시설 {facility_count}개'
    )

    # =====================================================
    # 10분 대기
    # =====================================================

    print()
    print('========================================')
    print('[WAIT] KOPIS 요청 없이 10분 대기 시작')
    print('========================================')

    time.sleep(600)

    print('[WAIT] 10분 대기 완료')

    # =====================================================
    # Step 4
    # =====================================================

    print()
    print('[4/4] 공연시설 목록 수집 시작')

    facility_list_df = get_kopis_facility_list(
        kopis_key=KOPIS_KEY,
        hall_keys_df=hall_keys_df
    )

    print(
        f'[4/4] 공연시설 목록 수집 완료: '
        f'{len(facility_list_df)}건'
    )

    print()
    print('========================================')
    print('[TEST] 전체 테스트 성공')
    print('========================================')


if __name__ == '__main__':
    run_test()