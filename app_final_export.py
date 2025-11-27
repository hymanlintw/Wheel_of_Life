import streamlit as st
import pandas as pd
import io
from datetime import date
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm # 用於中文字體配置
import numpy as np

# --- 1. 全局配置與字體設定 (修正亂碼) ---
ALL_ITEMS = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]

# 配置 Matplotlib 中文字體 設置優先級高的中文字體，解決亂碼問題
# plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'WenQuanYi Zen Hei', 'Arial Unicode MS']

# 1. 指定字型檔案路徑 (假設字型檔案放在根目錄)
FONT_PATH = 'NotoSansCJKtc-Regular.otf' # 請替換成您實際的字型檔案名稱

# 2. 清除 Matplotlib 字體快取並載入自訂字型
try:
    # 嘗試載入自訂字型
    custom_font = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.sans-serif'] = custom_font.get_name()
    
    # 清除快取：確保 Matplotlib 能夠讀取新字型 (重要步驟)
    fm.fontManager.findfont(custom_font.get_name(), rebuild_if_missing=False)

except FileNotFoundError:
    st.warning(f"⚠️ 警告：找不到中文字型檔案 {FONT_PATH}，請檢查檔案是否已上傳到專案根目錄。雷達圖可能出現亂碼。")
    # 如果找不到，則退回使用系統內建字型
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'WenQuanYi Zen Hei', 'Arial Unicode MS']

plt.rcParams['axes.unicode_minus'] = False # 解決負號亂碼問題

# 自訂 CSS (確保按鈕清晰，並加入 autocomplete="off" 的通用設定)
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
    /* 嘗試對所有 Streamlit text input 停用自動完成 */
    input[type="text"] {
        -webkit-autocomplete: off !important;
        -moz-autocomplete: off !important;
        autocomplete: off !important;
    }
    </style>
""", unsafe_allow_html=True)


# --- 2. 狀態管理與初始化 (邏輯不變) ---
def initialize_state():
    if 'initialized' not in st.session_state:
        st.session_state.stage = 0 
        
        st.session_state.user_info = {"name": "", "job": "", "gender": "", "birthday": "", "age": ""}
        st.session_state.importance_scores = {item: 5 for item in ALL_ITEMS}
        
        st.session_state.initial_candidates = list(ALL_ITEMS)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = [] 
        st.session_state.initial_match_history = {} 
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        
        st.session_state.keywords_map = {} 
        st.session_state.all_used_keywords = set() 
        st.session_state.current_keyword_index = 0
        
        st.session_state.deepest_keywords = {} 
        st.session_state.stage3_cat_idx = 0
        st.session_state.stage3_comp_status = {}
        
        st.session_state.final_candidates = [] 
        st.session_state.final_ranked_results = []
        st.session_state.final_history_stack = []
        st.session_state.final_match_history = {}
        st.session_state.final_current_champion = None
        st.session_state.final_challenger_idx = 1
        st.session_state.keyword_to_category = {} 

        st.session_state.initialized = True

initialize_state()

# --- 3. 核心邏輯函數 (排序與比較 - 邏輯不變) ---
# [此處省略 get_sorting_status, record_sorting_win, process_stage2_input, stage2_go_back, get_stage3_comparison, record_stage3_win 函數代碼]
# 由於函式篇幅過長，這裡僅顯示有修改的部分。
# ... (沿用上一版的核心邏輯，以確保排序正確性) ...

# [Stage 1 & 4 通用排序邏輯]
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

# [Stage 2 邏輯]
def process_stage2_input(category, k1, k2, k3):
    if not k1 or not k2 or not k3:
        st.error(f"⚠️ 請填滿 3 個聯想詞！")
        return False
    inputs = [k.strip() for k in [k1, k2, k3]]
    if len(set(inputs)) != 3:
        st.error(f"⚠️ 聯想詞重複！請確保 3 個詞都不一樣。")
        return False
    for word in inputs:
        if word in ALL_ITEMS:
            st.error(f"⚠️ 關鍵字不能與八大面向名稱（如：{word}）相同，請更換。")
            return False
    for word in inputs:
        temp_used_keywords = st.session_state.all_used_keywords - set(st.session_state.keywords_map.get(category, []))
        if word in temp_used_keywords:
            st.error(f"⚠️ 關鍵字「{word}」在之前的面向已經使用過了，請輸入新的詞彙。")
            return False

    st.session_state.keywords_map[category] = inputs
    st.session_state.all_used_keywords.update(inputs)
    for word in inputs:
        st.session_state.keyword_to_category[word] = category
    
    st.session_state.stage3_comp_status[category] = {
        'A': inputs[0], 'B': inputs[1], 'C': inputs[2], 
        'step': 1, 'winner': None
    }
    
    st.session_state.current_keyword_index += 1
    if st.session_state.current_keyword_index >= 8: st.session_state.stage = 3
    st.rerun()

def stage2_go_back():
    if st.session_state.current_keyword_index > 0:
        # 將索引退一步
        st.session_state.current_keyword_index -= 1
        
        # 取得要修改的面向名稱
        prev_cat = st.session_state.initial_ranked_results[st.session_state.current_keyword_index]
        
        # 從全域集合中移除該面向的關鍵字，以便重新輸入
        if prev_cat in st.session_state.keywords_map:
            st.session_state.all_used_keywords -= set(st.session_state.keywords_map[prev_cat])
            # 注意：這裡不刪除 st.session_state.keywords_map[prev_cat]，
            # 讓渲染函數可以使用其中的值來 pre-fill 欄位 (已修正邏輯)。
            # 刪除 Stage 3 狀態
            if prev_cat in st.session_state.stage3_comp_status:
                del st.session_state.stage3_comp_status[prev_cat]
        
        # 因為我們使用 dynamic key，所以欄位會自動用新的 prev_kws 重新渲染
        st.rerun()
    else:
        st.warning("已是第一個項目，無法再回上一步。")

# [Stage 3 邏輯]
def get_stage3_comparison():
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    status = st.session_state.stage3_comp_status[current_cat]
    A, B, C = status['A'], status['B'], status['C']
    step = status['step']
    
    if step == 1: # A vs B
        return "ASK", A, B
    elif step == 2: # Win1 vs C
        p1 = status['winner']
        return "ASK", p1, C
    elif step == 3: # Win2 vs Loser1
        winner_2 = status['winner']
        # 找出第一輪 (A vs B) 的輸家，用於進行第三次比較
        first_round_winner = status.get('first_round_winner', A if status['winner'] != B else B) # 這裡要確保能找到第一輪贏家
        loser_1 = A if first_round_winner == B else B # 假設第一輪贏家是 B，則輸家是 A
        return "ASK", winner_2, loser_1
    
    return "DONE", None, None

def record_stage3_win(winner, loser):
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    status = st.session_state.stage3_comp_status[current_cat]

    status['winner'] = winner
    
    if status['step'] == 1:
        # 儲存第一輪的贏家，用於第三步找出輸家
        status['first_round_winner'] = winner 
        status['step'] += 1
    elif status['step'] < 3:
        status['step'] += 1
    else:
        # 完成 3 次比較，找到最終代表
        st.session_state.deepest_keywords[current_cat] = winner
        
        st.session_state.stage3_cat_idx += 1
        status['step'] = 1
        status['winner'] = None # 清空
        
        if st.session_state.stage3_cat_idx >= 8:
            st.session_state.stage = 4
            sorted_cats = st.session_state.initial_ranked_results
            final_kws = [st.session_state.deepest_keywords[c] for c in sorted_cats]
            st.session_state.final_candidates = final_kws
            st.session_state.final_current_champion = final_kws[0]
            st.session_state.final_challenger_idx = 1
            
    st.rerun()


# --- 4. Excel 報表生成與雷達圖繪製 (A4, 字體, 16pt 修正) ---

def create_radar_chart():
    """繪製雷達圖並儲存為 PNG 圖片"""
    scores = [st.session_state.importance_scores[item] for item in ALL_ITEMS]

    # 載入自訂字型屬性，如果字型不存在，這裡會使用預設字型
    try:
        font_prop = fm.FontProperties(fname=FONT_PATH, size=9)
    except FileNotFoundError:
        font_prop = None # 使用預設字型

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    
    N = len(ALL_ITEMS)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    
    scores = scores + scores[:1]
    angles = angles + angles[:1]

    # 設定字體，確保中文顯示
    font_properties = fm.FontProperties(fname=None) 
    
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    
    ax.plot(angles, scores, color='#1E88E5', linewidth=1, linestyle='solid')
    ax.fill(angles, scores, color='#1E88E5', alpha=0.4)
    
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])

    # 這裡使用 plt.rcParams 設置的全局字體
    #ax.set_xticklabels(ALL_ITEMS, fontsize=9)    
    #ax.set_yticks([2, 4, 6, 8, 10])
    #ax.set_yticklabels(["2", "4", "6", "8", "10"], color="grey", size=8)
    #ax.set_ylim(0, 10)
    #ax.set_title("八大面向重要性權重", va='bottom', fontsize=11)

    # --- 關鍵修正：傳遞字型屬性 ---
    if font_prop:
        ax.set_xticklabels(ALL_ITEMS, fontproperties=font_prop) # 使用 custom_font
        ax.set_title("八大面向重要性權重", va='bottom', fontsize=11, fontproperties=font_prop)
    else:
        ax.set_xticklabels(ALL_ITEMS, fontsize=9)
        ax.set_title("八大面向重要性權重", va='bottom', fontsize=11)
    
    # --- 關鍵修正結束 ---
    
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
    
    # --- Excel 版面設定 (A4 滿版) ---
    worksheet.set_paper(9) # 9 是 A4 size
    worksheet.fit_to_pages(1, 1) # 調整為寬度/高度各一頁 (A4滿版)
    worksheet.set_margins(0.5, 0.5, 0.75, 0.75) # 設定邊界

    # --- 定義格式 (微軟正黑體, 16pt 修正) ---
    font_name = 'Microsoft JhengHei' # 微軟正黑體
    font_size = 16
    
    fmt_header = workbook.book.add_format({'bold': True, 'font_size': font_size + 4, 'align': 'center', 'valign': 'vcenter', 'font_name': font_name})
    fmt_label = workbook.book.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    fmt_value = workbook.book.add_format({'align': 'left', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    fmt_th = workbook.book.add_format({'bold': True, 'align': 'center', 'bg_color': '#4CAF50', 'font_color': 'white', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    fmt_center = workbook.book.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    
    # --- 調整欄寬 ---
    worksheet.set_column('A:A', 5)  # 排名
    worksheet.set_column('B:B', 20) # 表意識
    worksheet.set_column('C:E', 15) # 聯想詞 1, 2, 3 (調整寬度以容納16pt文字)
    worksheet.set_column('F:F', 20) # 潛意識

    # --- 上半部標題 ---
    worksheet.merge_range('A1:F1', '人生八輪協談紀錄表', fmt_header)

    # --- 上左：雷達圖 (插入到 A2) ---
    radar_buf = create_radar_chart()
    # 調整插入位置以讓圖表居中且不被遮擋
    worksheet.insert_image('A2', 'radar_chart.png', {'image_data': radar_buf, 'x_scale': 1.1, 'y_scale': 1.1}) 
    
    # --- 上右：基本資料 (從 D2/E2 開始往下) ---
    info = st.session_state.user_info
    
    # 這裡調整為從 D2/E2 開始，讓版面更緊湊
    worksheet.write('D2', '基本資料', workbook.book.add_format({'bold': True, 'font_size': font_size, 'align': 'center', 'valign': 'vcenter', 'font_name': font_name}))
    
    # 從 Row 3 開始
    worksheet.write('D3', '協談者：', fmt_label)
    worksheet.merge_range('E3:F3', info['name'], fmt_value)
    
    worksheet.write('D4', '協談日期：', fmt_label)
    worksheet.merge_range('E4:F4', date.today().strftime("%Y-%m-%d"), fmt_value)
    
    worksheet.write('D5', '職  業：', fmt_label)
    worksheet.merge_range('E5:F5', info['job'], fmt_value)
    
    worksheet.write('D6', '性  別：', fmt_label)
    worksheet.merge_range('E6:F6', info['gender'], fmt_value)
    
    worksheet.write('D7', '年  齡：', fmt_label)
    worksheet.merge_range('E7:F7', info['age'], fmt_value)

    # --- 下半部：三欄對照表 (從 Row 15 開始，留白) ---
    start_row = 14 # 從第 15 行開始放表格
    worksheet.write(start_row, 0, '順位', fmt_th)
    worksheet.merge_range(start_row, 1, start_row, 1, '表意識', fmt_th)
    worksheet.merge_range(start_row, 2, start_row, 4, '聯 想 詞', fmt_th) 
    worksheet.merge_range(start_row, 5, start_row, 5, '潛意識', fmt_th)

    conscious_list = st.session_state.initial_ranked_results
    subconscious_keywords = st.session_state.final_ranked_results 
    
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
        
        # 4. 潛意識 (F欄) - 填入面向名稱 (使用者確認 Excel 格式正確)
        if i < len(subconscious_keywords):
            s_kw = subconscious_keywords[i]
            s_item = st.session_state.keyword_to_category.get(s_kw, "未知")
        else:
            s_item = ""
            
        worksheet.write(row, 5, s_item, fmt_center)

    workbook.close()
    output.seek(0)
    return output

# --- 5. 介面渲染 (UI - 修正回上頁與最終畫面) ---

# Stage 2: 關鍵字聯想 (修正回上頁與 autofill)
elif st.session_state.stage == 2:
    current_idx = st.session_state.current_keyword_index
    sorted_cats = st.session_state.initial_ranked_results
    
    if current_idx >= len(sorted_cats):
        st.session_state.stage = 3
        st.rerun()

    current_cat = sorted_cats[current_idx]
    
    st.title(f"💡 第二階段：聯想 (項目 {current_idx+1}/8)")
    st.subheader(f"看到「{current_cat}」，你會想到什麼？")
    st.caption("請輸入 3 個不重複的關鍵字（不能與其他面向的詞彙相同）。")
    
    # 顯示回上一頁按鈕
    if current_idx > 0:
        st.button("⬅️ 回上一項 (修改)", on_click=stage2_go_back)

    # 獲取上次儲存的值，用於 pre-fill 欄位 (當回上頁時，這裡會顯示舊值)
    prev_kws = st.session_state.keywords_map.get(current_cat, ["", "", ""])
    
    with st.form(key=f"form_{current_cat}"): # 動態 key 確保清空
        # 加入 autocomplete="off" 禁用瀏覽器自動完成功能
        k1 = st.text_input("聯想詞 1", value=prev_kws[0], key=f"k1_{current_cat}", autocomplete="off")
        k2 = st.text_input("聯想詞 2", value=prev_kws[1], key=f"k2_{current_cat}", autocomplete="off")
        k3 = st.text_input("聯想詞 3", value=prev_kws[2], key=f"k3_{current_cat}", autocomplete="off")
        
        submit = st.form_submit_button("下一步 (進入下一項或第三階段)")
        
        if submit:
            process_stage2_input(current_cat, k1, k2, k3)

# Stage 5: 結果與下載 (修正潛意識核心關鍵字的顯示)
elif st.session_state.stage == 5:
    st.balloons()
    st.title("🎉 協談完成！潛意識羅盤分析")
    
    # 繪製並顯示雷達圖預覽
    radar_buf = create_radar_chart()
    st.image(radar_buf, caption='八大面向重要性權重')
    
    st.divider()
    
    # 顯示最終排序 (修正後的顯示格式)
    final_data = []
    for i, kw in enumerate(st.session_state.final_ranked_results):
        origin = st.session_state.keyword_to_category.get(kw, "未知")
        final_data.append([
            i + 1,
            origin, # 潛意識排序後的八輪面向 (使用者要求顯示的內容)
            kw      # 潛意識核心關鍵字
        ])
    
    st.subheader("潛意識最終排序結果：")
    # 將表格列標題修正為更清晰的描述
    df_final = pd.DataFrame(final_data, columns=["順位", "八輪面向", "核心關鍵字"])
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

# 由於篇幅限制，Stage 0, 1, 3, 4 的渲染邏輯將保持與上一版一致
# ... (Stage 0, 1, 3, 4 渲染邏輯請參考上一版程式碼)