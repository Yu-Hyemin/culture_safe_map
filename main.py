from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import KOPIS_KEY

from src.collectors.kdca import get_kdca_ari_table
from src.collectors.fluon import get_fluon_region_ili

from src.processors.disease import build_disease_df

from src.services.performance_service import refresh_performance_master
from src.services.risk import (
    build_weekly_risk_df,
    build_risk_df
)

from src.storage.csv_storage import (
    read_csv_if_exists,
    save_csv,
    save_performance_master,
    upsert_ili_region,
    upsert_risk
)


# =========================================================
# 저장 경로
# =========================================================

OUTPUT_DIR = Path('output')

PERFORMANCE_PATH = OUTPUT_DIR / 'performance_master.csv'
DISEASE_PATH = OUTPUT_DIR / 'disease.csv'
ILI_PATH = OUTPUT_DIR / 'ili_region.csv'
RISK_PATH = OUTPUT_DIR / 'risk.csv'


# =========================================================
# KDCA 현재 주차 계산
#
# 기준
# - 일요일 시작
# - 1월 1일이 포함된 주 = 1주차
# =========================================================

def get_current_kdca_week():

    today = date.today()

    jan_1 = date(
        today.year,
        1,
        1
    )

    days_since_sunday = (
        jan_1.weekday() + 1
    ) % 7

    week_1_start = (
        jan_1
        - timedelta(
            days=days_since_sunday
        )
    )

    week = (
        (today - week_1_start).days
        // 7
        + 1
    )

    return (
        today.year,
        week
    )


# =========================================================
# 공연 데이터 업데이트
#
# 매일:
# 오늘 ~ 3개월 후 전체 재수집
# 기존 파일 전체 교체
# =========================================================

def update_performance():

    print()
    print('========================================')
    print('공연 데이터 업데이트 시작')
    print('========================================')

    performance_master_df = (
        refresh_performance_master(
            kopis_key=KOPIS_KEY
        )
    )

    save_performance_master(
        performance_master_df,
        PERFORMANCE_PATH
    )

    print(
        f'공연 데이터 업데이트 완료: '
        f'{len(performance_master_df)}건'
    )

    return performance_master_df


# =========================================================
# 질병 데이터 업데이트
#
# 매주:
# 2015년 1주차 ~ 현재 주차 전체 재수집
#
# 집계 중 데이터는 kdca.py에서 제외
#
# 기존 disease.csv에 누적하지 않고
# 매번 전체 교체
# =========================================================

def update_disease():

    print()
    print('========================================')
    print('질병 데이터 업데이트 시작')
    print('========================================')

    end_year, end_week = (
        get_current_kdca_week()
    )

    print(
        f'KDCA 조회 범위: '
        f'2015년 1주차 ~ '
        f'{end_year}년 {end_week}주차'
    )

    # -------------------------------------------------
    # 1. KDCA 원본 수집
    # -------------------------------------------------

    kdca_df = get_kdca_ari_table(
        start_year=2015,
        start_week=1,
        end_year=end_year,
        end_week=end_week
    )

    print(
        f'KDCA 수집 완료: '
        f'{len(kdca_df)}주'
    )

    # -------------------------------------------------
    # 2. 질병 데이터 전처리 + 유행수준 계산
    # -------------------------------------------------

    disease_df = build_disease_df(
        kdca_df
    )

    # -------------------------------------------------
    # 3. 전체 교체 저장
    # -------------------------------------------------

    save_csv(
        disease_df,
        DISEASE_PATH
    )

    print(
        f'질병 데이터 업데이트 완료: '
        f'{len(disease_df)}건'
    )

    return disease_df


# =========================================================
# 지역 ILI 업데이트
#
# 매주:
# 기존 데이터 유지
#
# 같은
# 연도 + 주차 + 지역_시도
# 조합은 갱신
#
# 새로운 주차는 누적
# =========================================================

def update_ili():

    print()
    print('========================================')
    print('지역 ILI 업데이트 시작')
    print('========================================')

    new_ili_df = (
        get_fluon_region_ili()
    )

    ili_region_df = (
        upsert_ili_region(
            new_ili_df,
            ILI_PATH
        )
    )

    print(
        f'지역 ILI 업데이트 완료: '
        f'{len(ili_region_df)}건'
    )

    return ili_region_df


# =========================================================
# 최종 위험도 업데이트
#
# disease_df
# → 주간 대표 유행수준
#
# performance_master_df
# + weekly_risk_df
# → 공연별 최종 위험단계
#
# risk_df는 누적 저장
# =========================================================

def update_risk(
    performance_master_df=None,
    disease_df=None
):

    print()
    print('========================================')
    print('최종 위험도 업데이트 시작')
    print('========================================')

    # -------------------------------------------------
    # 1. 공연 데이터
    # -------------------------------------------------

    if performance_master_df is None:

        performance_master_df = (
            read_csv_if_exists(
                PERFORMANCE_PATH
            )
        )

    if (
        performance_master_df is None
        or performance_master_df.empty
    ):
        raise ValueError(
            'performance_master 데이터가 없습니다. '
            '먼저 공연 데이터를 업데이트해야 합니다.'
        )

    # -------------------------------------------------
    # 2. 질병 데이터
    # -------------------------------------------------

    if disease_df is None:

        disease_df = (
            read_csv_if_exists(
                DISEASE_PATH,
                parse_dates=[
                    '주차시작일',
                    '주차종료일'
                ]
            )
        )

    if (
        disease_df is None
        or disease_df.empty
    ):
        raise ValueError(
            'disease 데이터가 없습니다. '
            '먼저 질병 데이터를 업데이트해야 합니다.'
        )

    # -------------------------------------------------
    # 3. 주간 대표 유행수준 생성
    # -------------------------------------------------

    weekly_risk_df = (
        build_weekly_risk_df(
            disease_df
        )
    )

    # -------------------------------------------------
    # 4. 공연별 최종 위험도 계산
    # -------------------------------------------------

    new_risk_df = (
        build_risk_df(
            performance_master_df,
            weekly_risk_df
        )
    )

    # -------------------------------------------------
    # 5. 누적 저장
    #
    # 기준:
    # 공연ID + 적용시작일
    # -------------------------------------------------

    risk_df = (
        upsert_risk(
            new_risk_df,
            RISK_PATH
        )
    )

    print(
        f'최종 위험도 업데이트 완료: '
        f'{len(risk_df)}건'
    )

    return risk_df


# =========================================================
# 매일 실행
#
# 공연 데이터 갱신
# → 새 공연에 대한 위험도 다시 계산
# =========================================================

def run_daily():

    print()
    print('########################################')
    print('DAILY UPDATE 시작')
    print('########################################')

    performance_master_df = (
        read_csv_if_exists(
            PERFORMANCE_PATH,
            parse_dates=[
                '공연시작일',
                '공연종료일'
            ]
        )
    )

    update_risk(
        performance_master_df=performance_master_df
    )

    print()
    print('########################################')
    print('DAILY UPDATE 완료')
    print('########################################')


# =========================================================
# 주간 실행
#
# 질병
# → ILI
# → 새로운 질병 수준으로 위험도 갱신
# =========================================================

def run_weekly():

    print()
    print('########################################')
    print('WEEKLY UPDATE 시작')
    print('########################################')

    disease_df = (
        update_disease()
    )

    update_ili()

    update_risk(
        disease_df=disease_df
    )

    print()
    print('########################################')
    print('WEEKLY UPDATE 완료')
    print('########################################')


# =========================================================
# 전체 실행
#
# 초기 세팅 또는 전체 갱신 시 사용
# =========================================================

def run_all():

    print()
    print('########################################')
    print('FULL UPDATE 시작')
    print('########################################')

    # -------------------------------------------------
    # 1. 공연
    # -------------------------------------------------

    performance_master_df = (
        update_performance()
    )

    # -------------------------------------------------
    # 2. 질병
    # -------------------------------------------------

    disease_df = (
        update_disease()
    )

    # -------------------------------------------------
    # 3. 지역 ILI
    # -------------------------------------------------

    update_ili()

    # -------------------------------------------------
    # 4. 최종 위험도
    # -------------------------------------------------

    update_risk(
        performance_master_df=performance_master_df,
        disease_df=disease_df
    )

    print()
    print('########################################')
    print('FULL UPDATE 완료')
    print('########################################')


# =========================================================
# ILI만 테스트gkstlr
# =========================================================

def run_ili_only():

    update_ili()


# =========================================================
# 직접 실행
# =========================================================

if __name__ == '__main__':
    run_all()