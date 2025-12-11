# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
# openai 라이브러리 임포트 (설치 및 환경변수 필요)
from openai import OpenAI

from utils.file_loader import load_expense_csv
from utils.category_mapper import apply_category_mapping

# 페이지 설정
st.set_page_config(
    page_title="개인 지출 분석 대시보드",
    layout="wide"
)

st.title("💸 개인 지출 분석 대시보드")
st.write("CSV 파일을 업로드하면 **키워드 기반 자동 카테고리 분류**와 **월별/카테고리별 분석** 결과를 보여줍니다.")

# --- 파일 업로드 영역 ---
# 🔧 넘버링 "1." 제거
st.sidebar.header("CSV 파일 업로드")
uploaded_file = st.sidebar.file_uploader("지출 내역 CSV 파일을 업로드하세요", type=["csv"])

# --- CSV 형식 안내 + 샘플 파일 다운로드 ---
with st.sidebar.expander("📄 CSV 형식 안내", expanded=False):
    st.markdown(
        """
        최소 컬럼:
        - `date` 또는 `날짜` : 지출 날짜 (예: 2025-09-01)
        - `description` 또는 `내용`/`메모` : 지출 내용/메모
        - `amount` 또는 `금액` : 지출 금액 (숫자)
        
        예시:
        ```csv
        date,description,amount
        2025-09-01,점심 식사,12000
        2025-09-01,지하철 교통비,1450
        2025-09-02,온라인 강의 수강료,45000
        ```
        """
    )

    # 샘플 CSV 데이터 생성
    sample_df = pd.DataFrame(
        {
            "date": [
                "2025-09-01",
                "2025-09-01",
                "2025-09-02",
                "2025-10-05",
                "2025-11-10",
            ],
            "description": [
                "점심 식사",
                "지하철 교통비",
                "온라인 강의 수강료",
                "편의점 간식",
                "월세",
            ],
            "amount": [
                12000,
                1450,
                45000,
                3800,
                500000,
            ],
        }
    )

    # CSV 문자열로 변환 (UTF-8)
    sample_csv = sample_df.to_csv(index=False)

    st.download_button(
        label="📥 샘플 CSV 다운로드",
        data=sample_csv,
        file_name="expense_sample.csv",
        mime="text/csv",
        help="이 샘플 파일 형식을 그대로 사용해서 지출 내역을 입력해 보세요.",
    )

# --- 업로드된 파일 처리 ---
if uploaded_file is not None:
    # 1) CSV 로드/전처리 (인코딩 자동 처리 포함)
    try:
        df = load_expense_csv(uploaded_file)
    except Exception as e:
        st.error(f"CSV 파일을 불러오는 중 오류가 발생했습니다: {e}")
        st.stop()

    # 2) 카테고리 자동 분류
    df = apply_category_mapping(df, text_col="description", category_col="category")

    # 3) 월(Year-Month) 컬럼 생성
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    # 🔧 날짜 표시 형식: 시각 제거(연-월-일만 표시)
    preview_df = df.copy()
    preview_df["date"] = preview_df["date"].dt.strftime("%Y-%m-%d")

    st.subheader("📋 업로드 데이터 미리보기 (자동 카테고리 포함)")
    st.dataframe(preview_df.head(20), use_container_width=True)

    # 4) 월별 총 지출 분석
    st.markdown("---")
    st.subheader("📆 월별 지출 분석")

    monthly_summary = (
        df.groupby("year_month")["amount"]
        .sum()
        .reset_index()
        .sort_values("year_month")
    )

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.write("**월별 총 지출 표**")
        st.dataframe(monthly_summary, use_container_width=True)

    with col2:
        st.write("**월별 총 지출 차트**")
        # 🔧 Plotly 막대 그래프 + 다양한 색상
        fig_monthly = px.bar(
            monthly_summary,
            x="year_month",
            y="amount",
            color="year_month",
            title="월별 총 지출",
            labels={"year_month": "월", "amount": "지출 금액"}
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    # 5) 카테고리별 지출 분석 (전체 기간)
    st.markdown("---")
    st.subheader("🏷 카테고리별 지출 분석 (전체 기간)")

    category_summary = (
        df.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    col3, col4 = st.columns([1, 1.2])

    with col3:
        st.write("**카테고리별 총 지출 표**")
        st.dataframe(category_summary, use_container_width=True)

    with col4:
        st.write("**카테고리별 지출 비중 (파이 차트)**")
        # 🔧 파이 차트로 비중 확인 + 다양한 색상
        fig_cat_pie = px.pie(
            category_summary,
            names="category",
            values="amount",
            color="category",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_cat_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_cat_pie, use_container_width=True)

    # 6) 월별 × 카테고리별 피벗 분석
    st.markdown("---")
    st.subheader("📊 월별 × 카테고리별 지출 분석")

    pivot_table = (
        df.pivot_table(
            index="year_month",
            columns="category",
            values="amount",
            aggfunc="sum",
            fill_value=0
        )
        .sort_index()
    )

    st.write("**월별 × 카테고리별 지출 피벗 테이블**")
    st.dataframe(pivot_table, use_container_width=True)

    st.write("**월별 × 카테고리별 추이 차트**")
    # Streamlit line_chart는 카테고리별로 자동으로 다른 색을 사용
    st.line_chart(pivot_table)

    # 7) 특정 월 선택해서 카테고리 상세보기 + 세부 지출 내역
    st.markdown("---")
    st.subheader("🔍 특정 월의 카테고리별 지출 보기")

    month_options = sorted(df["year_month"].unique())
    selected_month = st.selectbox("월 선택", options=month_options)

    month_df = df[df["year_month"] == selected_month]

    month_cat_summary = (
        month_df.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    col5, col6 = st.columns([1, 1.2])

    with col5:
        st.write(f"**{selected_month} 카테고리별 지출 표**")
        st.dataframe(month_cat_summary, use_container_width=True)

    with col6:
        st.write(f"**{selected_month} 카테고리별 지출 차트**")
        # 🔧 Plotly 막대 그래프 + 카테고리별 색상
        fig_month_cat = px.bar(
            month_cat_summary,
            x="category",
            y="amount",
            color="category",
            title=f"{selected_month} 카테고리별 지출",
            labels={"category": "카테고리", "amount": "지출 금액"}
        )
        st.plotly_chart(fig_month_cat, use_container_width=True)

    # 🔧 월별 카테고리별 분석에서 카테고리 선택 시 세부 지출 내역 표시
    st.markdown("#### 📑 선택한 월·카테고리의 세부 지출 내역")

    if not month_cat_summary.empty:
        selected_category = st.selectbox(
            "카테고리 선택",
            options=month_cat_summary["category"].tolist()
        )

        detail_df = month_df[month_df["category"] == selected_category].copy()

        if detail_df.empty:
            st.info("해당 월/카테고리에 해당하는 지출 내역이 없습니다.")
        else:
            detail_df_display = detail_df[["date", "description", "amount", "category"]].copy()
            # 🔧 날짜 표시 형식: 연-월-일
            detail_df_display["date"] = detail_df_display["date"].dt.strftime("%Y-%m-%d")
            detail_df_display = detail_df_display.sort_values("date")

            total_amount = detail_df_display["amount"].sum()
            st.write(f"**총 {len(detail_df_display)}건, 합계 {total_amount:,.0f}원**")
            st.dataframe(detail_df_display, use_container_width=True)
    else:
        st.info("선택한 월에는 지출 데이터가 없습니다.")

    # ---------------------------------------------------
    # 8) GPT API를 활용한 요약 리포트 작성 기능
    # ---------------------------------------------------
    st.markdown("---")
    st.subheader("🧾 지출 요약 리포트")

    st.write("아래 버튼을 누르면 현재 업로드한 데이터를 기반으로 GPT가 지출 요약 리포트를 작성합니다.")

    if st.button("요약 리포트 작성"):
        with st.spinner("요약 리포트를 생성 중입니다..."):
            try:              
                # Streamlit secrets에 저장된 API 키 사용 예시
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

                # 모델에 전달할 요약용 텍스트 준비
                monthly_text = monthly_summary.to_string(index=False)
                category_text = category_summary.to_string(index=False)
                recent_20 = preview_df.sort_values("date").tail(20)
                recent_text = recent_20.to_string(index=False)

                prompt = f"""
다음은 한 사용자의 개인 지출 내역에 대한 요약 데이터입니다.

[월별 총 지출 요약]
{monthly_text}

[카테고리별 총 지출 요약]
{category_text}

[최근 20건 지출 상세 내역]
{recent_text}

위 정보를 바탕으로, 한국어로 다음 기준에 맞는 '지출 요약 리포트'를 작성해 주세요.

- 1~2문단 정도의 전체 요약 (총 지출 규모, 지출이 많은 달, 특징적인 패턴)
- 항목별 Bullet Point:
  - 지출이 특히 많은 카테고리와 그 이유/추정 원인
  - 절감 여지가 있어 보이는 카테고리
  - 긍정적인 지출 패턴 (예: 특정 월에 지출 감소 등)
- 마지막에 "다음 달을 위한 간단한 지출 관리 팁" 3가지 정도 제안

반말이 아닌, 부드러운 존댓말로 작성해 주세요.
"""

                response = client.chat.completions.create(
                    model="gpt-4.1-mini",  # 필요시 gpt-4.1 등으로 변경
                    messages=[
                        {"role": "system", "content": "당신은 개인 재무 코치를 돕는 분석가입니다."},
                        {"role": "user", "content": prompt},
                    ],
                )

                report_text = response.choices[0].message.content

                st.markdown("### 📄 생성된 지출 요약 리포트")
                st.markdown(report_text)

            except ImportError:
                st.error(
                    "openai 패키지가 설치되어 있지 않습니다. "
                    "`requirements.txt`에 `openai`를 추가한 뒤 다시 배포해 주세요."
                )
            except KeyError:
                st.error(
                    "`st.secrets['OPENAI_API_KEY']`를 찾을 수 없습니다. "
                    "Streamlit secrets에 OPENAI_API_KEY를 설정해 주세요."
                )
            except Exception as e:
                st.error(f"요약 리포트 생성 중 오류가 발생했습니다: {e}")

else:
    st.info("좌측 사이드바에서 CSV 파일을 업로드하면 분석 결과가 여기에 표시됩니다.")
