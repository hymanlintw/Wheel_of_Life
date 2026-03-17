import streamlit as st
import pandas as pd

# --- 1. 定義常數 ---
ALL_CATEGORIES = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]

# --- 2. 狀態初始化 (解決執行不出來的核心問題) ---
def init_game():
    if 'stage' not in st.session_state:
        st.session_state.stage = 1
        
        # 第一階段 (Initial Sorting) 變數
        st.session_state.initial_candidates = list(ALL_CATEGORIES)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = []
        st.session_state.initial_match_history = {}
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        
        # 第二階段 (Keywords) 變數
        st.session_state.keywords_data = {} # 存 {面向: [A, B, C]}
        st.session_state.kw_step_idx = 0 # 目前填到第幾個面向
        
        # 第三階段 (Selection) 變數
        st.session_state.s3_cat_idx = 0 # 正在處理第幾個面向的代表詞
        st.session_state.s3_sub_step = 1 # 1: A vs B, 2: Winner vs C
        st.session_state.s3_temp_winner = None
        st.session_state.representative_keywords = {} # 存 8 個最終代表詞
        
        # 第四階段 (Final Sorting) 變數
        st.session_state.final_candidates = []
        st.session_state.final_ranked_results = []
        st.session_state.final_history_stack = []
        st.session_state.final_match_history = {}
        st.session_state.final_current_champion = None
        st.session_state.final_challenger_idx = 1

init_game()

# --- 3. 通用排序引擎 (用於第一階段與第四階段) ---
def get_sort_status(prefix):
    candidates = st.session_state[f'{prefix}candidates']
    if not candidates:
        return "DONE", None, None
    
    idx = st.session_state[f'{prefix}challenger_idx']
    
    # 如果挑戰者索引超過長度，代表當前冠軍勝出
    if idx >= len(candidates):
        winner = st.session_state[f'{prefix}current_champion']
        st.session_state[f'{prefix}ranked_results'].append(winner)
        candidates.remove(winner)
        
        if not candidates:
            return "DONE", None, None
        
        # 尋找下一個擂台主 (回溯邏輯)
        if st.session_state[f'{prefix}history_stack']:
            while st.session_state[f'{prefix}history_stack']:
                resurrected = st.session_state[f'{prefix}history_stack'].pop()
                if resurrected in candidates:
                    st.session_state[f'{prefix}current_champion'] = resurrected
                    break
            else:
                st.session_state[f'{prefix}current_champion'] = candidates[0]
        else:
            st.session_state[f'{prefix}current_champion'] = candidates[0]
            
        st.session_state[f'{prefix}challenger_idx'] = candidates.index(st.session_state[f'{prefix}current_champion']) + 1
        st.rerun()

    champ = st.session_state[f'{prefix}current_champion']
    challenger = candidates[idx]
    
    # 檢查是否比過
    if (champ, challenger) in st.session_state[f'{prefix}match_history'] or (challenger, champ) in st.session_state[f'{prefix}match_history']:
        st.session_state[f'{prefix}challenger_idx'] += 1
        st.rerun()
        
    return "ASK", champ, challenger

def record_win(prefix, winner, loser):
    st.session_state[f'{prefix}match_history'][(winner, loser)] = True
    if winner != st.session_state[f'{prefix}current_champion']:
        st.session_state[f'{prefix}history_stack'].append(st.session_state[f'{prefix}current_champion'])
        st.session_state[f'{prefix}current_champion'] = winner
    st.session_state[f'{prefix}challenger_idx'] += 1
    st.rerun()

# --- 4. 介面渲染邏輯 ---

st.set_page_config(page_title="人生八輪協談系統", layout="centered")

# 第一階段：表意識排序
if st.session_state.stage == 1:
    st.title("第一階段：表意識價值排序")
    status, p1, p2 = get_sort_status("initial_")
    
    if status == "ASK":
        st.subheader("這兩個面向，哪一個對您目前更重要？")
        col1, col2 = st.columns(2)
        if col1.button(f"{p1}", use_container_width=True): record_win("initial_", p1, p2)
        if col2.button(f"{p2}", use_container_width=True): record_win("initial_", p2, p1)
    else:
        st.success("排序完成！")
        if st.button("下一步：聯想關鍵字"):
            st.session_state.stage = 2
            st.rerun()

# 第二階段：關鍵字輸入
elif st.session_state.stage == 2:
    idx = st.session_state.kw_step_idx
    ranked_order = st.session_state.initial_ranked_results
    current_cat = ranked_order[idx]
    
    st.title("第二階段：關鍵字聯想")
    st.subheader(f"看到或聽到「{current_cat}」，您想到什麼？")
    st.write(f"請列舉 3 項 (目前進度: {idx+1}/8)")
    
    with st.form("kw_form"):
        a = st.text_input("聯想詞 A", key=f"in_a_{idx}")
        b = st.text_input("聯想詞 B", key=f"in_b_{idx}")
        c = st.text_input("聯想詞 C", key=f"in_c_{idx}")
        if st.form_submit_button("儲存並繼續"):
            kws = [a.strip(), b.strip(), c.strip()]
            if "" in kws or len(set(kws)) < 3 or any(k in ALL_CATEGORIES for k in kws):
                st.error("請確保填寫 3 個不同詞彙，且不能包含面向名稱。")
            else:
                st.session_state.keywords_data[current_cat] = kws
                st.session_state.kw_step_idx += 1
                if st.session_state.kw_step_idx >= 8:
                    st.session_state.stage = 3
                st.rerun()

# 第三階段：代表詞提煉 (A vs B, Win vs C)
elif st.session_state.stage == 3:
    idx = st.session_state.s3_cat_idx
    ranked_order = st.session_state.initial_ranked_results
    current_cat = ranked_order[idx]
    words = st.session_state.keywords_data[current_cat] # [A, B, C]
    
    st.title("第三階段：代表詞提煉")
    st.write(f"針對「{current_cat}」，哪一個聯想感覺更深刻？")
    
    if st.session_state.s3_sub_step == 1:
        p1, p2 = words[0], words[1] # A vs B
    else:
        p1, p2 = st.session_state.s3_temp_winner, words[2] # Win vs C

    col1, col2 = st.columns(2)
    with col1:
        if st.button(p1, key="s3_b1", use_container_width=True):
            if st.session_state.s3_sub_step == 1:
                st.session_state.s3_temp_winner = p1
                st.session_state.s3_sub_step = 2
            else:
                st.session_state.representative_keywords[current_cat] = p1
                st.session_state.s3_cat_idx += 1
                st.session_state.s3_sub_step = 1
                if st.session_state.s3_cat_idx >= 8:
                    # 準備進入第四階段
                    st.session_state.final_candidates = list(st.session_state.representative_keywords.values())
                    st.session_state.final_current_champion = st.session_state.final_candidates[0]
                    st.session_state.stage = 4
            st.rerun()
    with col2:
        if st.button(p2, key="s3_b2", use_container_width=True):
            if st.session_state.s3_sub_step == 1:
                st.session_state.s3_temp_winner = p2
                st.session_state.s3_sub_step = 2
            else:
                st.session_state.representative_keywords[current_cat] = p2
                st.session_state.s3_cat_idx += 1
                st.session_state.s3_sub_step = 1
                if st.session_state.s3_cat_idx >= 8:
                    st.session_state.final_candidates = list(st.session_state.representative_keywords.values())
                    st.session_state.final_current_champion = st.session_state.final_candidates[0]
                    st.session_state.stage = 4
            st.rerun()

# 第四階段：潛意識最終排序
elif st.session_state.stage == 4:
    st.title("第四階段：潛意識最終排序")
    status, p1, p2 = get_sort_status("final_")
    
    if status == "ASK":
        st.subheader("這兩個深刻感受，哪一個更觸動您的內心？")
        col1, col2 = st.columns(2)
        if col1.button(f"{p1}", use_container_width=True): record_win("final_", p1, p2)
        if col2.button(f"{p2}", use_container_width=True): record_win("final_", p2, p1)
    else:
        st.success("潛意識排序分析完成！")
        if st.button("查看最終對照分析報告"):
            st.session_state.stage = 5
            st.rerun()

# 第五階段：結果報告
elif st.session_state.stage == 5:
    st.title("📊 最終諮商報告")
    
    # 建立對照表資料
    final_order = st.session_state.final_ranked_results
    # 建立 反向查詢 (關鍵字 -> 面向)
    lookup = {v: k for k, v in st.session_state.representative_keywords.items()}
    
    report_data = []
    for i, kw in enumerate(final_order):
        report_data.append({
            "潛意識順位": i + 1,
            "深刻代表詞 (潛意識)": kw,
            "對應人生面向": lookup.get(kw, "")
        })
    
    st.table(report_data)
    
    # 對比表意識
    st.subheader("💡 表意識 vs 潛意識 順位對比")
    comparison = pd.DataFrame({
        "順位": range(1, 9),
        "表意識 (第一階段)": st.session_state.initial_ranked_results,
        "潛意識 (第四階段對應)": [lookup.get(kw, "") for kw in final_order]
    })
    st.dataframe(comparison, hide_index=True)
    
    if st.button("重啟測驗"):
        st.session_state.clear()
        st.rerun()
