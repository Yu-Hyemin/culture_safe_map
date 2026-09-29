import numpy as np
import pandas as pd

from datetime import datetime, timedelta


# =========================================================
# 주차 날짜 계산
#
# 기준
# - 주 시작일: 일요일
# - 주 종료일: 토요일
# - 1주차: 1월 1일이 포함된 일요일 시작 주
# =========================================================

def get_week_dates(year, week):

    year = int(year)
    week = int(week)

    jan_1 = datetime(
        year,
        1,
        1
    )

    # Python weekday()
    # 월=0 ... 일=6
    days_since_sunday = (
        jan_1.weekday() + 1
    ) % 7

    week_1_start = (
        jan_1
        - timedelta(
            days=days_since_sunday
        )
    )

    week_start = (
        week_1_start
        + timedelta(
            weeks=week - 1
        )
    )

    week_end = (
        week_start
        + timedelta(
            days=6
        )
    )

    return (
        week_start.date(),
        week_end.date()
    )


# =========================================================
# KDCA 데이터 전처리
#
# 입력
# 연도 | 주차 | 계 | 마이코플라즈마균 | ... | 코로나19
#
# 출력
# 연도 | 주차 | 주차시작일 | 주차종료일 | 질병명 | 환자수
# =========================================================

def preprocess_kdca_data(kdca_df):

    df = kdca_df.copy()

    # -------------------------------------------------
    # 1. 전체 합계 제거
    # -------------------------------------------------

    if '계' in df.columns:

        df = df.drop(
            columns=['계']
        )

    # -------------------------------------------------
    # 2. wide → long
    # -------------------------------------------------

    disease_df = df.melt(
        id_vars=[
            '연도',
            '주차'
        ],
        var_name='질병명',
        value_name='환자수'
    )

    # -------------------------------------------------
    # 3. 자료형 정리
    # -------------------------------------------------

    disease_df['연도'] = (
        disease_df['연도']
        .astype(int)
    )

    disease_df['주차'] = (
        disease_df['주차']
        .astype(int)
    )

    disease_df['환자수'] = pd.to_numeric(
        disease_df['환자수'],
        errors='coerce'
    )

    # -------------------------------------------------
    # 4. 코로나19 집계 시작 전 값 결측 처리
    #
    # 코로나19:
    # - 2024년 이전 값은 실제 0이 아니라 미집계값
    # - 따라서 NaN 처리
    #
    # 그 외 질병:
    # - 0은 실제 관측값이므로 그대로 유지
    # -------------------------------------------------

    covid_before_start = (
        (disease_df['질병명'] == '코로나19')
        & (disease_df['연도'] < 2024)
    )

    disease_df.loc[
        covid_before_start,
        '환자수'
    ] = np.nan

    # -------------------------------------------------
    # 5. 주차 시작일 / 종료일 생성
    # -------------------------------------------------

    week_dates = disease_df.apply(
        lambda row: get_week_dates(
            row['연도'],
            row['주차']
        ),
        axis=1
    )

    disease_df[
        [
            '주차시작일',
            '주차종료일'
        ]
    ] = pd.DataFrame(
        week_dates.tolist(),
        index=disease_df.index
    )

    # -------------------------------------------------
    # 6. 컬럼 순서
    # -------------------------------------------------

    disease_df = disease_df[
        [
            '연도',
            '주차',
            '주차시작일',
            '주차종료일',
            '질병명',
            '환자수'
        ]
    ]

    # -------------------------------------------------
    # 7. 정렬
    # -------------------------------------------------

    disease_df = (
        disease_df
        .sort_values(
            [
                '질병명',
                '연도',
                '주차'
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return disease_df


# =========================================================
# 유행수준 백분위 계산
#
# 비교 기준
# - 같은 질병
# - 현재 연도의 직전 2개 연도
#
# 공식
# 현재값보다 작은 과거 관측값 수
# -------------------------------- × 100
#       비교 가능한 과거 값 수
#
# 동일값은 "작다"에 포함하지 않음
#
# 결측값:
# - 비교 대상에서 제외
#
# 0:
# - 실제 관측값이면 정상 포함
# =========================================================

def calculate_level_percentile(disease_df):

    df = disease_df.copy()

    df['레벨백분위'] = np.nan
    df['비교주차수'] = pd.NA

    diseases = (
        df['질병명']
        .dropna()
        .unique()
    )

    for disease in diseases:

        disease_data = df[
            df['질병명'] == disease
        ].copy()

        years = sorted(
            disease_data['연도'].unique()
        )

        for year in years:

            baseline_years = [
                year - 2,
                year - 1
            ]

            # 직전 2개 연도 각각에 실제 관측값이 있는지 확인
            valid_baseline = True

            for baseline_year in baseline_years:

                year_values = disease_data[
                    disease_data['연도'] == baseline_year
                ]['환자수'].dropna()

                if year_values.empty:
                    valid_baseline = False
                    break

            if not valid_baseline:
                continue

            baseline = disease_data[
                disease_data['연도'].isin(
                    baseline_years
                )
            ]['환자수'].dropna()

            comparison_count = len(
                baseline
            )

            if comparison_count == 0:
                continue

            current_indexes = disease_data[
                disease_data['연도'] == year
            ].index

            for idx in current_indexes:

                current_value = df.at[
                    idx,
                    '환자수'
                ]

                if pd.isna(
                    current_value
                ):
                    continue

                lower_count = (
                    baseline
                    < current_value
                ).sum()

                percentile = (
                    lower_count
                    / comparison_count
                    * 100
                )

                df.at[
                    idx,
                    '레벨백분위'
                ] = percentile

                df.at[
                    idx,
                    '비교주차수'
                ] = comparison_count

    return df


# =========================================================
# 백분위 → 유행수준
#
# 1단계: 60 미만
# 2단계: 60 이상 90 미만
# 3단계: 90 이상 95 미만
# 4단계: 95 이상
# =========================================================

def classify_epidemic_level(percentile):

    if pd.isna(
        percentile
    ):
        return pd.NA

    if percentile < 60:
        return 1

    if percentile < 90:
        return 2

    if percentile < 95:
        return 3

    return 4


# =========================================================
# 유행수준 추가
# =========================================================

def add_disease_risk_levels(disease_df):

    df = disease_df.copy()

    df['유행수준'] = (
        df['레벨백분위']
        .apply(
            classify_epidemic_level
        )
        .astype('Int64')
    )

    return df


# =========================================================
# KDCA 원본 → 최종 disease_df 생성
# =========================================================

def build_disease_df(kdca_df):

    # 1. KDCA 데이터 전처리
    disease_df = preprocess_kdca_data(
        kdca_df
    )

    # 2. 직전 2개 연도 대비 백분위 계산
    disease_df = calculate_level_percentile(
        disease_df
    )

    # 3. 백분위 기반 유행수준 계산
    disease_df = add_disease_risk_levels(
        disease_df
    )

    # 4. 최종 정렬
    disease_df = (
        disease_df
        .sort_values(
            [
                '연도',
                '주차',
                '질병명'
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return disease_df