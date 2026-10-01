import pandas as pd


# =========================================================
# 좌석수 → 좌석단계
#
# 1 ~ 299석   : 1단계
# 300 ~ 499석 : 2단계
# 500 ~ 999석 : 3단계
# 1000석 이상 : 4단계
# =========================================================

def get_seat_level(value):

    if pd.isna(value) or value <= 0:
        return pd.NA

    if value < 300:
        return 1

    elif value < 500:
        return 2

    elif value < 1000:
        return 3

    else:
        return 4


# =========================================================
# 공연시간 → 시간단계
#
# 1 ~ 59분    : 1단계
# 60 ~ 119분  : 2단계
# 120 ~ 179분 : 3단계
# 180분 이상  : 4단계
# =========================================================

def get_time_level(value):

    if pd.isna(value) or value <= 0:
        return pd.NA

    if value < 60:
        return 1

    elif value < 120:
        return 2

    elif value < 180:
        return 3

    else:
        return 4


# =========================================================
# 좌석단계 + 시간단계 → 행사노출단계
#
# 합계 2 ~ 3 : 1단계
# 합계 4 ~ 5 : 2단계
# 합계 6 ~ 7 : 3단계
# 합계 8     : 4단계
# =========================================================

def get_exposure_level(row):

    seat_level = row['좌석단계']
    time_level = row['시간단계']

    if pd.isna(seat_level) or pd.isna(time_level):
        return pd.NA

    score = seat_level + time_level

    if score <= 3:
        return 1

    elif score <= 5:
        return 2

    elif score <= 7:
        return 3

    else:
        return 4


# =========================================================
# 공연정보 + 공연장정보 + 지역정보 결합
# =========================================================

def build_performance_master(
    performance_detail_df,
    hall_detail_df,
    facility_list_df,
    hall_metadata_df
):

    hall_detail_df = hall_detail_df.copy()
    performance_detail_df = performance_detail_df.copy()
    facility_list_df = facility_list_df.copy()

    # 공연장 좌석수 숫자형 변환
    hall_detail_df['공연장좌석수'] = pd.to_numeric(
        hall_detail_df['공연장좌석수']
        .astype(str)
        .str.replace(',', '', regex=False),
        errors='coerce'
    )

    # 공연시설 지역정보 추가
    hall_detail_df = hall_detail_df.merge(
        facility_list_df[
            [
                '공연시설ID',
                '지역_시도',
                '지역_구군'
            ]
        ],
        on='공연시설ID',
        how='left'
    )

    # 공연정보 + 공연장정보 결합
    performance_master_df = performance_detail_df.merge(
        hall_detail_df,
        on=[
            '공연시설ID',
            '공연장ID'
        ],
        how='left'
    )

    # 공연장 장소유형 추가
    performance_master_df = (
        performance_master_df.merge(
            hall_metadata_df[
                [
                    '공연시설ID',
                    '공연장ID',
                    '장소유형'
                ]
            ],
            on=[
                '공연시설ID',
                '공연장ID'
            ],
            how='left'
        )
    )

    performance_master_df[
        '장소유형'
    ] = (
        performance_master_df[
            '장소유형'
        ]
        .fillna('실내')
    )

    return performance_master_df


# =========================================================
# 행사노출단계 계산
# =========================================================

def add_exposure_levels(performance_master_df):

    df = performance_master_df.copy()

    # 좌석수 숫자형 정리
    df['공연장좌석수'] = pd.to_numeric(
        df['공연장좌석수'],
        errors='coerce'
    )

    # 공연시간 숫자형 정리
    df['공연시간_분'] = pd.to_numeric(
        df['공연시간_분'],
        errors='coerce'
    )

    # 좌석단계
    df['좌석단계'] = (
        df['공연장좌석수']
        .apply(get_seat_level)
        .astype('Int64')
    )

    # 시간단계
    df['시간단계'] = (
        df['공연시간_분']
        .apply(get_time_level)
        .astype('Int64')
    )

    # 행사노출단계
    df['행사노출단계'] = (
        df
        .apply(
            get_exposure_level,
            axis=1
        )
        .astype('Int64')
    )

    return df