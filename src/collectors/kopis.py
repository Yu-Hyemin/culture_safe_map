import re
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET

from datetime import datetime
from dateutil.relativedelta import relativedelta


# =========================================================
# 공연시간 문자열 → 분 변환
#
# 예:
# "1시간 30분" → 90
# =========================================================

def runtime_to_minutes(runtime_text):

    if not runtime_text:
        return None

    hour_match = re.search(
        r'(\d+)\s*시간',
        runtime_text
    )

    minute_match = re.search(
        r'(\d+)\s*분',
        runtime_text
    )

    hours = (
        int(hour_match.group(1))
        if hour_match
        else 0
    )

    minutes = (
        int(minute_match.group(1))
        if minute_match
        else 0
    )

    total_minutes = (
        hours * 60
        + minutes
    )

    return (
        total_minutes
        if total_minutes > 0
        else None
    )


# =========================================================
# 오늘 기준 3개월 공연 ID 수집
#
# 정상 요청 간격:
# 0.2초
#
# 오류 발생 시:
# 2초 대기 후 1회 재시도
#
# 주의:
# HTTP 400을 목록 종료로 간주하지 않음.
# 중간 오류로 일부 데이터만 반환하는 것을 방지.
# =========================================================

def get_kopis_performance_ids(
    kopis_key,
    request_delay=0.12,
    retry_delay=2.0,
    max_retries=1,
    max_pages=None
):

    today = datetime.today()

    stdate = today.strftime(
        '%Y%m%d'
    )

    eddate = (
        today
        + relativedelta(months=3)
    ).strftime(
        '%Y%m%d'
    )

    url = (
        'http://www.kopis.or.kr/'
        'openApi/restful/pblprfr'
    )

    performance_ids = []

    page = 1
    rows_per_page = 100

    while True:

        # ---------------------------------------------
        # 테스트용 페이지 제한
        # ---------------------------------------------

        if (
            max_pages is not None
            and page > max_pages
        ):
            break

        params = {
            'service': kopis_key,
            'stdate': stdate,
            'eddate': eddate,
            'cpage': page,
            'rows': rows_per_page
        }

        attempt = 0

        # ---------------------------------------------
        # 페이지 요청 + 재시도
        # ---------------------------------------------

        while True:

            try:

                response = requests.get(
                    url,
                    params=params,
                    timeout=20
                )

                response.raise_for_status()

                root = ET.fromstring(
                    response.text
                )

                break

            except (
                requests.RequestException,
                ET.ParseError
            ):

                attempt += 1

                if attempt > max_retries:
                    raise

                time.sleep(
                    retry_delay
                )

        items = root.findall(
            'db'
        )

        # ---------------------------------------------
        # 데이터가 없으면 종료
        # ---------------------------------------------

        if not items:
            break

        # ---------------------------------------------
        # 공연ID 저장
        # ---------------------------------------------

        for item in items:

            performance_id = (
                item.findtext(
                    'mt20id'
                )
            )

            if performance_id:

                performance_ids.append(
                    performance_id
                )

        # ---------------------------------------------
        # 100건 미만이면 마지막 페이지
        #
        # 예:
        # 마지막 페이지가 82건이면
        # 다음 페이지를 호출하지 않고 종료
        # ---------------------------------------------

        if len(items) < rows_per_page:
            break

        page += 1

        # ---------------------------------------------
        # 다음 서버 요청 전 대기
        # ---------------------------------------------

        time.sleep(
            request_delay
        )

    performance_ids = list(
        dict.fromkeys(
            performance_ids
        )
    )

    return performance_ids


# =========================================================
# 공연 상세정보 수집
#
# 공연ID별 상세 API 호출
#
# 정상 요청 간격:
# 0.2초
#
# 실패한 ID는 반환하고
# performance_service.py에서 한 번 더 재시도
# =========================================================

def get_kopis_performance_details(
    kopis_key,
    performance_ids,
    request_delay=0.12
):

    records = []
    failed_ids = []

    for performance_id in performance_ids:

        url = (
            'http://www.kopis.or.kr/'
            'openApi/restful/'
            f'pblprfr/{performance_id}'
        )

        params = {
            'service': kopis_key
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=20
            )

            response.raise_for_status()

            root = ET.fromstring(
                response.text
            )

            item = root.find(
                'db'
            )

            if item is None:

                failed_ids.append(
                    performance_id
                )

            else:

                runtime = (
                    item.findtext(
                        'prfruntime'
                    )
                )

                records.append({
                    '공연ID':
                        item.findtext(
                            'mt20id'
                        ),

                    '공연시설ID':
                        item.findtext(
                            'mt10id'
                        ),

                    '공연장ID':
                        item.findtext(
                            'mt13id'
                        ),

                    '공연명':
                        item.findtext(
                            'prfnm'
                        ),

                    '공연장르':
                        item.findtext(
                            'genrenm'
                        ),

                    '공연시작일':
                        item.findtext(
                            'prfpdfrom'
                        ),

                    '공연종료일':
                        item.findtext(
                            'prfpdto'
                        ),

                    '공연시간':
                        runtime,

                    '공연시간_분':
                        runtime_to_minutes(
                            runtime
                        ),

                    '공연일정':
                        item.findtext(
                            'dtguidance'
                        )
                })

        except (
            requests.RequestException,
            ET.ParseError
        ):

            failed_ids.append(
                performance_id
            )

        # ---------------------------------------------
        # 공연별 서버 요청 사이 대기
        # ---------------------------------------------

        time.sleep(
            request_delay
        )

    performance_detail_df = (
        pd.DataFrame(
            records
        )
    )

    return (
        performance_detail_df,
        failed_ids
    )


# =========================================================
# 공연시설 목록에서 지역정보 수집
#
# 지역_시도 / 지역_구군 확보
#
# 정상 요청 간격:
# 0.2초
#
# 오류 발생 시:
# 2초 대기 후 1회 재시도
# =========================================================

def get_kopis_facility_list(
    kopis_key,
    hall_keys_df,
    request_delay=0.12,
    retry_delay=2.0,
    max_retries=1
):

    target_facility_ids = set(
        hall_keys_df[
            '공연시설ID'
        ]
        .dropna()
        .unique()
    )

    records = []

    found_facility_ids = set()

    page = 1
    rows_per_page = 100

    url = (
        'http://www.kopis.or.kr/'
        'openApi/restful/prfplc'
    )

    while True:

        params = {
            'service': kopis_key,
            'cpage': page,
            'rows': rows_per_page
        }

        attempt = 0

        # ---------------------------------------------
        # 페이지 요청 + 재시도
        # ---------------------------------------------

        while True:

            try:

                response = requests.get(
                    url,
                    params=params,
                    timeout=20
                )

                response.raise_for_status()

                root = ET.fromstring(
                    response.text
                )

                break

            except (
                requests.RequestException,
                ET.ParseError
            ):

                attempt += 1

                if attempt > max_retries:
                    raise

                time.sleep(
                    retry_delay
                )

        items = root.findall(
            'db'
        )

        # ---------------------------------------------
        # 데이터가 없으면 종료
        # ---------------------------------------------

        if not items:
            break

        # ---------------------------------------------
        # 필요한 시설만 저장
        # ---------------------------------------------

        for item in items:

            facility_id = (
                item.findtext(
                    'mt10id'
                )
            )

            if (
                facility_id
                in target_facility_ids
            ):

                records.append({
                    '공연시설ID':
                        facility_id,

                    '공연시설명':
                        item.findtext(
                            'fcltynm'
                        ),

                    '지역_시도':
                        item.findtext(
                            'sidonm'
                        ),

                    '지역_구군':
                        item.findtext(
                            'gugunnm'
                        )
                })

                found_facility_ids.add(
                    facility_id
                )

        # ---------------------------------------------
        # 필요한 시설을 전부 찾았으면 종료
        # ---------------------------------------------

        if (
            found_facility_ids
            == target_facility_ids
        ):
            break

        # ---------------------------------------------
        # 마지막 페이지면 종료
        # ---------------------------------------------

        if len(items) < rows_per_page:
            break

        page += 1

        # ---------------------------------------------
        # 다음 서버 요청 전 대기
        # ---------------------------------------------

        time.sleep(
            request_delay
        )

    facility_list_df = (
        pd.DataFrame(
            records
        )
        .drop_duplicates(
            subset='공연시설ID'
        )
        .reset_index(
            drop=True
        )
    )

    missing_facility_ids = (
        target_facility_ids
        - found_facility_ids
    )

    if missing_facility_ids:

        print(
            '[KOPIS] 시설목록에서 '
            '찾지 못한 공연시설ID:',
            sorted(
                missing_facility_ids
            )
        )

    return facility_list_df


# =========================================================
# 공연시설 상세정보에서
# 실제 사용하는 공연장 정보 수집
#
# 위도 / 경도 / 주소 / 좌석수
#
# 정상 요청 간격:
# 0.2초
#
# 실패 시설은 반환하고
# performance_service.py에서 한 번 더 재시도
# =========================================================

def get_kopis_hall_details(
    kopis_key,
    hall_keys_df,
    request_delay=0.12
):

    records = []
    failed_facilities = []

    facility_ids = (
        hall_keys_df[
            '공연시설ID'
        ]
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    for facility_id in facility_ids:

        url = (
            'http://www.kopis.or.kr/'
            'openApi/restful/'
            f'prfplc/{facility_id}'
        )

        params = {
            'service': kopis_key
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=20
            )

            response.raise_for_status()

            root = ET.fromstring(
                response.text
            )

            item = root.find(
                'db'
            )

            if item is None:

                failed_facilities.append(
                    facility_id
                )

            else:

                # -------------------------------------
                # 시설 공통 정보
                # -------------------------------------

                facility_address = (
                    item.findtext(
                        'adres'
                    )
                )

                facility_lat = (
                    item.findtext(
                        'la'
                    )
                )

                facility_lon = (
                    item.findtext(
                        'lo'
                    )
                )

                # -------------------------------------
                # 해당 시설에서
                # 실제 사용하는 공연장ID만 추출
                # -------------------------------------

                target_hall_ids = set(
                    hall_keys_df.loc[
                        (
                            hall_keys_df[
                                '공연시설ID'
                            ]
                            == facility_id
                        ),
                        '공연장ID'
                    ]
                )

                hall_items = (
                    item.findall(
                        './mt13s/mt13'
                    )
                )

                for hall in hall_items:

                    hall_id = (
                        hall.findtext(
                            'mt13id'
                        )
                    )

                    if (
                        hall_id
                        in target_hall_ids
                    ):

                        records.append({
                            '공연시설ID':
                                facility_id,

                            '공연시설위도':
                                facility_lat,

                            '공연시설경도':
                                facility_lon,

                            '공연시설주소':
                                facility_address,

                            '공연장ID':
                                hall_id,

                            '공연장명':
                                hall.findtext(
                                    'prfplcnm'
                                ),

                            '공연장좌석수':
                                hall.findtext(
                                    'seatscale'
                                )
                        })

        except (
            requests.RequestException,
            ET.ParseError
        ):

            failed_facilities.append(
                facility_id
            )

        # ---------------------------------------------
        # 시설별 서버 요청 사이 대기
        # ---------------------------------------------

        time.sleep(
            request_delay
        )

    hall_detail_df = (
        pd.DataFrame(
            records
        )
    )

    return (
        hall_detail_df,
        failed_facilities
    )