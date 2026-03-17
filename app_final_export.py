import streamlit as st
import pandas as pd

# --- 1. 初始化與全域配置 ---
ALL_ITEMS = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]

def initialize_state():
    if 'stage' not in st.session_state:
        st.session_state.stage = 1
        # Stage 1: 表意識排序
        st.session_state.initial_candidates = list(ALL_ITEMS)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = []
        st.session_state.initial_match_history = {}
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        # Stage 2: 關鍵字
        st.session_state.keywords = {}
        st.session_state.all_used_keywords = set()
        st.session_state.current_keyword_index = 0
        # Stage 3: 代表詞提煉 (A vs B, Winner vs C)
        st.session_state.deepest_keywords = {} # 存 8 個代表詞
        st.session_state.s3_category_idx = 0 # 目前比到第幾個面向
        st.session_state.s3_step = 1 # 1: A vs B, 2: Winner vs C
        st.session_state.s3_temp_winner = None
        # Stage 4: 最終潛意識排序
        st.session_state.final_ranked_results = []
        # (其他 final_ 變數將在進入 Stage 4 時動態初始化)

initialize_state()

# --- 2. 核心排序邏輯 (Stage 1 & 4 共用) ---
def record_sorting_win(prefix, winner, loser):
    st.session_state[f'{prefix}match_history'][(winner, loser)] = True
    if winner == st.session_state[f'{prefix}current_champion']:
        st.session_state[f'{prefix}challenger_idx'] += 1
    else:
        st.session_state[f'{prefix}history_stack'].append(st.session_state[f'{prefix}current_champion'])
        st.session_state[f'{prefix}current_champion'] = winner
        st.session_state[f'{prefix}challenger_idx'] += 1

def get_sorting_status(prefix):
    candidates = st.session_state[f'{prefix}candidates']
    while len(candidates) > 0:
        idx = st.session_state[f'{prefix}challenger_idx']
        if idx >= len(candidates):
            winner = st.session_state[f'{prefix}current_champion']
            st.session_state[f'{prefix}ranked_results'].append(winner)
            candidates.remove(winner)
            if not candidates: return "DONE", None, None
            if st.session_state[f'{prefix}history_stack']:
                while st.session_state[f'{prefix}history_stack']:
                    resurrected = st.session_state[f'{prefix}history_stack'].pop()
                    if resurrected in candidates:
                        st.session_state[f'{prefix}current_champion'] = resurrected
                        break
                else: st.session_state[f'{prefix}current_champion'] = candidates[0]
            else: st.session_state[f'{prefix}current_champion'] = candidates[0]
            st.session_state[f'{prefix}challenger_idx'] = candidates.index(st.session_state[f'{prefix}current_champion']) + 1
            continue
        challenger = candidates[idx]
        champion = st.session_state[f'{prefix}current_champion']
        if (champion, challenger) in st.session_state[f'{prefix}match_history'] or (challenger, champion) in st.session_state[f'{prefix}match_history']:
            st.session_state[f'{prefix}challenger_idx'] += 1
            continue
        return "ASK", champion, challenger
    return "DONE", None, None

# --- 3. Stage 3 特殊邏輯 (擂台制：A vs B -> Win vs C) ---
def render_stage_3():
    idx = st.session_state.s3_category_idx
    ranked_list = st.session_state.initial_ranked_results
    current_cat = ranked_list[idx]
    words = st.session_state.keywords[current_cat] # [A, B, C]

    st.title("💖 第三階段：深刻代表詞提煉")
    st.write(f"針對 **{current_cat}**，從你的聯想詞中選出最深刻的一個。")
    st.progress(idx / 8)

    if st.session_state.s3_step == 1:
        p1, p2 = words[0], words[1] # A vs B
        st.subheader(f"就「{current_cat}」而言，哪一個對你更深刻？")
    else:
        p1, p2 = st.session_state.s3_temp_winner, words[2] # Winner vs C
        st.subheader(f"那麼，與「{words[2]}」相比，哪一個更深刻？")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(p1, use_container_width=True):
            if st.session_state.s3_step == 1:
                st.session_state.s3_temp_winner = p1
                st.session_state.s3_step = 2
            else:
                st.session_state.deepest_keywords[current_cat] = p1
                next_s3_category()
            st.rerun()
    with col2:
        if st.button(p2, use_container_width=True):
            if st.session_state.s3_step == 1:
                st.session_state.s3_temp_winner = p2
                st.session_state.s3_step = 2
            else:
                st.session_state.deepest_keywords[current_cat] = p2
                next_s3_category()
            st.rerun()

def next_s3_category():
    st.session_state.s3_category_idx += 1
    st.session_state.s3_step = 1
    st.session_state.s3_temp_winner = None
    if st.session_state.s3_category_idx >= 8:
        # 進入 Stage 4 初始化
        st.session_state.stage = 4
        final_list = list(st.session_state.deepest_keywords.values())
        st.session_state.final_candidates = final_list
        st.session_state.final_current_champion = final_list[0]
        st.session_state.final_challenger_idx = 1
        st.session_state.final_match_history = {}
        st.session_state.final_history_stack = []

# --- 4. 主流程控制 ---
if st.session_state.stage == 1:
    st.title("🧬 第一階段：表意識排序")
    status, p1, p2 = get_sorting_status('initial_')
    if status == "ASK":
        st.subheader(f"哪一個對你比較重要？")
        c1, c2 = st.columns(2)
        if c1.button(p1, use_container_width=True): record_sorting_win('initial_', p1, p2); st.rerun()
        if c2.button(p2, use_container_width=True): record_sorting_win('initial_', p2, p1); st.rerun()
    else:
        st.success("排序完成！"); st.button("下一步", on_click=lambda: setattr(st.session_state, 'stage', 2))

elif st.session_state.stage == 2:
    st.title("💡 第二階段：關鍵字聯想")
    idx = st.session_state.current_keyword_index
    cat = st.session_state.initial_ranked_results[idx]
    st.subheader(f"看到「{cat}」，你想到的 3 個詞是？")
    with st.form("kw_form"):
        k1 = st.text_input("聯想詞 A")
        k2 = st.text_input("聯想詞 B")
        k3 = st.text_input("聯想詞 C")
        if st.form_submit_button("儲存"):
            # 簡單檢查
            inputs = [k1.strip(), k2.strip(), k3.strip()]
            if len(set(inputs)) == 3 and not any(i in ALL_ITEMS for i in inputs):
                st.session_state.keywords[cat] = inputs
                st.session_state.current_keyword_index += 1
                if st.session_state.current_keyword_index >= 8: st.session_state.stage = 3
                st.rerun()
            else: st.error("請確保輸入不重複且不含面向名稱。")

elif st.session_state.stage == 3:
    render_stage_3()

elif st.session_state.stage == 4:
    st.title("✨ 第四階段：潛意識最終排序")
    status, p1, p2 = get_sorting_status('final_')
    if status == "ASK":
        st.subheader(f"哪一個感覺更深刻、更重要？")
        c1, c2 = st.columns(2)
        if c1.button(p1, use_container_width=True): record_sorting_win('final_', p1, p2); st.rerun()
        if c2.button(p2, use_container_width=True): record_sorting_win('final_', p2, p1); st.rerun()
    else:
        st.session_state.stage = 5; st.rerun()

elif st.session_state.stage == 5:
    st.title("🎉 最終報告：內在核心價值")
    res = st.session_state.final_ranked_results
    # 建立對照表
    lookup = {v: k for k, v in st.session_state.deepest_keywords.items()}
    data = []
    for i, word in enumerate(res):
        data.append({"順位": i+1, "潛意識核心 (關鍵字)": word, "對應人生面向": lookup[word]})
    st.table(data)
    if st.button("重新開始"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()