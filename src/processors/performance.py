import re
from pathlib import Path

import pandas as pd


# =========================================================
# 설정
# =========================================================

DEFAULT_HOLIDAY_PATH = Path(
    "data/holidays.csv"
)


WEEKDAY_MAP = {
    "월요일": 0,
    "화요일": 1,
    "수요일": 2,
    "목요일": 3,
    "금요일": 4,
    "토요일": 5,
    "일요일": 6,
}


# =========================================================
# 법정공휴일 CSV 로드
#
# data/holidays.csv
#
# 기준:
# - 2014 ~ 2040
# - 대체공휴일 제외
# - 선거일 제외
# - 임시공휴일 제외
# - 2026년부터 노동절 / 제헌절 포함
#
# 같은 날짜에 공휴일이 여러 개 있어도
# 공연일수 계산에서는 1일로 처리
# =========================================================

def load_holiday_dates(
    holiday_path=DEFAULT_HOLIDAY_PATH
):

    holiday_path = Path(
        holiday_path
    )

    if not holiday_path.exists():

        raise FileNotFoundError(
            f"공휴일 파일을 찾을 수 없습니다: "
            f"{holiday_path}"
        )

    holiday_df = pd.read_csv(
        holiday_path
    )

    if "날짜" not in holiday_df.columns:

        raise ValueError(
            "holidays.csv에 "
            "'날짜' 컬럼이 없습니다."
        )

    holiday_df["날짜"] = pd.to_datetime(
        holiday_df["날짜"],
        errors="coerce"
    )

    holiday_df = holiday_df.dropna(
        subset=["날짜"]
    )

    holiday_dates = set(
        holiday_df["날짜"]
        .dt.normalize()
        .tolist()
    )

    return holiday_dates


# =========================================================
# 공연일정 문자열 → 공연 요일 추출
#
# 예)
#
# 금요일(19:00)
# → {4}
#
# 화요일 ~ 금요일(19:30)
# → {1, 2, 3, 4}
#
# 토요일 ~ 일요일(...)
# → {5, 6}
#
# pandas weekday:
# 월=0 ... 일=6
# =========================================================

def parse_performance_weekdays(
    schedule
):

    if pd.isna(schedule):
        return set()

    schedule = str(
        schedule
    )

    weekdays = set()

    # -----------------------------------------------------
    # 요일 범위 처리
    # 예: 월요일 ~ 금요일
    # -----------------------------------------------------

    range_pattern = (
        r"(월요일|화요일|수요일|목요일|"
        r"금요일|토요일|일요일)"
        r"\s*~\s*"
        r"(월요일|화요일|수요일|목요일|"
        r"금요일|토요일|일요일)"
    )

    matches = re.findall(
        range_pattern,
        schedule
    )

    for start_name, end_name in matches:

        start_idx = WEEKDAY_MAP[
            start_name
        ]

        end_idx = WEEKDAY_MAP[
            end_name
        ]

        # 일반 범위
        # 예: 월 ~ 금
        if start_idx <= end_idx:

            for weekday in range(
                start_idx,
                end_idx + 1
            ):

                weekdays.add(
                    weekday
                )

        # 주말을 넘어가는 범위 대비
        # 예: 금 ~ 월
        else:

            for weekday in range(
                start_idx,
                7
            ):

                weekdays.add(
                    weekday
                )

            for weekday in range(
                0,
                end_idx + 1
            ):

                weekdays.add(
                    weekday
                )


    # -----------------------------------------------------
    # 개별 요일 처리
    #
    # 범위 안의 요일이 다시 들어가도
    # set이므로 중복 없음
    # -----------------------------------------------------

    for weekday_name, weekday_num in (
        WEEKDAY_MAP.items()
    ):

        if weekday_name in schedule:

            weekdays.add(
                weekday_num
            )


    return weekdays


# =========================================================
# HOL 포함 여부
# =========================================================

def has_hol_schedule(
    schedule
):

    if pd.isna(schedule):
        return False

    return (
        "HOL"
        in str(schedule).upper()
    )


# =========================================================
# 공연 1건의 실제 공연일수 계산
#
# 현재 임시 HOL 정책
#
# HOL 있음
# → 기본 공연요일 + 법정공휴일
#
# HOL 없음
# → 기본 공연요일 - 법정공휴일
#
# 하루 여러 회차
# → 1일
#
# 같은 날짜에 공휴일 여러 개
# → 1일
# =========================================================

def calculate_performance_days(
    start_date,
    end_date,
    schedule,
    holiday_dates
):

    start_date = pd.to_datetime(
        start_date,
        errors="coerce"
    )

    end_date = pd.to_datetime(
        end_date,
        errors="coerce"
    )

    if (
        pd.isna(start_date)
        or pd.isna(end_date)
    ):
        return pd.NA

    start_date = start_date.normalize()
    end_date = end_date.normalize()

    if end_date < start_date:
        return pd.NA


    weekdays = parse_performance_weekdays(
        schedule
    )

    if (
            not weekdays
            and not has_hol_schedule(schedule)
    ):
        return pd.NA


    # -----------------------------------------------------
    # 공연 전체 기간 날짜 생성
    # -----------------------------------------------------

    all_dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D"
    )


    # -----------------------------------------------------
    # 기본 공연요일에 해당하는 날짜
    # -----------------------------------------------------

    performance_dates = {
        date.normalize()
        for date in all_dates
        if date.weekday() in weekdays
    }


    # -----------------------------------------------------
    # 공연기간 안의 법정공휴일
    # -----------------------------------------------------

    period_holidays = {
        holiday_date
        for holiday_date in holiday_dates
        if (
            start_date
            <= holiday_date
            <= end_date
        )
    }


    # -----------------------------------------------------
    # HOL 규칙
    # -----------------------------------------------------

    if has_hol_schedule(
        schedule
    ):

        final_dates = (
            performance_dates
            | period_holidays
        )

    else:

        final_dates = (
            performance_dates
            - period_holidays
        )


    return len(
        final_dates
    )


# =========================================================
# performance_master 전체에 공연일수 추가
# =========================================================

def add_performance_days(
    performance_master_df,
    holiday_path=DEFAULT_HOLIDAY_PATH
):

    df = performance_master_df.copy()

    holiday_dates = load_holiday_dates(
        holiday_path
    )

    df["공연일수"] = (
        df.apply(
            lambda row: calculate_performance_days(
                start_date=row[
                    "공연시작일"
                ],
                end_date=row[
                    "공연종료일"
                ],
                schedule=row[
                    "공연일정"
                ],
                holiday_dates=holiday_dates
            ),
            axis=1
        )
        .astype(
            "Int64"
        )
    )

    return df


# =========================================================
# 공연정보 + 공연장정보 + 지역정보 + 장소유형 결합
# =========================================================

def build_performance_master(
    performance_detail_df,
    hall_detail_df,
    facility_list_df,
    hall_metadata_df
):

    hall_detail_df = (
        hall_detail_df.copy()
    )

    performance_detail_df = (
        performance_detail_df.copy()
    )

    facility_list_df = (
        facility_list_df.copy()
    )

    hall_metadata_df = (
        hall_metadata_df.copy()
    )


    # -----------------------------------------------------
    # 공연장 좌석수 숫자형 변환
    # -----------------------------------------------------

    hall_detail_df[
        "공연장좌석수"
    ] = pd.to_numeric(
        hall_detail_df[
            "공연장좌석수"
        ]
        .astype(str)
        .str.replace(
            ",",
            "",
            regex=False
        ),
        errors="coerce"
    )


    # -----------------------------------------------------
    # 공연시설 지역정보 추가
    # -----------------------------------------------------

    hall_detail_df = (
        hall_detail_df.merge(
            facility_list_df[
                [
                    "공연시설ID",
                    "지역_시도",
                    "지역_구군",
                ]
            ],
            on="공연시설ID",
            how="left"
        )
    )


    # -----------------------------------------------------
    # 공연정보 + 공연장정보 결합
    # -----------------------------------------------------

    performance_master_df = (
        performance_detail_df.merge(
            hall_detail_df,
            on=[
                "공연시설ID",
                "공연장ID",
            ],
            how="left"
        )
    )


    # -----------------------------------------------------
    # hall_metadata 장소유형 결합
    # -----------------------------------------------------

    performance_master_df = (
        performance_master_df.merge(
            hall_metadata_df[
                [
                    "공연시설ID",
                    "공연장ID",
                    "장소유형",
                ]
            ],
            on=[
                "공연시설ID",
                "공연장ID",
            ],
            how="left"
        )
    )


    # 신규 / 미매칭 공연장은
    # 기본값 실내
    performance_master_df[
        "장소유형"
    ] = (
        performance_master_df[
            "장소유형"
        ]
        .fillna(
            "실내"
        )
    )


    return performance_master_df


# =========================================================
# 위험요소 기본값 생성
#
# 장소유형
# → hall_metadata 값 사용
#
# 환기정도
# → 실내 기본 보통
# → 실외 해당없음
#
# 밀집도
# → 기본값 100
#
# 예방수준
# → 기본값 보통
# =========================================================

def add_risk_variables(
    performance_master_df
):

    df = performance_master_df.copy()


    # -----------------------------------------------------
    # 장소유형 정리
    # -----------------------------------------------------

    df["장소유형"] = (
        df["장소유형"]
        .fillna(
            "실내"
        )
    )


    # -----------------------------------------------------
    # 환기정도
    # -----------------------------------------------------

    df["환기정도"] = "보통"

    df.loc[
        df["장소유형"] == "실외",
        "환기정도"
    ] = "해당없음"


    # -----------------------------------------------------
    # 밀집도
    #
    # 현재 실제 참여자 수 미확보
    # → 최대 조건 100% 사용
    # -----------------------------------------------------

    df["밀집도"] = 100.0


    # -----------------------------------------------------
    # 예방수준
    # -----------------------------------------------------

    df["예방수준"] = "보통"


    return df


# =========================================================
# 장소유형 점수
#
# 실내 = 10
# 실외 = 0
# =========================================================

def get_place_type_score(
    value
):

    if value == "실내":
        return 10

    if value == "실외":
        return 0

    return pd.NA


# =========================================================
# 환기정도 점수
#
# 해당없음 = 0
# 양호     = 3
# 보통     = 6
# 미흡     = 10
# =========================================================

def get_ventilation_score(
    value
):

    score_map = {
        "해당없음": 0,
        "양호": 3,
        "보통": 6,
        "미흡": 10,
    }

    return score_map.get(
        value,
        pd.NA
    )


# =========================================================
# 밀집도 점수
#
# 25 미만       = 0
# 25 ~ 50 미만  = 3
# 50 ~ 75       = 6
# 75 초과       = 10
# =========================================================

def get_density_score(
    value
):

    if pd.isna(value):
        return pd.NA

    value = float(
        value
    )

    if value < 25:
        return 0

    elif value < 50:
        return 3

    elif value <= 75:
        return 6

    else:
        return 10


# =========================================================
# 공연일수 점수
#
# 1일 이하  = 2.5
# 2 ~ 3일   = 5
# 4 ~ 6일   = 7.5
# 7일 이상  = 10
# =========================================================

def get_performance_days_score(
    value
):

    if pd.isna(value):
        return pd.NA

    value = int(
        value
    )

    if value <= 1:
        return 2.5

    elif value <= 3:
        return 5.0

    elif value <= 6:
        return 7.5

    else:
        return 10.0


# =========================================================
# 예방수준 점수
#
# 낮음 = 10
# 보통 = 5
# 높음 = 0
# =========================================================

def get_prevention_score(
    value
):

    score_map = {
        "낮음": 10,
        "보통": 5,
        "높음": 0,
    }

    return score_map.get(
        value,
        pd.NA
    )


# =========================================================
# 위험요소 점수 추가
# =========================================================

def add_risk_scores(
    performance_master_df
):

    df = performance_master_df.copy()

    df["장소유형_점수"] = pd.to_numeric(
        df["장소유형"].apply(
            get_place_type_score
        ),
        errors="coerce"
    ).astype("Float64")

    df["환기정도_점수"] = pd.to_numeric(
        df["환기정도"].apply(
            get_ventilation_score
        ),
        errors="coerce"
    ).astype("Float64")

    df["밀집도_점수"] = pd.to_numeric(
        df["밀집도"].apply(
            get_density_score
        ),
        errors="coerce"
    ).astype("Float64")

    df["공연일수_점수"] = pd.to_numeric(
        df["공연일수"].apply(
            get_performance_days_score
        ),
        errors="coerce"
    ).astype("Float64")

    df["예방수준_점수"] = pd.to_numeric(
        df["예방수준"].apply(
            get_prevention_score
        ),
        errors="coerce"
    ).astype("Float64")


    return df


# =========================================================
# 행사환경 점수
#
# 장소유형 + 환기정도 + 밀집도
# 단순 평균
# =========================================================

def add_environment_score(
    performance_master_df
):

    df = performance_master_df.copy()

    df[
        "행사환경_점수"
    ] = (
        (
            df[
                "장소유형_점수"
            ]
            +
            df[
                "환기정도_점수"
            ]
            +
            df[
                "밀집도_점수"
            ]
        )
        / 3
    )

    df["행사환경_점수"] = pd.to_numeric(
        df["행사환경_점수"],
        errors="coerce"
    ).astype("Float64")

    return df


# =========================================================
# 행사위해점수
#
# 변경 가중치
#
# 행사환경 = 0.596
# 공연일수 = 0.150
# 예방수준 = 0.254
#
# 합계 = 1.000
# =========================================================

def add_event_risk_score(
    performance_master_df
):

    df = performance_master_df.copy()

    df[
        "행사위해점수"
    ] = (
        df[
            "행사환경_점수"
        ]
        * 0.596
        +
        df[
            "공연일수_점수"
        ]
        * 0.150
        +
        df[
            "예방수준_점수"
        ]
        * 0.254
    )

    df["행사위해점수"] = pd.to_numeric(
        df["행사위해점수"],
        errors="coerce"
    ).astype("Float64")

    return df


# =========================================================
# 공연 위해요소 전체 계산
#
# 순서:
#
# 1. 공연일수 계산
# 2. 위험요소 기본값 생성
# 3. 요소별 점수 계산
# 4. 행사환경 점수 계산
# 5. 행사위해점수 계산
# =========================================================

def add_performance_risk_features(
    performance_master_df,
    holiday_path=DEFAULT_HOLIDAY_PATH
):

    df = performance_master_df.copy()


    df = add_performance_days(
        df,
        holiday_path=holiday_path
    )


    df = add_risk_variables(
        df
    )


    df = add_risk_scores(
        df
    )


    df = add_environment_score(
        df
    )


    df = add_event_risk_score(
        df
    )


    return df