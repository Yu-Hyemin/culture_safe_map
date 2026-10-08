import time
import pandas as pd

from src.collectors.kopis import (
    get_kopis_performance_ids,
    get_kopis_performance_details,
    get_kopis_facility_list,
    get_kopis_hall_details
)

from src.processors.performance import (
    build_performance_master,
    add_performance_risk_features
)

from src.services.hall_metadata_service import (
    update_hall_metadata
)

from src.utils.logger import log
from pathlib import Path

# =========================================================
# 시간 표시
# =========================================================

def format_elapsed(seconds):

    if seconds < 60:
        return f'{seconds:.1f}초'

    minutes = int(
        seconds // 60
    )

    remain_seconds = int(
        seconds % 60
    )

    if minutes < 60:
        return (
            f'{minutes}분 '
            f'{remain_seconds}초'
        )

    hours = int(
        minutes // 60
    )

    remain_minutes = int(
        minutes % 60
    )

    return (
        f'{hours}시간 '
        f'{remain_minutes}분 '
        f'{remain_seconds}초'
    )


# =========================================================
# 공연 데이터 전체 갱신
# =========================================================

def refresh_performance_master(
    kopis_key
):

    total_start = time.time()

    log('========================================')
    log('공연 데이터 전체 수집 시작')
    log('========================================')

    # -------------------------------------------------
    # 1. 공연 ID 목록 수집
    # -------------------------------------------------

    step_start = time.time()

    log(
        '[1/6] 공연 ID 목록 수집 시작'
    )

    performance_ids = (
        get_kopis_performance_ids(
            kopis_key=kopis_key
        )
    )

    log(
        '[1/6] 공연 ID 목록 수집 완료 '
        f'- {len(performance_ids)}건 '
        f'- 소요시간: '
        f'{format_elapsed(time.time() - step_start)}'
    )

    # -------------------------------------------------
    # 2. 공연 상세정보 수집
    # -------------------------------------------------

    step_start = time.time()

    log(
        '[2/6] 공연 상세정보 수집 시작 '
        f'- 대상 {len(performance_ids)}건'
    )

    performance_detail_df, failed_ids = (
        get_kopis_performance_details(
            kopis_key=kopis_key,
            performance_ids=performance_ids
        )
    )

    log(
        '[2/6] 공연 상세정보 1차 수집 완료 '
        f'- 성공 {len(performance_detail_df)}건 '
        f'- 실패 {len(failed_ids)}건 '
        f'- 소요시간: '
        f'{format_elapsed(time.time() - step_start)}'
    )

    # -------------------------------------------------
    # 2-1. 실패 공연 재시도
    # -------------------------------------------------

    if failed_ids:

        retry_start = time.time()

        log(
            '[2/6] 공연 상세정보 재시도 시작 '
            f'- {len(failed_ids)}건'
        )

        retry_df, retry_failed_ids = (
            get_kopis_performance_details(
                kopis_key=kopis_key,
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
                    subset=[
                        '공연ID'
                    ],
                    keep='last'
                )
                .reset_index(
                    drop=True
                )
            )

        failed_ids = (
            retry_failed_ids
        )

        log(
            '[2/6] 공연 상세정보 재시도 완료 '
            f'- 최종 실패 {len(failed_ids)}건 '
            f'- 소요시간: '
            f'{format_elapsed(time.time() - retry_start)}'
        )

    # -------------------------------------------------
    # 3. 공연시설 / 공연장 키 생성
    #
    # 공연시설ID + 공연장ID
    # -------------------------------------------------

    step_start = time.time()

    log(
        '[3/6] 공연시설 / 공연장 키 정리 시작'
    )

    hall_keys_df = (
        performance_detail_df[
            [
                '공연시설ID',
                '공연장ID'
            ]
        ]
        .dropna()
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    log(
        '[3/6] 공연시설 / 공연장 키 정리 완료 '
        f'- {len(hall_keys_df)}개 '
        f'- 소요시간: '
        f'{format_elapsed(time.time() - step_start)}'
    )


    # -------------------------------------------------
    # KOPIS 요청 제한 방지를 위한 대기
    # -------------------------------------------------

    log(
        '[WAIT] KOPIS 요청 없이 10분 대기 시작'
    )
    time.sleep(600)

    log(
        '[WAIT] 10분 대기 완료'
    )





    # -------------------------------------------------
    # 4. 공연시설 목록 수집
    #
    # 지역_시도 / 지역_구군 확보
    # -------------------------------------------------

    step_start = time.time()

    log(
        '[4/6] 공연시설 목록 수집 시작'
    )

    facility_list_df = (
        get_kopis_facility_list(
            kopis_key=kopis_key,
            hall_keys_df=hall_keys_df
        )
    )

    log(
        '[4/6] 공연시설 목록 수집 완료 '
        f'- {len(facility_list_df)}건 '
        f'- 소요시간: '
        f'{format_elapsed(time.time() - step_start)}'
    )

    # -------------------------------------------------
    # 5. 공연장 상세정보 수집
    #
    # 위도 / 경도 / 주소 / 좌석수
    # -------------------------------------------------

    step_start = time.time()

    facility_count = (
        hall_keys_df[
            '공연시설ID'
        ]
        .dropna()
        .nunique()
    )

    log(
        '[5/6] 공연장 상세정보 수집 시작 '
        f'- 공연시설 {facility_count}개'
    )

    hall_detail_df, failed_facility_ids = (
        get_kopis_hall_details(
            kopis_key=kopis_key,
            hall_keys_df=hall_keys_df
        )
    )

    log(
        '[5/6] 공연장 상세정보 1차 수집 완료 '
        f'- 상세 {len(hall_detail_df)}건 '
        f'- 실패 시설 {len(failed_facility_ids)}개 '
        f'- 소요시간: '
        f'{format_elapsed(time.time() - step_start)}'
    )

    # -------------------------------------------------
    # 5-1. 실패 시설 재시도
    # -------------------------------------------------

    if failed_facility_ids:

        retry_start = time.time()

        log(
            '[5/6] 공연장 상세정보 재시도 시작 '
            f'- {len(failed_facility_ids)}개'
        )

        # ---------------------------------------------
        # 실패한 공연시설에 해당하는
        # 공연장 키만 다시 추출
        # ---------------------------------------------

        retry_hall_keys_df = (
            hall_keys_df[
                hall_keys_df[
                    '공연시설ID'
                ].isin(
                    failed_facility_ids
                )
            ]
            .copy()
        )

        retry_hall_df, retry_failed_facility_ids = (
            get_kopis_hall_details(
                kopis_key=kopis_key,
                hall_keys_df=retry_hall_keys_df
            )
        )

        if not retry_hall_df.empty:

            hall_detail_df = (
                pd.concat(
                    [
                        hall_detail_df,
                        retry_hall_df
                    ],
                    ignore_index=True
                )
                .drop_duplicates(
                    subset=[
                        '공연시설ID',
                        '공연장ID'
                    ],
                    keep='last'
                )
                .reset_index(
                    drop=True
                )
            )

        failed_facility_ids = (
            retry_failed_facility_ids
        )

        log(
            '[5/6] 공연장 상세정보 재시도 완료 '
            f'- 최종 실패 시설 '
            f'{len(failed_facility_ids)}개 '
            f'- 소요시간: '
            f'{format_elapsed(time.time() - retry_start)}'
        )

    # -------------------------------------------------
    # 5-2. 공연장 메타데이터 갱신
    #
    # 기존 공연장 → 기존 장소유형 유지
    # 신규 공연장 → 장소유형 '실내'로 추가
    # -------------------------------------------------

    log(
        '[5-2/6] 공연장 메타데이터 갱신 시작'
    )

    hall_metadata_df = (
        update_hall_metadata(
            hall_detail_df
        )
    )

    log(
        '[5-2/6] 공연장 메타데이터 갱신 완료 '
        f'- {len(hall_metadata_df)}개'
    )




    # -------------------------------------------------
    # 5-3. 중간 결과 저장
    # -------------------------------------------------

    TEMP_DIR = Path('output/temp')
    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    performance_detail_df.to_csv(
        TEMP_DIR / 'performance_detail.csv',
        index=False,
        encoding='utf-8-sig'
    )

    facility_list_df.to_csv(
        TEMP_DIR / 'facility_list.csv',
        index=False,
        encoding='utf-8-sig'
    )

    hall_detail_df.to_csv(
        TEMP_DIR / 'hall_detail.csv',
        index=False,
        encoding='utf-8-sig'
    )

    log(
        '[CHECKPOINT] 1~5단계 중간 결과 저장 완료'
    )




    # -------------------------------------------------
    # 6. 최종 공연 마스터 생성
    # -------------------------------------------------

    step_start = time.time()

    log(
        '[6/6] performance_master 생성 시작'
    )

    performance_master_df = build_performance_master(
        performance_detail_df=performance_detail_df,
        hall_detail_df=hall_detail_df,
        facility_list_df=facility_list_df,
        hall_metadata_df=hall_metadata_df
    )

    performance_master_df = (
        add_performance_risk_features(
            performance_master_df
        )
    )

    log(
        '[6/6] performance_master 생성 완료 '
        f'- {len(performance_master_df)}건 '
        f'- 소요시간: '
        f'{format_elapsed(time.time() - step_start)}'
    )

    # -------------------------------------------------
    # 전체 완료
    # -------------------------------------------------

    total_elapsed = (
        time.time()
        - total_start
    )

    log('========================================')

    log(
        '공연 데이터 전체 수집 완료 '
        f'- 총 {len(performance_master_df)}건 '
        f'- 총 소요시간: '
        f'{format_elapsed(total_elapsed)}'
    )

    log('========================================')

    if failed_ids:

        log(
            f'주의: 최종 실패 공연ID '
            f'{len(failed_ids)}건'
        )

    if failed_facility_ids:

        log(
            f'주의: 최종 실패 공연시설 '
            f'{len(failed_facility_ids)}개'
        )

    return performance_master_df