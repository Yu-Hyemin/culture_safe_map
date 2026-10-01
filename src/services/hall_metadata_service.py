from pathlib import Path

import pandas as pd


# =========================================================
# hall_metadata 저장 경로
# =========================================================

HALL_METADATA_PATH = Path(
    'data/hall_metadata.csv'
)


# =========================================================
# hall_metadata 갱신
#
# 기준:
# - 공연시설ID + 공연장ID
#
# 기존 공연장:
# - 기존 값 유지
#
# 신규 공연장:
# - 공연장명은 performance_detail 기준
# - 장소유형은 기본 '실내'
# =========================================================

def update_hall_metadata(
    hall_detail_df,
    metadata_path=HALL_METADATA_PATH
):

    id_cols = [
        '공연시설ID',
        '공연장ID'
    ]

    required_cols = [
        '공연시설ID',
        '공연장ID',
        '공연장명'
    ]

    # -------------------------------------------------
    # 1. 필요한 컬럼 확인
    # -------------------------------------------------

    for col in required_cols:

        if col not in hall_detail_df.columns:

            raise ValueError(
                f'hall_detail_df에 '
                f'{col} 컬럼이 없습니다.'
            )

    # -------------------------------------------------
    # 2. 현재 공연에서 고유 공연장 목록 생성
    # -------------------------------------------------

    current_halls_df = (
        hall_detail_df[
            required_cols
        ]
        .dropna(
            subset=id_cols
        )
        .drop_duplicates(
            subset=id_cols,
            keep='first'
        )
        .reset_index(
            drop=True
        )
    )

    # -------------------------------------------------
    # 3. 기존 hall_metadata 읽기
    # -------------------------------------------------

    if metadata_path.exists():

        hall_metadata_df = pd.read_csv(
            metadata_path,
            encoding='utf-8-sig'
        )

    else:

        hall_metadata_df = pd.DataFrame(
            columns=[
                '공연시설ID',
                '공연장ID',
                '공연장명',
                '장소유형'
            ]
        )

    # -------------------------------------------------
    # 4. 기존 데이터 중복 정리
    # -------------------------------------------------

    hall_metadata_df = (
        hall_metadata_df
        .drop_duplicates(
            subset=id_cols,
            keep='first'
        )
        .reset_index(
            drop=True
        )
    )

    # -------------------------------------------------
    # 5. 기존 공연장 ID 조합 확인
    # -------------------------------------------------

    existing_keys = set(
        zip(
            hall_metadata_df[
                '공연시설ID'
            ],
            hall_metadata_df[
                '공연장ID'
            ]
        )
    )

    # -------------------------------------------------
    # 6. 신규 공연장만 추출
    # -------------------------------------------------

    new_halls_df = (
        current_halls_df[
            ~current_halls_df.apply(
                lambda row: (
                    row['공연시설ID'],
                    row['공연장ID']
                )
                in existing_keys,
                axis=1
            )
        ]
        .copy()
    )

    # -------------------------------------------------
    # 7. 신규 공연장 기본 장소유형 = 실내
    # -------------------------------------------------

    new_halls_df[
        '장소유형'
    ] = '실내'

    # -------------------------------------------------
    # 8. 신규 공연장 추가
    # -------------------------------------------------

    if not new_halls_df.empty:

        hall_metadata_df = pd.concat(
            [
                hall_metadata_df,
                new_halls_df
            ],
            ignore_index=True
        )

    # -------------------------------------------------
    # 9. 최종 컬럼 순서
    # -------------------------------------------------

    hall_metadata_df = (
        hall_metadata_df[
            [
                '공연시설ID',
                '공연장ID',
                '공연장명',
                '장소유형'
            ]
        ]
        .drop_duplicates(
            subset=id_cols,
            keep='first'
        )
        .reset_index(
            drop=True
        )
    )

    # -------------------------------------------------
    # 10. 저장
    # -------------------------------------------------

    metadata_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    hall_metadata_df.to_csv(
        metadata_path,
        index=False,
        encoding='utf-8-sig'
    )

    print(
        '[hall_metadata] '
        f'기존/전체 {len(hall_metadata_df)}개 '
        f'- 신규 추가 {len(new_halls_df)}개'
    )

    return hall_metadata_df