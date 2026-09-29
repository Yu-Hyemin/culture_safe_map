from pathlib import Path

import pandas as pd


# =========================================================
# 공통 CSV 읽기
# =========================================================

def read_csv_if_exists(
    file_path,
    parse_dates=None
):

    file_path = Path(file_path)

    if not file_path.exists():
        return pd.DataFrame()

    return pd.read_csv(
        file_path,
        encoding='utf-8-sig',
        parse_dates=parse_dates
    )


# =========================================================
# 공통 CSV 저장
# =========================================================

def save_csv(
    df,
    file_path
):

    file_path = Path(file_path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        file_path,
        index=False,
        encoding='utf-8-sig'
    )


# =========================================================
# 공연마스터 저장
#
# 운영 방식:
# - 매일 오늘 기준 3개월 공연을 다시 조회
# - 최신본으로 교체
# =========================================================

def save_performance_master(
    performance_master_df,
    file_path
):

    save_csv(
        performance_master_df,
        file_path
    )


# =========================================================
# disease_df 누적 저장
#
# 키:
# - 연도
# - 주차
# - 질병명
#
# 동일 키가 다시 들어오면
# 새 데이터로 갱신
# =========================================================

def upsert_disease(
    new_df,
    file_path
):

    old_df = read_csv_if_exists(
        file_path,
        parse_dates=[
            '주차시작일',
            '주차종료일'
        ]
    )

    if old_df.empty:

        combined_df = new_df.copy()

    else:

        combined_df = pd.concat(
            [
                old_df,
                new_df
            ],
            ignore_index=True
        )

    combined_df = (
        combined_df
        .drop_duplicates(
            subset=[
                '연도',
                '주차',
                '질병명'
            ],
            keep='last'
        )
        .sort_values(
            [
                '연도',
                '주차',
                '질병명'
            ]
        )
        .reset_index(drop=True)
    )

    save_csv(
        combined_df,
        file_path
    )

    return combined_df


# =========================================================
# ili_region_df 누적 저장
#
# 키:
# - 연도
# - 주차
# - 지역_시도
#
# 동일 키가 다시 들어오면
# 새 데이터로 갱신
# =========================================================

def upsert_ili_region(
    new_df,
    file_path
):

    old_df = read_csv_if_exists(
        file_path,
        parse_dates=[
            '주차시작일',
            '주차종료일',
            '업데이트일자'
        ]
    )

    if old_df.empty:

        combined_df = new_df.copy()

    else:

        combined_df = pd.concat(
            [
                old_df,
                new_df
            ],
            ignore_index=True
        )

    combined_df = (
        combined_df
        .drop_duplicates(
            subset=[
                '연도',
                '주차',
                '지역_시도'
            ],
            keep='last'
        )
        .sort_values(
            [
                '연도',
                '주차',
                '지역_시도'
            ]
        )
        .reset_index(drop=True)
    )

    # 날짜 컬럼 포맷 통일
    for col in [
        '주차시작일',
        '주차종료일',
        '업데이트일자'
    ]:

        combined_df[col] = (
            pd.to_datetime(
                combined_df[col]
            )
            .dt.strftime(
                '%Y-%m-%d'
            )
        )

    save_csv(
        combined_df,
        file_path
    )

    return combined_df


# =========================================================
# risk_df 누적 저장
#
# 키:
# - 공연ID
# - 적용시작일
#
# 같은 공연의 같은 적용기간 결과가 다시 계산되면
# 새 데이터로 갱신
# =========================================================

def upsert_risk(
    new_df,
    file_path
):

    old_df = read_csv_if_exists(
        file_path,
        parse_dates=[
            '적용시작일',
            '적용종료일'
        ]
    )

    if old_df.empty:

        combined_df = new_df.copy()

    else:

        combined_df = pd.concat(
            [
                old_df,
                new_df
            ],
            ignore_index=True
        )

    combined_df = (
        combined_df
        .drop_duplicates(
            subset=[
                '공연ID',
                '적용시작일'
            ],
            keep='last'
        )
        .sort_values(
            [
                '적용시작일',
                '공연ID'
            ]
        )
        .reset_index(drop=True)
    )

    save_csv(
        combined_df,
        file_path
    )

    return combined_df