import re
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.processors.disease import get_week_dates


HOME_URL = (
    'https://fluon-web-ui-revision-v52-final-dat.vercel.app/'
)

REGION_URL = (
    'https://fluon-web-ui-revision-v52-final-dat.vercel.app/'
    'clinical/region'
)


# =========================================================
# Chrome Driver 생성
# =========================================================

def create_driver():

    options = webdriver.ChromeOptions()

    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(
        options=options
    )

    return driver


# =========================================================
# FluON 지역별 ILI 수집
#
# 반환 컬럼
# - 연도
# - 주차
# - 주차시작일
# - 주차종료일
# - 업데이트일자
# - 지역_시도
# - ILI분율
# =========================================================

def get_fluon_region_ili(
    page_delay=2.0
):

    driver = create_driver()

    try:

        # -------------------------------------------------
        # 1. 홈페이지 → 업데이트일자 확인
        # -------------------------------------------------

        driver.get(HOME_URL)

        update_element = WebDriverWait(
            driver,
            20
        ).until(
            lambda d: d.find_element(
                By.CSS_SELECTOR,
                '.overviewUpdateMeta strong'
            )
        )

        update_text = update_element.text

        update_match = re.search(
            r'\d{4}-\d{2}-\d{2}',
            update_text
        )

        if update_match is None:
            raise ValueError(
                'FluON 업데이트일자를 찾을 수 없습니다.'
            )

        update_date = pd.to_datetime(
            update_match.group()
        )

        year = update_date.year

        # 다음 페이지 요청 전 대기
        time.sleep(page_delay)

        # -------------------------------------------------
        # 2. 지역 페이지 → 주차 확인
        # -------------------------------------------------

        driver.get(REGION_URL)

        meta = WebDriverWait(
            driver,
            20
        ).until(
            lambda d: (
                element
                if (
                    element := d.find_element(
                        By.CSS_SELECTOR,
                        '.regionSelectedMeta em'
                    )
                ).text
                and '—' not in element.text
                else False
            )
        )

        meta_text = meta.text

        week_match = re.search(
            r'(\d+)주',
            meta_text
        )

        if week_match is None:
            raise ValueError(
                'FluON 주차를 찾을 수 없습니다.'
            )

        week = int(
            week_match.group(1)
        )

        # -------------------------------------------------
        # 3. 지역별 ILI 값 로딩
        # -------------------------------------------------

        region_elements = WebDriverWait(
            driver,
            20
        ).until(
            lambda d: d.find_elements(
                By.CSS_SELECTOR,
                '.koreaValueLabel'
            )
        )

        # -------------------------------------------------
        # 4. 주차 날짜 계산
        # -------------------------------------------------

        week_start, week_end = (
            get_week_dates(
                year,
                week
            )
        )

        # -------------------------------------------------
        # 5. 지역별 데이터 저장
        #
        # 여기서는 서버 요청을 새로 보내는 게 아니라
        # 이미 로딩된 DOM 요소를 읽는 것이므로
        # 반복문 안에 sleep을 넣지 않음
        # -------------------------------------------------

        records = []

        for element in region_elements:

            region = (
                element
                .find_element(
                    By.TAG_NAME,
                    'span'
                )
                .text
            )

            ili_text = (
                element
                .find_element(
                    By.TAG_NAME,
                    'strong'
                )
                .text
            )

            records.append({
                '연도': year,
                '주차': week,
                '주차시작일': week_start,
                '주차종료일': week_end,
                '업데이트일자': update_date,
                '지역_시도': region,
                'ILI분율': float(ili_text)
            })

        ili_region_df = pd.DataFrame(
            records
        )

        return ili_region_df

    finally:

        driver.quit()