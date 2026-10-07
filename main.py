from datetime import date, timedelta
from pathlib import Path

from src.config import KOPIS_KEY

from src.collectors.kdca import (
    get_kdca_ari_table
)

from src.collectors.fluon import (
    get_fluon_region_ili
)

from src.processors.disease import (
    build_disease_df
)

from src.services.performance_service import (
    refresh_performance_master
)

from src.storage.csv_storage import (
    save_csv,
    save_performance_master,
    upsert_ili_region
)


# =========================================================
# 저장 경로
# =========================================================

OUTPUT_DIR = Path(
    "output"
)

PERFORMANCE_PATH = (
    OUTPUT_DIR
    / "performance_master.csv"
)

DISEASE_PATH = (
    OUTPUT_DIR
    / "disease.csv"
)

ILI_PATH = (
    OUTPUT_DIR
    / "ili_region.csv"
)


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
# 오늘 ~ 3개월 후 공연 전체 재수집
#
# 처리:
# - KOPIS 공연정보 수집
# - 공연장정보 수집
# - hall_metadata 갱신
# - 법정공휴일 기준 공연일수 계산
# - 행사 위해요소 계산
# - 행사위해점수 계산
#
# performance_master.csv 전체 교체
# =========================================================

def update_performance():

    print()
    print(
        "========================================"
    )
    print(
        "공연 데이터 업데이트 시작"
    )
    print(
        "========================================"
    )

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
        f"공연 데이터 업데이트 완료: "
        f"{len(performance_master_df)}건"
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
# disease.csv는 누적하지 않고
# 매번 전체 교체
# =========================================================

def update_disease():

    print()
    print(
        "========================================"
    )
    print(
        "질병 데이터 업데이트 시작"
    )
    print(
        "========================================"
    )

    end_year, end_week = (
        get_current_kdca_week()
    )

    print(
        f"KDCA 조회 범위: "
        f"2015년 1주차 ~ "
        f"{end_year}년 {end_week}주차"
    )

    # -------------------------------------------------
    # 1. KDCA 원본 수집
    # -------------------------------------------------

    kdca_df = (
        get_kdca_ari_table(
            start_year=2015,
            start_week=1,
            end_year=end_year,
            end_week=end_week
        )
    )

    print(
        f"KDCA 수집 완료: "
        f"{len(kdca_df)}주"
    )

    # -------------------------------------------------
    # 2. 질병 데이터 전처리
    #    + 유행수준 계산
    # -------------------------------------------------

    disease_df = (
        build_disease_df(
            kdca_df
        )
    )

    # -------------------------------------------------
    # 3. 전체 교체 저장
    # -------------------------------------------------

    save_csv(
        disease_df,
        DISEASE_PATH
    )

    print(
        f"질병 데이터 업데이트 완료: "
        f"{len(disease_df)}건"
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
    print(
        "========================================"
    )
    print(
        "지역 ILI 업데이트 시작"
    )
    print(
        "========================================"
    )

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
        f"지역 ILI 업데이트 완료: "
        f"{len(ili_region_df)}건"
    )

    return ili_region_df


# =========================================================
# 매일 실행
#
# 공연 데이터 갱신
#
# performance_master.csv에
# 행사 위해요소와 행사위해점수까지 저장
# =========================================================

def run_daily():

    print()
    print(
        "########################################"
    )
    print(
        "DAILY UPDATE 시작"
    )
    print(
        "########################################"
    )

    update_performance()

    print()
    print(
        "########################################"
    )
    print(
        "DAILY UPDATE 완료"
    )
    print(
        "########################################"
    )


# =========================================================
# 주간 실행
#
# 질병 데이터 갱신
# → 지역 ILI 갱신
#
# 공연 행사위해점수와
# 질병 유행수준은 별도 데이터로 관리
# =========================================================

def run_weekly():

    print()
    print(
        "########################################"
    )
    print(
        "WEEKLY UPDATE 시작"
    )
    print(
        "########################################"
    )

    update_disease()

    update_ili()

    print()
    print(
        "########################################"
    )
    print(
        "WEEKLY UPDATE 완료"
    )
    print(
        "########################################"
    )


# =========================================================
# 전체 실행
#
# 초기 세팅 또는 전체 갱신 시 사용
#
# 1. 공연 데이터
# 2. 질병 데이터
# 3. 지역 ILI
# =========================================================

def run_all():

    print()
    print(
        "########################################"
    )
    print(
        "FULL UPDATE 시작"
    )
    print(
        "########################################"
    )

    # -------------------------------------------------
    # 1. 공연
    # -------------------------------------------------

    update_performance()

    # -------------------------------------------------
    # 2. 질병
    # -------------------------------------------------

    update_disease()

    # -------------------------------------------------
    # 3. 지역 ILI
    # -------------------------------------------------

    update_ili()

    print()
    print(
        "########################################"
    )
    print(
        "FULL UPDATE 완료"
    )
    print(
        "########################################"
    )


# =========================================================
# 공연 데이터만 테스트
# =========================================================

def run_performance_only():

    update_performance()


# =========================================================
# 질병 데이터만 테스트
# =========================================================

def run_disease_only():

    update_disease()


# =========================================================
# ILI만 테스트
# =========================================================

def run_ili_only():

    update_ili()


# =========================================================
# 직접 실행
# =========================================================

if __name__ == "__main__":

    run_all()