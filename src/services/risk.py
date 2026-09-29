import pandas as pd


# =========================================================
# 최종위험단계 매트릭스
#
# (유행수준, 행사노출단계) → 최종위험단계
# =========================================================

RISK_MATRIX = {
    (1, 1): 1,
    (1, 2): 1,
    (1, 3): 2,
    (1, 4): 2,

    (2, 1): 1,
    (2, 2): 2,
    (2, 3): 2,
    (2, 4): 3,

    (3, 1): 2,
    (3, 2): 3,
    (3, 3): 3,
    (3, 4): 4,

    (4, 1): 3,
    (4, 2): 3,
    (4, 3): 4,
    (4, 4): 4
}


# =========================================================
# 유행수준 + 행사노출단계 → 최종위험단계
#
# 주최자 입력 행사에서도 그대로 재사용 가능
# =========================================================

def calculate_final_risk(
    epidemic_level,
    exposure_level
):

    if (
        pd.isna(epidemic_level)
        or pd.isna(exposure_level)
    ):
        return pd.NA

    return RISK_MATRIX.get(
        (
            int(epidemic_level),
            int(exposure_level)
        ),
        pd.NA
    )


# =========================================================
# 주차별 대표 유행질병 / 유행수준 생성
#
# 기준
# - 실제 존재하는 최근 N개 관측주차 사용
# - 각 주차에서 레벨백분위가 가장 높은 질병 선택
# - 동률이면 질병명 오름차순
# - 대표유행수준 = 해당 질병의 표본감시_유행단계
#
# 발표일     = 관측종료일 + 5일
# 적용시작일 = 발표일
# 적용종료일 = 발표일 + 6일
# =========================================================

def build_weekly_risk_df(
    disease_df,
    recent_weeks=4
):

    df = disease_df.copy()

    # 실제 존재하는 최근 N개 관측주차
    recent_week_dates = (
        df['주차시작일']
        .drop_duplicates()
        .sort_values()
        .tail(recent_weeks)
    )

    recent_disease_df = df[
        df['주차시작일'].isin(
            recent_week_dates
        )
    ].copy()

    # 각 주차에서 레벨백분위가 가장 높은 질병 선택
    weekly_risk_df = (
        recent_disease_df
        .sort_values(
            [
                '주차시작일',
                '레벨백분위',
                '질병명'
            ],
            ascending=[
                True,
                False,
                True
            ]
        )
        .drop_duplicates(
            subset=['주차시작일'],
            keep='first'
        )
        [
            [
                '연도',
                '주차',
                '주차시작일',
                '주차종료일',
                '질병명',
                '유행수준'
            ]
        ]
        .rename(
            columns={
                '질병명': '대표유행질병',
                '유행수준': '대표유행수준'
            }
        )
    )

    # 발표일
    weekly_risk_df['발표일'] = (
        weekly_risk_df['주차종료일']
        + pd.Timedelta(days=5)
    )

    # 서비스 적용기간
    weekly_risk_df['적용시작일'] = (
        weekly_risk_df['발표일']
    )

    weekly_risk_df['적용종료일'] = (
        weekly_risk_df['발표일']
        + pd.Timedelta(days=6)
    )

    weekly_risk_df['대표유행수준'] = (
        weekly_risk_df['대표유행수준']
        .astype('Int64')
    )

    return weekly_risk_df


# =========================================================
# 공연 × 적용기간 → risk_df 생성
#
# 결합 기준
# 공연시작일 <= 적용종료일
# AND
# 공연종료일 >= 적용시작일
#
# 적용기간과 공연기간이 하루라도 겹치면 포함
# =========================================================

def build_risk_df(
    performance_master_df,
    weekly_risk_df
):

    performance_df = performance_master_df.copy()
    weekly_df = weekly_risk_df.copy()

    # 날짜형 통일
    performance_df['공연시작일'] = pd.to_datetime(
        performance_df['공연시작일']
    )

    performance_df['공연종료일'] = pd.to_datetime(
        performance_df['공연종료일']
    )

    weekly_df['적용시작일'] = pd.to_datetime(
        weekly_df['적용시작일']
    )

    weekly_df['적용종료일'] = pd.to_datetime(
        weekly_df['적용종료일']
    )

    # -----------------------------------------------------
    # risk_df 생성에 실제 필요한 공연 컬럼만 사용
    # -----------------------------------------------------

    performance_risk_df = performance_df[
        [
            '공연ID',
            '공연시작일',
            '공연종료일',
            '행사노출단계'
        ]
    ].copy()

    # -----------------------------------------------------
    # 적용기간 × 공연 조합 생성
    # -----------------------------------------------------

    risk_df = weekly_df[
        [
            '적용시작일',
            '적용종료일',
            '대표유행수준',
            '대표유행질병'
        ]
    ].merge(
        performance_risk_df,
        how='cross'
    )

    # -----------------------------------------------------
    # 적용기간과 공연기간이 겹치는 공연만 남기기
    # -----------------------------------------------------

    risk_df = risk_df[
        (
            risk_df['공연시작일']
            <= risk_df['적용종료일']
        )
        &
        (
            risk_df['공연종료일']
            >= risk_df['적용시작일']
        )
    ].copy()

    # 대표유행수준 → 유행수준
    risk_df = risk_df.rename(
        columns={
            '대표유행수준': '유행수준'
        }
    )

    # -----------------------------------------------------
    # 최종위험단계 계산
    # -----------------------------------------------------

    risk_df['최종위험단계'] = risk_df.apply(
        lambda row: calculate_final_risk(
            row['유행수준'],
            row['행사노출단계']
        ),
        axis=1
    ).astype('Int64')

    # -----------------------------------------------------
    # 최종 risk_df
    #
    # 공연 상세정보는 performance_master_df에 보관하고,
    # risk_df에는 위험 계산에 필요한 값만 유지
    # -----------------------------------------------------

    risk_df = risk_df[
        [
            '적용시작일',
            '적용종료일',
            '공연ID',
            '행사노출단계',
            '유행수준',
            '대표유행질병',
            '최종위험단계'
        ]
    ].sort_values(
        [
            '적용시작일',
            '공연ID'
        ]
    ).reset_index(drop=True)

    return risk_df