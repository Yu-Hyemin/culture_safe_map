import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


KDCA_ARI_URL = 'https://dportal.kdca.go.kr/pot/is/st/ari.do'


# =========================================================
# KDCA 급성호흡기감염증 주간 통계 수집
# =========================================================

def get_kdca_ari_table(
    start_year,
    start_week,
    end_year,
    end_week,
    wait_seconds=3
):

    options = webdriver.ChromeOptions()

    # 현재는 테스트 중이므로 브라우저 화면이 보이도록 유지
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(
        options=options
    )

    try:

        # -------------------------------------------------
        # 1. 페이지 접속
        # -------------------------------------------------

        driver.get(KDCA_ARI_URL)

        WebDriverWait(
            driver,
            20
        ).until(
            EC.presence_of_element_located(
                (By.ID, 'startYear')
            )
        )

        # -------------------------------------------------
        # 2. 조회기간 설정
        # -------------------------------------------------

        Select(
            driver.find_element(
                By.ID,
                'startYear'
            )
        ).select_by_visible_text(
            f'{start_year}년'
        )

        Select(
            driver.find_element(
                By.ID,
                'startWeek'
            )
        ).select_by_visible_text(
            f'{int(start_week):02d}주'
        )

        Select(
            driver.find_element(
                By.ID,
                'endYear'
            )
        ).select_by_visible_text(
            f'{end_year}년'
        )

        Select(
            driver.find_element(
                By.ID,
                'endWeek'
            )
        ).select_by_visible_text(
            f'{int(end_week):02d}주'
        )

        # -------------------------------------------------
        # 3. 감염병 구분 / 연령 전체 선택
        # -------------------------------------------------

        Select(
            driver.find_element(
                By.ID,
                'infectiousGubun'
            )
        ).select_by_visible_text(
            '전체'
        )

        Select(
            driver.find_element(
                By.ID,
                'age1'
            )
        ).select_by_visible_text(
            '전체'
        )

        # -------------------------------------------------
        # 4. 통계작성 클릭
        # -------------------------------------------------

        search_button = driver.find_element(
            By.ID,
            'searchBtn'
        )

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            search_button
        )

        driver.execute_script(
            "arguments[0].click();",
            search_button
        )

        # 결과 렌더링 대기
        time.sleep(wait_seconds)

        # -------------------------------------------------
        # 5. 결과 테이블 대기
        # -------------------------------------------------

        table = WebDriverWait(
            driver,
            60
        ).until(
            EC.presence_of_element_located(
                (By.ID, 'table')
            )
        )

        rows = table.find_elements(
            By.CSS_SELECTOR,
            'tbody tr'
        )

        # -------------------------------------------------
        # 6. 데이터 읽기
        # -------------------------------------------------

        records = []

        for row in rows:

            cells = row.find_elements(
                By.TAG_NAME,
                'td'
            )

            values = [
                cell.get_attribute(
                    'textContent'
                ).strip()
                for cell in cells
            ]

            # 사이트 구조 변경 감지
            if len(values) != 14:
                raise ValueError(
                    f'KDCA 결과 테이블 컬럼 수가 예상과 다릅니다. '
                    f'예상: 14개 / 실제: {len(values)}개 / '
                    f'값: {values}'
                )

            records.append(values)

        # -------------------------------------------------
        # 7. DataFrame 생성
        # -------------------------------------------------

        columns = [
            '연도',
            '주차',
            '계',
            '마이코플라즈마균',
            '클라미디아균',
            '아데노바이러스',
            '사람보카바이러스',
            '파라인플루엔자바이러스',
            '호흡기세포융합바이러스',
            '리노바이러스',
            '사람메타뉴모바이러스',
            '사람코로나바이러스',
            '인플루엔자바이러스',
            '코로나19'
        ]

        ari_df = pd.DataFrame(
            records,
            columns=columns
        )

        # -------------------------------------------------
        # 8. 집계 중 행 제거
        # -------------------------------------------------

        ari_df = ari_df[
            ari_df['계'] != '집계 중'
        ].copy()

        # -------------------------------------------------
        # 9. 연도 / 주차 숫자형 변환
        # -------------------------------------------------

        ari_df['연도'] = (
            ari_df['연도']
            .astype(int)
        )

        ari_df['주차'] = (
            ari_df['주차']
            .astype(int)
        )

        # -------------------------------------------------
        # 10. 환자수 컬럼 숫자형 변환
        # -------------------------------------------------

        numeric_columns = [
            '계',
            '마이코플라즈마균',
            '클라미디아균',
            '아데노바이러스',
            '사람보카바이러스',
            '파라인플루엔자바이러스',
            '호흡기세포융합바이러스',
            '리노바이러스',
            '사람메타뉴모바이러스',
            '사람코로나바이러스',
            '인플루엔자바이러스',
            '코로나19'
        ]

        for column in numeric_columns:

            ari_df[column] = (
                ari_df[column]
                .str.replace(
                    ',',
                    '',
                    regex=False
                )
                .astype(int)
            )

        # -------------------------------------------------
        # 11. 정렬
        # -------------------------------------------------

        ari_df = (
            ari_df
            .sort_values(
                ['연도', '주차']
            )
            .reset_index(
                drop=True
            )
        )

        return ari_df

    finally:

        driver.quit()