
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
from itertools import combinations
from collections import Counter

# ==========================================
# 1. 페이지 설정
# ==========================================

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.write(
    "송탄고 급식 데이터를 이용해 "
    "어떤 메뉴들이 함께 등장하는지 분석합니다."
)

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "it-teacher-go/data-share-/main/"
    "songtan_meals_184.csv"
)


# ==========================================
# 2. 데이터 불러오기
# ==========================================

@st.cache_data(ttl=3600)
def load_data():

    df = pd.read_csv(
        DATA_URL,
        encoding="utf-8-sig"
    )

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(
                f"CSV에 '{col}' 열이 없습니다."
            )

    # 중식 데이터만 사용
    df["식사"] = df["식사"].astype(str).str.strip()

    df = df[df["식사"] == "중식"].copy()

    # 괄호와 괄호 안의 내용 제거
    def clean_menu(menu):

        if pd.isna(menu):
            return []

        items = str(menu).split("|")

        cleaned = []

        for item in items:

            # 일반 괄호 제거
            item = re.sub(
                r"\([^)]*\)",
                "",
                item
            )

            # 전각 괄호 제거
            item = re.sub(
                r"（[^）]*）",
                "",
                item
            )

            item = item.strip()

            if item:
                cleaned.append(item)

        # 하루에 같은 메뉴가 중복 기록되어도 한 번만 계산
        return sorted(set(cleaned))

    df["메뉴목록"] = df["메뉴"].apply(clean_menu)

    # 메뉴가 없는 행 제외
    df = df[
        df["메뉴목록"].apply(len) > 0
    ].copy()

    return df


# ==========================================
# 3. 장바구니 분석
# ==========================================

@st.cache_data
def analyze_data(df):

    transactions = df["메뉴목록"].tolist()

    total_days = len(transactions)

    # 메뉴별 등장 횟수
    menu_count = Counter()

    # 두 메뉴가 함께 등장한 횟수
    pair_count = Counter()

    for basket in transactions:

        menu_count.update(basket)

        # 같은 날 등장한 메뉴의 모든 조합
        for pair in combinations(sorted(basket), 2):
            pair_count[pair] += 1

    total_menus = len(menu_count)

    # ======================================
    # 4. 연관 규칙 생성
    # ======================================

    rules = []

    for (a, b), count in pair_count.items():

        support = count / total_days

        # A → B
        confidence_ab = count / menu_count[a]

        support_b = menu_count[b] / total_days

        lift_ab = confidence_ab / support_b

        rules.append({
            "조건": a,
            "결과": b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
        confidence_ba = count / menu_count[b]

        support_a = menu_count[a] / total_days

        lift_ba = confidence_ba / support_a

        rules.append({
            "조건": b,
            "결과": a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return (
        rules_df,
        total_days,
        total_menus,
        len(pair_count),
        sorted(menu_count.keys())
    )


# ==========================================
# 5. 데이터 분석 실행
# ==========================================

try:

    with st.spinner("급식 데이터를 분석하고 있습니다..."):

        df = load_data()

        (
            rules_df,
            total_days,
            total_menus,
            total_pairs,
            menu_list
        ) = analyze_data(df)

except Exception as e:

    st.error(f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}")
    st.stop()


if rules_df.empty:

    st.warning("분석할 수 있는 메뉴 쌍이 없습니다.")
    st.stop()


# ==========================================
# 6. 전체 분석 결과 요약
# ==========================================

st.subheader("📊 분석 데이터")

col1, col2, col3 = st.columns(3)

col1.metric(
    "급식 일수",
    f"{total_days:,}일"
)

col2.metric(
    "메뉴 종류 수",
    f"{total_menus:,}개"
)

col3.metric(
    "함께 나온 메뉴 쌍",
    f"{total_pairs:,}쌍"
)

st.divider()


# ==========================================
# 7. 메뉴 선택 및 정렬
# ==========================================

st.subheader("🔎 연관 규칙 찾아보기")

col1, col2 = st.columns(2)

with col1:

    selected_menu = st.selectbox(
        "메뉴 선택",
        options=["전체 메뉴"] + menu_list,
        index=0
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        options=[
            "향상도 순",
            "신뢰도 순",
            "동시 순"
        ],
        index=0
    )


# ==========================================
# 8. 메뉴 필터링
# ==========================================

filtered_df = rules_df.copy()

if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ].copy()


# ==========================================
# 9. 정렬
# ==========================================

sort_columns = {
    "향상도 순": ["향상도", "신뢰도", "동시"],
    "신뢰도 순": ["신뢰도", "향상도", "동시"],
    "동시 순": ["동시", "향상도", "신뢰도"]
}

filtered_df = filtered_df.sort_values(
    by=sort_columns[sort_option],
    ascending=[False, False, False]
).reset_index(drop=True)


# ==========================================
# 10. 연관 규칙 표
# ==========================================

st.subheader("📋 메뉴 연관 규칙")

if selected_menu == "전체 메뉴":

    st.caption("모든 메뉴의 연관 규칙을 보여 줍니다.")

else:

    st.caption(
        f"'{selected_menu}' 메뉴가 조건 또는 결과에 포함된 규칙입니다."
    )


if filtered_df.empty:

    st.info("선택한 메뉴와 관련된 규칙이 없습니다.")

else:

    display_df = filtered_df.copy()

    # 보기 편하게 표시 형식 변경
    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x * 100:.2f}%"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x * 100:.2f}%"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    display_df["동시"] = display_df["동시"].astype(int)

    st.dataframe(
        display_df[
            [
                "조건",
                "결과",
                "동시",
                "지지도",
                "신뢰도",
                "향상도"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=500
    )

    st.caption(
        f"현재 표시 중인 규칙: {len(filtered_df):,}개"
    )


# ==========================================
# 11. 향상도 상위 10개 그래프
# ==========================================

st.divider()

st.subheader("📈 향상도 TOP 10")

st.write(
    "향상도가 높은 메뉴 연관 규칙을 가로 막대그래프로 보여 줍니다."
)

if filtered_df.empty:

    st.info("그래프로 나타낼 데이터가 없습니다.")

else:

    # 필터링된 데이터 중 향상도 상위 10개
    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=[False, False, False]
        )
        .head(10)
        .copy()
    )

    # 그래프에 표시할 규칙 이름
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    # 가로 막대그래프
    fig = px.bar(
        top10.sort_values("향상도"),
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10.sort_values("향상도")["향상도"].round(3),
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "메뉴 연관 규칙"
        },
        title="함께 등장하는 경향이 높은 메뉴 TOP 10"
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=500,
        yaxis_title="",
        xaxis_title="향상도",
        showlegend=False,
        margin=dict(
            l=20,
            r=60,
            t=60,
            b=30
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# 12. 분석 지표 설명
# ==========================================

st.divider()

with st.expander("📖 지지도, 신뢰도, 향상도란?"):

    st.markdown("""
    ### ① 지지도 (Support)

    두 메뉴가 전체 급식 일수 중에서 함께 나온 비율입니다.

    지지도 = 두 메뉴가 함께 나온 횟수 / 전체 급식 일수

    ### ② 신뢰도 (Confidence)

    조건 메뉴가 나온 날 중에서 결과 메뉴도 함께 나온 비율입니다.

    신뢰도 = 두 메뉴가 함께 나온 횟수 / 조건 메뉴가 나온 횟수

    ### ③ 향상도 (Lift)

    조건 메뉴와 결과 메뉴의 관계가 우연히 함께 나오는 경우보다
    얼마나 강한지를 나타냅니다.

    향상도 = 신뢰도 / 결과 메뉴의 등장 비율

    - 향상도 > 1 : 함께 등장하는 경향이 있음
    - 향상도 = 1 : 서로 독립적인 경향
    - 향상도 < 1 : 함께 등장하는 경향이 낮음

    ### 분석할 때 주의할 점

    향상도가 높다고 해서 반드시 한 메뉴가 다른 메뉴의 원인이라는 뜻은 아닙니다.
    두 메뉴가 함께 등장하는 통계적 관계를 나타냅니다.
    """)
