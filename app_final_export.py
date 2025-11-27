import streamlit as st
import pandas as pd
import io
from datetime import date
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np

# --- 1. 全局配置與 CSS ---
ALL_ITEMS = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]
ITEM_COLORS = {
    "健康": "#1E88E5", "工作": "#4CAF50", "家庭": "#FF9800", "休閒": "#9C27B0",
    "情緒": "#F44336", "成長": "#00BCD4", "人際": "#FFEB3B", "財富": "#795548"
}

# 自訂 CSS (確保按鈕清晰)
st.markdown("""
    <style>
    div.stButton > button {
        height: 60px;
        font-size: 18px;
        border-radius: 8px;
        transition: all 0.2s;
    }
    .stProgress > div > div > div > div {
        background-color: #FF9800;
    }
    </style>
""", unsafe_allow_html=True)


# --- 2. 狀態管理與初始化 ---
def initialize_state():
    if 'initialized' not in st.session_state:
        st.session_state.stage = 0 
        
        # === Stage 0: 基本資料 & 權重 ===
        st.session_state.user_info = {"name": "", "job": "", "gender": "", "birthday": "", "age": ""}
        st.session_state.importance_scores = {item: 5 for item in ALL_ITEMS} # 權重 (1-10分)
        
        # === Stage 1: 表意識排序 (堆疊回溯法) ===
        st.session_state.initial_candidates = list(ALL_ITEMS)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = [] 
        st.session_state.initial_match_history = {} 
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        
        # === Stage 2: 關鍵字聯想 ===
        st.session_state.keywords_map = {} 
        st.session_state.all_used_keywords = set() 
        st.session_state.current_keyword_index = 0
        
        # === Stage 3: 潛意識代表提煉 (新的 3 次比較邏輯) ===
        st.session_state.deepest_keywords = {} # {面向: 最終代表詞}
        st.session_state.stage3_cat_idx = 0
        st.session_state.stage3_comp_status = {} # {面向: {'A':k1, 'B':k2, 'C':k3, 'step':0, 'winner':None}}
        
        # === Stage 4: 潛意識最終排序 (堆疊回溯法) ===
        st.session_state.final_candidates = [] 
        st.session_state.final_ranked_results = []
        st.session_state.final_history_stack = []
        st.session_state.final_match_history = {}
        st.session_state.final_current_champion = None
        st.session_state.final_challenger_idx = 1
        st.session_state.keyword_to_category = {} 

        st.session_state.initialized = True

initialize_state()

# --- 3. 核心邏輯函數 (排序與比較) ---

# [此處的 get_sorting_status 和 record_sorting_win 沿用上一版精確的堆疊回溯邏輯，適用於 Stage 1 & 4]
# ... (為節省篇幅，省略 Stage 1/4 的通用排序函數代碼，假設其已存在並正確運行) ...
def get_sorting_status(prefix):
    candidates = st.session_state[f'{prefix}candidates']
    ranked_list = st.session_state[f'{prefix}ranked_results']
    stack = st.session_state[f'{prefix}history_stack']
    history = st.session_state[f'{prefix}match_history']
    
    while len(candidates) > 0:
        champion = st.session_state[f'{prefix}current_champion']
        challenger_idx = st.session_state[f'{prefix}challenger_idx']
        
        if challenger_idx >= len(candidates):
            ranked_list.append(champion)
            candidates.remove(champion)
            
            if len(candidates) == 0: return "DONE", None, None
            
            if stack:
                found_resurrected = False
                while stack:
                    resurrected = stack.pop()
                    if resurrected in candidates:
                        st.session_state[f'{prefix}current_champion'] = resurrected
                        found_resurrected = True
                        break
                if not found_resurrected: st.session_state[f'{prefix}current_champion'] = candidates[0]
            else: st.session_state[f'{prefix}current_champion'] = candidates[0]
            
            current_champ_idx = candidates.index(st.session_state[f'{prefix}current_champion'])
            st.session_state[f'{prefix}challenger_idx'] = current_champ_idx + 1
            continue

        challenger = candidates[challenger_idx]
        
        if (champion, challenger) in history: 
            st.session_state[f'{prefix}challenger_idx'] += 1
            continue
        elif (challenger, champion) in history: 
            stack.append(champion)
            st.session_state[f'{prefix}current_champion'] = challenger
            st.session_state[f'{prefix}challenger_idx'] += 1
            continue
        
        return "ASK", champion, challenger

    return "DONE", None, None

def record_sorting_win(prefix, winner, loser):
    st.session_state[f'{prefix}match_history'][(winner, loser)] = True
    current_champ = st.session_state[f'{prefix}current_champion']
    
    if winner == current_champ:
        st.session_state[f'{prefix}challenger_idx'] += 1
    else:
        st.session_state[f'{prefix}history_stack'].append(current_champ)
        st.session_state[f'{prefix}current_champion'] = winner
        st.session_state[f'{prefix}challenger_idx'] += 1
    
    status, _, _ = get_sorting_status(prefix)
    if status == "DONE":
        if prefix == 'initial_': st.session_state.stage = 2 
        elif prefix == 'final_': st.session_state.stage = 5 
    st.rerun()

# --- 4. 關鍵字處理邏輯 (Stage 2 & 3) ---

def process_stage2_input(category, k1, k2, k3):
    # 檢查空值
    if not k1 or not k2 or not k3:
        st.error(f"⚠️ 請填滿 3 個聯想詞！")
        return False

    inputs = [k.strip() for k in [k1, k2, k3]]
    
    # 檢查該組內的重複
    if len(set(inputs)) != 3:
        st.error(f"⚠️ 聯想詞重複！請確保 3 個詞都不一樣。")
        return False
        
    # 檢查與八大面向名稱重複
    for word in inputs:
        if word in ALL_ITEMS:
            st.error(f"⚠️ 關鍵字不能與八大面向名稱（如：{word}）相同，請更換。")
            return False
    
    # 檢查全域重複
    for word in inputs:
        # 排除當前已儲存的，只檢查其他面向是否用過
        temp_used_keywords = st.session_state.all_used_keywords - set(st.session_state.keywords_map.get(category, []))
        if word in temp_used_keywords:
            st.error(f"⚠️ 關鍵字「{word}」在之前的面向已經使用過了，請輸入新的詞彙。")
            return False

    # 通過檢查 -> 儲存並初始化 Stage 3 比較狀態
    st.session_state.keywords_map[category] = inputs
    st.session_state.all_used_keywords.update(inputs)
    for word in inputs:
        st.session_state.keyword_to_category[word] = category
    
    # 初始化 Stage 3 比較狀態
    st.session_state.stage3_comp_status[category] = {
        'A': inputs[0], 'B': inputs[1], 'C': inputs[2], 
        'step': 1,      # 1: A vs B, 2: Win1 vs C, 3: Win2 vs Loser1
        'winner': None  # 暫時贏家
    }
    
    st.session_state.current_keyword_index += 1
    if st.session_state.current_keyword_index >= 8: st.session_state.stage = 3
    st.rerun()

def stage2_go_back():
    """回上一頁：清除當前面向的資料，並將索引退一步"""
    if st.session_state.current_keyword_index > 0:
        st.session_state.current_keyword_index -= 1
        
        # 清除上一個面向的資料
        prev_cat = st.session_state.initial_ranked_results[st.session_state.current_keyword_index]
        
        # 從全域集合中移除上一個面向的關鍵字
        if prev_cat in st.session_state.keywords_map:
            st.session_state.all_used_keywords -= set(st.session_state.keywords_map[prev_cat])
            # 也可以刪除該面向的狀態，但我們只需要讓它回到 Stage 2 重新填寫即可
            del st.session_state.keywords_map[prev_cat]
            if prev_cat in st.session_state.stage3_comp_status:
                del st.session_state.stage3_comp_status[prev_cat]

        st.rerun()
    else:
        st.warning("已是第一個項目，無法再回上一步。")


def get_stage3_comparison():
    """新的 Stage 3 比較邏輯：A vs B, Win1 vs C, Win2 vs Loser1"""
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    status = st.session_state.stage3_comp_status[current_cat]
    
    A, B, C = status['A'], status['B'], status['C']
    step = status['step']
    
    if step == 1:
        # A vs B
        return "ASK", A, B
    elif step == 2:
        # Win1 vs C
        p1 = status['winner']
        return "ASK", p1, C
    elif step == 3:
        # Win2 vs Loser1 (找到第一輪輸家)
        winner_2 = status['winner']
        # 第一輪的兩個詞是 A 和 B
        loser_1 = A if status['winner'] != A else B
        return "ASK", winner_2, loser_1
    
    return "DONE", None, None # 代表本輪比較已完成

def record_stage3_win(winner, loser):
    """處理 Stage 3 點擊，推進到下一步或儲存最終代表詞"""
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    status = st.session_state.stage3_comp_status[current_cat]

    # 記錄當前勝者
    status['winner'] = winner
    
    if status['step'] < 3:
        # 繼續下一比較步驟
        status['step'] += 1
    else:
        # 完成 3 次比較，找到最終代表
        st.session_state.deepest_keywords[current_cat] = winner
        
        # 進入下一面向
        st.session_state.stage3_cat_idx += 1
        
        if st.session_state.stage3_cat_idx >= 8:
            st.session_state.stage = 4
            
            # 初始化 Stage 4 參數 (將 8 個代表詞依 Stage 1 順序放入)
            sorted_cats = st.session_state.initial_ranked_results
            final_kws = [st.session_state.deepest_keywords[c] for c in sorted_cats]
            
            st.session_state.final_candidates = final_kws
            st.session_state.final_current_champion = final_kws[0]
            st.session_state.final_challenger_idx = 1
            
    st.rerun()


# --- 5. Excel 報表生成與雷達圖繪製 ---

def create_radar_chart():
    """繪製雷達圖並儲存為 PNG 圖片"""
    scores = [st.session_state.importance_scores[item] for item in ALL_ITEMS]
    
    N = len(ALL_ITEMS)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    
    # 將數據閉合，形成一個圈
    scores = scores + scores[:1]
    angles = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    
    # 繪製雷達圖
    ax.plot(angles, scores, color='#1E88E5', linewidth=1, linestyle='solid')
    ax.fill(angles, scores, color='#1E88E5', alpha=0.4)
    
    # 設定軸標籤和刻度
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(ALL_ITEMS, fontsize=8)
    
    # 設定分數範圍 (1-10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], color="grey", size=7)
    ax.set_ylim(0, 10)
    
    # 設定標題 (如果需要)
    ax.set_title("八大面向重要性權重", va='bottom', fontsize=10)
    
    # 儲存為 BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_excel_report():
    output = io.BytesIO()
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    
    df_dummy = pd.DataFrame()
    df_dummy.to_excel(workbook, sheet_name='協談結果', index=False)
    worksheet = workbook.sheets['協談結果']
    
    # 繪製並插入雷達圖
    radar_buf = create_radar_chart()
    worksheet.insert_image('A2', 'radar_chart.png', {'image_data': radar_buf, 'x_scale': 1, 'y_scale': 1})
    
    # --- 定義格式 ---
    fmt_header = workbook.book.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
    fmt_label = workbook.book.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1, 'font_size': 10})
    fmt_value = workbook.book.add_format({'align': 'left', 'border': 1, 'font_size': 10})
    fmt_th = workbook.book.add_format({'bold': True, 'align': 'center', 'bg_color': '#4CAF50', 'font_color': 'white', 'border': 1, 'font_size': 10})
    fmt_center = workbook.book.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
    
    # --- 調整欄寬 (以 A4 視覺效果為目標) ---
    worksheet.set_column('A:A', 5) # 排名
    worksheet.set_column('B:B', 20) # 表意識
    worksheet.set_column('C:C', 10) # 聯想詞 1
    worksheet.set_column('D:D', 10) # 聯想詞 2
    worksheet.set_column('E:E', 10) # 聯想詞 3
    worksheet.set_column('F:F', 20) # 潛意識
    
    # --- 上半部標題 ---
    worksheet.merge_range('A1:F1', '人生八輪協談紀錄表', fmt_header)

    # --- 上右：基本資料 (從 F2 開始往下) ---
    info = st.session_state.user_info
    worksheet.merge_range('D2:E2', '基本資料', fmt_th)
    
    # Row 3 (D3: 協談者, E3: 姓名)
    worksheet.write('D3', '協談者：', fmt_label)
    worksheet.merge_range('E3:F3', info['name'], fmt_value)
    
    # Row 4 (D4: 協談日期, E4: Date)
    worksheet.write('D4', '協談日期：', fmt_label)
    worksheet.merge_range('E4:F4', date.today().strftime("%Y-%m-%d"), fmt_value)
    
    # Row 5 (D5: 職業)
    worksheet.write('D5', '職  業：', fmt_label)
    worksheet.merge_range('E5:F5', info['job'], fmt_value)
    
    # Row 6 (D6: 性別)
    worksheet.write('D6', '性  別：', fmt_label)
    worksheet.merge_range('E6:F6', info['gender'], fmt_value)
    
    # Row 7 (D7: 年齡)
    worksheet.write('D7', '年  齡：', fmt_label)
    worksheet.merge_range('E7:F7', info['age'], fmt_value)

    # --- 下半部：三欄對照表 ---
    start_row = 10 # 從第 11 行開始放表格
    worksheet.write(start_row, 0, '順位', fmt_th)
    worksheet.merge_range(start_row, 1, start_row, 1, '表意識', fmt_th)
    worksheet.merge_range(start_row, 2, start_row, 4, '聯 想 詞', fmt_th) # 合併 C11, D11, E11
    worksheet.merge_range(start_row, 5, start_row, 5, '潛意識', fmt_th)

    # 準備資料
    conscious_list = st.session_state.initial_ranked_results
    subconscious_keywords = st.session_state.final_ranked_results # 關鍵字
    
    for i in range(8):
        row = start_row + 1 + i
        rank = i + 1
        
        # 1. 順位 (A欄)
        worksheet.write(row, 0, rank, fmt_center)
        
        # 2. 表意識 (B欄)
        c_item = conscious_list[i] if i < len(conscious_list) else ""
        worksheet.write(row, 1, c_item, fmt_center)
        
        # 3. 聯想詞 (C, D, E欄)
        kw_list = st.session_state.keywords_map.get(c_item, ["", "", ""])
        worksheet.write(row, 2, kw_list[0], fmt_center)
        worksheet.write(row, 3, kw_list[1], fmt_center)
        worksheet.write(row, 4, kw_list[2], fmt_center)
        
        # 4. 潛意識 (F欄) - 只填入面向名稱
        if i < len(subconscious_keywords):
            s_kw = subconscious_keywords[i]
            # 根據潛意識排序的關鍵字，反查它是哪個八輪面向
            s_item = st.session_state.keyword_to_category.get(s_kw, "未知")
        else:
            s_item = ""
            
        worksheet.write(row, 5, s_item, fmt_center)

    workbook.close()
    output.seek(0)
    return output

# --- 6. 介面渲染 (UI) ---

# Stage 0: 基本資料與權重
if st.session_state.stage == 0:
    st.title("📋 協談者資料建立與權重設定")
    
    # 6.1 基本資料輸入
    st.subheader("一、基本資料")
    with st.form("info_form"):
        col1, col2 = st.columns(2)
        st.session_state.user_info['name'] = col1.text_input("姓名", st.session_state.user_info['name'])
        st.session_state.user_info['gender'] = col2.selectbox("性別", ["男", "女", "其他"])
        st.session_state.user_info['birthday'] = col1.text_input("生日 (YYYY/MM/DD)", st.session_state.user_info['birthday'])
        st.session_state.user_info['age'] = col2.text_input("年齡", st.session_state.user_info['age'])
        st.session_state.user_info['job'] = st.text_input("職業", st.session_state.user_info['job'])
        
        st.subheader("二、八大面向重要性權重 (1-10分)")
        st.caption("請評估每個面向在您人生中的重要程度 (10分最高)。")
        
        # 6.2 權重輸入
        cols = st.columns(4)
        for i, item in enumerate(ALL_ITEMS):
            st.session_state.importance_scores[item] = cols[i%4].slider(
                item, 1, 10, st.session_state.importance_scores[item], key=f'score_{item}'
            )
        
        if st.form_submit_button("開始測驗 (第一階段)"):
            st.session_state.stage = 1
            st.rerun()

# Stage 1, 3, 4 沿用 Stage 1, 3, 4 的邏輯

# Stage 2: 關鍵字聯想 (增加回上一頁)
elif st.session_state.stage == 2:
    current_idx = st.session_state.current_keyword_index
    sorted_cats = st.session_state.initial_ranked_results
    
    if current_idx >= len(sorted_cats):
        st.session_state.stage = 3 # 防止 Stage 1 結束，但 Stage 2 未完成時的錯誤跳轉
        st.rerun()

    current_cat = sorted_cats[current_idx]
    
    st.title(f"💡 第二階段：聯想 (項目 {current_idx+1}/8)")
    st.subheader(f"看到「{current_cat}」，你會想到什麼？")
    st.caption("請輸入 3 個不重複的關鍵字（不能與其他面向的詞彙相同）。")
    
    # 顯示回上一頁按鈕
    if current_idx > 0:
        st.button("⬅️ 回上一項 (修改)", on_click=stage2_go_back)

    # 獲取上次儲存的值，方便回頭時預填
    prev_kws = st.session_state.keywords_map.get(current_cat, ["", "", ""])
    
    with st.form(key=f"form_{current_cat}"): 
        k1 = st.text_input("聯想詞 1", value=prev_kws[0], key=f"k1_{current_cat}")
        k2 = st.text_input("聯想詞 2", value=prev_kws[1], key=f"k2_{current_cat}")
        k3 = st.text_input("聯想詞 3", value=prev_kws[2], key=f"k3_{current_cat}")
        
        submit = st.form_submit_button("下一步 (進入下一項或第三階段)")
        
        if submit:
            process_stage2_input(current_cat, k1, k2, k3)

# Stage 3: 潛意識代表提煉 (新的 3 次比較邏輯)
elif st.session_state.stage == 3:
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    
    status_type, p1, p2 = get_stage3_comparison()
    
    st.title(f"💖 第三階段：深層感受提煉 (項目 {st.session_state.stage3_cat_idx+1}/8)")
    st.caption(f"針對「{current_cat}」的聯想詞，請選出感受較深刻的詞。")
    st.progress((st.session_state.stage3_cat_idx + (st.session_state.stage3_comp_status[current_cat]['step'] / 3)) / 8)
    
    if status_type == "ASK":
        st.subheader(f"哪一個感受比較深刻？")
        st.info(f"這是 {current_cat} 的第 {st.session_state.stage3_comp_status[current_cat]['step']} 次比較 (共 3 次)")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"{p1}", key=f"s3_l_{p1}", use_container_width=True):
                record_stage3_win(p1, p2)
        with col2:
            if st.button(f"{p2}", key=f"s3_r_{p2}", use_container_width=True):
                record_stage3_win(p2, p1)

# Stage 5: 結果與下載
elif st.session_state.stage == 5:
    st.balloons()
    st.title("🎉 協談完成！")
    
    # 繪製並顯示雷達圖預覽
    radar_buf = create_radar_chart()
    st.image(radar_buf, caption='八大面向重要性權重')
    
    st.divider()
    
    # 顯示最終排序
    final_data = []
    for i, kw in enumerate(st.session_state.final_ranked_results):
        origin = st.session_state.keyword_to_category.get(kw, "未知")
        final_data.append([
            i + 1,
            origin, # 顯示項目名稱
            kw # 顯示關鍵字
        ])
    
    st.subheader("最終排序結果：")
    df_final = pd.DataFrame(final_data, columns=["順位", "八輪面向", "潛意識核心關鍵字"])
    st.dataframe(df_final.set_index('順位'), use_container_width=True)
        
    st.divider()
    
    # 下載按鈕
    excel_file = generate_excel_report()
    st.download_button(
        label="📥 下載完整協談報表 (Excel) - A4 格式",
        data=excel_file,
        file_name=f"人生八輪協談_{st.session_state.user_info['name']}_{date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🔄 重新開始"):
        st.session_state.clear()
        st.rerun()

# Stage 1 & 4 渲染邏輯 (簡潔版，避免程式碼過長)
elif st.session_state.stage == 1:
    st.title("🧬 第一階段：表意識排序")
    status, p1, p2 = get_sorting_status('initial_')
    if status == "ASK":
        st.subheader(f"哪一個比較重要？")
        c1, c2 = st.columns(2)
        if c1.button(f"🅰️ {p1}", key=f"s1_{p1}", use_container_width=True): record_sorting_win('initial_', p1, p2)
        if c2.button(f"🅱️ {p2}", key=f"s1_{p2}", use_container_width=True): record_sorting_win('initial_', p2, p1)
elif st.session_state.stage == 4:
    st.title("✨ 第四階段：潛意識最終排序")
    status, p1, p2 = get_sorting_status('final_')
    if status == "ASK":
        st.subheader(f"哪一個對你的生命更重要？")
        c1, c2 = st.columns(2)
        if c1.button(f"🅰️ {p1}", key=f"s4_{p1}", use_container_width=True): record_sorting_win('final_', p1, p2)
        if c2.button(f"🅱️ {p2}", key=f"s4_{p2}", use_container_width=True): record_sorting_win('final_', p2, p1)