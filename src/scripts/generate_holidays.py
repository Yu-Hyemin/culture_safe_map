from pathlib import Path

import pandas as pd
from korean_lunar_calendar import (
    KoreanLunarCalendar
)


# =========================================================
# 설정
# =========================================================

START_YEAR = 2014
END_YEAR = 2040

OUTPUT_PATH = Path(
    "data/holidays.csv"
)


# =========================================================
# 음력 → 양력 변환
# =========================================================

def lunar_to_solar(
    year,
    month,
    day
):
    """
    음력 날짜를 양력 날짜로 변환한다.
    윤달은 사용하지 않는다.
    """

    calendar = (
        KoreanLunarCalendar()
    )

    success = calendar.setLunarDate(
        year,
        month,
        day,
        False
    )

    if not success:
        raise ValueError(
            f"음력 변환 실패: "
            f"{year}-{month}-{day}"
        )

    return pd.Timestamp(
        calendar.SolarIsoFormat()
    )


# =========================================================
# 공휴일 추가 함수
# =========================================================

def add_holiday(
    rows,
    date,
    name,
    holiday_type
):
    rows.append(
        {
            "날짜": pd.Timestamp(
                date
            ),
            "공휴일명": name,
            "유형": holiday_type,
        }
    )


# =========================================================
# 연도별 기본 법정공휴일 생성
# =========================================================

def create_holidays(
    start_year,
    end_year
):

    rows = []

    for year in range(
        start_year,
        end_year + 1
    ):

        # -------------------------------------------------
        # 양력 기준 고정 공휴일
        # -------------------------------------------------

        fixed_holidays = [
            (
                f"{year}-01-01",
                "1월1일"
            ),
            (
                f"{year}-03-01",
                "삼일절"
            ),
            (
                f"{year}-05-05",
                "어린이날"
            ),
            (
                f"{year}-06-06",
                "현충일"
            ),
            (
                f"{year}-08-15",
                "광복절"
            ),
            (
                f"{year}-10-03",
                "개천절"
            ),
            (
                f"{year}-10-09",
                "한글날"
            ),
            (
                f"{year}-12-25",
                "기독탄신일"
            ),
        ]

        for date, name in fixed_holidays:

            add_holiday(
                rows,
                date,
                name,
                "고정공휴일"
            )


        # -------------------------------------------------
        # 2026년부터 추가
        # 노동절 / 제헌절
        # -------------------------------------------------

        if year >= 2026:

            add_holiday(
                rows,
                f"{year}-05-01",
                "노동절",
                "고정공휴일"
            )

            add_holiday(
                rows,
                f"{year}-07-17",
                "제헌절",
                "고정공휴일"
            )


        # -------------------------------------------------
        # 설날
        # 음력 1월 1일 전날 / 당일 / 다음날
        # -------------------------------------------------

        lunar_new_year = lunar_to_solar(
            year,
            1,
            1
        )

        add_holiday(
            rows,
            lunar_new_year
            - pd.Timedelta(days=1),
            "설날",
            "음력공휴일"
        )

        add_holiday(
            rows,
            lunar_new_year,
            "설날",
            "음력공휴일"
        )

        add_holiday(
            rows,
            lunar_new_year
            + pd.Timedelta(days=1),
            "설날",
            "음력공휴일"
        )


        # -------------------------------------------------
        # 부처님오신날
        # 음력 4월 8일
        # -------------------------------------------------

        buddha_birthday = lunar_to_solar(
            year,
            4,
            8
        )

        add_holiday(
            rows,
            buddha_birthday,
            "부처님오신날",
            "음력공휴일"
        )


        # -------------------------------------------------
        # 추석
        # 음력 8월 15일 전날 / 당일 / 다음날
        # -------------------------------------------------

        chuseok = lunar_to_solar(
            year,
            8,
            15
        )

        add_holiday(
            rows,
            chuseok
            - pd.Timedelta(days=1),
            "추석",
            "음력공휴일"
        )

        add_holiday(
            rows,
            chuseok,
            "추석",
            "음력공휴일"
        )

        add_holiday(
            rows,
            chuseok
            + pd.Timedelta(days=1),
            "추석",
            "음력공휴일"
        )


    holidays_df = pd.DataFrame(
        rows
    )

    holidays_df = (
        holidays_df
        .sort_values(
            "날짜"
        )
        .reset_index(
            drop=True
        )
    )

    return holidays_df


# =========================================================
# CSV 생성
# =========================================================

holidays_df = create_holidays(
    START_YEAR,
    END_YEAR
)


OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


holidays_df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d"
)


# =========================================================
# 결과 확인
# =========================================================

print(
    "============================================"
)

print(
    "공휴일 CSV 생성 완료"
)

print(
    "============================================"
)

print(
    "기간:",
    START_YEAR,
    "~",
    END_YEAR
)

print(
    "저장 위치:",
    OUTPUT_PATH
)

print(
    "총 행 수:",
    len(holidays_df)
)


print()

print(
    "===== 2026년 확인 ====="
)


check_2026 = holidays_df[
    holidays_df[
        "날짜"
    ].dt.year == 2026
]


print(
    check_2026.to_string(
        index=False
    )
)