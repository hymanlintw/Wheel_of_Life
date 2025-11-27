import streamlit as st
import pandas as pd
import io
from datetime import date
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

# --- 1. 全局配置 ---
ALL_ITEMS = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]

# 自訂 CSS
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
    /* 停用自動完成 */
    input[type="text"] {
        autocomplete: off;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 字型設定 (解決中文亂碼) ---
FONT_PATH = 'NotoSansCJKtc-Regular.otf' # 請確認此檔案已上傳至根目錄

def get_font_properties():
    """取得 Matplotlib 字型屬性"""
    if os.path.exists(FONT_PATH):
        return fm.FontProperties(fname=FONT_PATH)
    else:
        # 回退機制：嘗試使用系統常見中文字型
        return fm.FontProperties(family=['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS'])

# 配置 Matplotlib 全局設定 (盡量避免方塊字)
try:
    if os.path.exists(FONT_PATH):
        custom_font = fm.FontProperties(fname=FONT_PATH)
        fm.fontManager.addfont(FONT_PATH)
        plt.rcParams['font.family'] = custom_font.get_name()
    else:
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
except Exception:
    pass
plt.rcParams['axes.unicode_minus'] = False 


# --- 3. 狀態管理與初始化 ---
def initialize_state():
    if 'initialized' not in st.session_state:
        st.session_state.stage = 0 
        
        # 基本資料
        st.session_state.user_info = {"name": "", "job": "", "gender": "", "birthday": "", "age": ""}
        st.session_state.importance_scores = {item: 5 for item in ALL_ITEMS}
        
        # Stage 1: 表意識
        st.session_state.initial_candidates = list(ALL_ITEMS)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = [] 
        st.session_state.initial_match_history = {} 
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        
        # Stage 2: 聯想
        st.session_state.keywords_map = {} 
        st.session_state.all_used_keywords = set() 
        st.session_state.current_keyword_index = 0
        
        # Stage 3: 提煉
        st.session_state.deepest_keywords = {} 
        st.session_state.stage3_cat_idx = 0
        st.session_state.stage3_comp_status = {}
        
        # Stage 4: 潛意識
        st.session_state.final_candidates = [] 
        st.session_state.final_ranked_results = []
        st.session_state.final_history_stack = []
        st.session_state.final_match_history = {}
        st.session_state.final_current_champion = None
        st.session_state.final_challenger_idx = 1
        st.session_state.keyword_to_category = {} 

        st.session_state.initialized = True

initialize_state()


# --- 4. 所有邏輯函數定義 (Logic Functions) ---
# 必須放在 if/elif 渲染邏輯之前！

def get_sorting_status(prefix):
    """通用排序邏輯 (堆疊回溯法)"""
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
    """通用記錄勝負邏輯"""
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

def process_stage2_input(category, k1, k2, k3):
    """Stage 2: 處理輸入並儲存"""
    if not k1 or not k2 or not k3:
        st.error(f"⚠️ 請填滿 3 個聯想詞！")
        return False
    inputs = [k.strip() for k in [k1, k2, k3]]
    
    # 檢查重複
    if len(set(inputs)) != 3:
        st.error(f"⚠️ 聯想詞重複！")
        return False
    for word in inputs:
        if word in ALL_ITEMS:
            st.error(f"⚠️ 不能與八大面向名稱相同：{word}")
            return False
    
    # 全域重複檢查 (排除自己這一項原本的)
    current_stored = set(st.session_state.keywords_map.get(category, []))
    other_used = st.session_state.all_used_keywords - current_stored
    
    for word in inputs:
        if word in other_used:
            st.error(f"⚠️ 關鍵字「{word}」在其他面向已使用過。")
            return False

    # 儲存
    st.session_state.keywords_map[category] = inputs
    st.session_state.all_used_keywords.update(inputs)
    for word in inputs:
        st.session_state.keyword_to_category[word] = category
    
    # 初始化 Stage 3 狀態
    st.session_state.stage3_comp_status[category] = {
        'A': inputs[0], 'B': inputs[1], 'C': inputs[2], 
        'step': 1, 'winner': None
    }
    
    st.session_state.current_keyword_index += 1
    if st.session_state.current_keyword_index >= 8: st.session_state.stage = 3
    st.rerun()

def stage2_go_back():
    """Stage 2: 回上一頁"""
    if st.session_state.current_keyword_index > 0:
        st.session_state.current_keyword_index -= 1
        # 不刪除資料，保留以供顯示，僅退回索引
        st.rerun()
    else:
        st.warning("已是第一個項目。")

def get_stage3_comparison():
    """Stage 3: 取得比較對象 (3步驟邏輯)"""
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
        first_round_winner = status.get('first_round_winner', A if status['winner'] != B else B)
        loser_1 = A if first_round_winner == B else B
        return "ASK", winner_2, loser_1
    
    return "DONE", None, None

def record_stage3_win(winner, loser):
    """Stage 3: 記錄勝負"""
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    status = st.session_state.stage3_comp_status[current_cat]

    status['winner'] = winner
    
    if status['step'] == 1:
        status['first_round_winner'] = winner 
        status['step'] += 1
    elif status['step'] < 3:
        status['step'] += 1
    else:
        # 完成
        st.session_state.deepest_keywords[current_cat] = winner
        st.session_state.stage3_cat_idx += 1
        status['step'] = 1
        status['winner'] = None
        
        if st.session_state.stage3_cat_idx >= 8:
            st.session_state.stage = 4
            # 初始化 Stage 4
            sorted_cats = st.session_state.initial_ranked_results
            final_kws = [st.session_state.deepest_keywords[c] for c in sorted_cats]
            st.session_state.final_candidates = final_kws
            st.session_state.final_current_champion = final_kws[0]
            st.session_state.final_challenger_idx = 1
            
    st.rerun()

def create_radar_chart():
    """繪製雷達圖"""
    scores = [st.session_state.importance_scores[item] for item in ALL_ITEMS]
    N = len(ALL_ITEMS)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    scores += scores[:1]
    angles += angles[:1]

    font_prop = get_font_properties() # 使用上方定義的字型載入函數

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, color='#1E88E5', linewidth=1, linestyle='solid')
    ax.fill(angles, scores, color='#1E88E5', alpha=0.4)
    
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(ALL_ITEMS, fontproperties=font_prop, fontsize=10)
    
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], color="grey", size=8)
    ax.set_ylim(0, 10)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_excel_report():
    """生成 Excel (A4, 16pt, JhengHei)"""
    output = io.BytesIO()
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    
    df_dummy = pd.DataFrame()
    df_dummy.to_excel(workbook, sheet_name='協談結果', index=False)
    worksheet = workbook.sheets['協談結果']
    
    worksheet.set_paper(9) # A4
    worksheet.fit_to_pages(1, 1)
    worksheet.set_margins(0.5, 0.5, 0.75, 0.75)

    font_name = 'Microsoft JhengHei'
    font_size = 16
    
    # 格式定義
    fmt_header = workbook.book.add_format({'bold': True, 'font_size': 20, 'align': 'center', 'valign': 'vcenter', 'font_name': font_name})
    fmt_label = workbook.book.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    fmt_value = workbook.book.add_format({'align': 'left', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    fmt_th = workbook.book.add_format({'bold': True, 'align': 'center', 'bg_color': '#4CAF50', 'font_color': 'white', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    fmt_center = workbook.book.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': font_size, 'font_name': font_name})
    
    # 欄寬
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:E', 15)
    worksheet.set_column('F:F', 20)

    # 上半部：標題
    worksheet.merge_range('A1:F1', '人生八輪協談紀錄表', fmt_header)

    # 上左：雷達圖 (A2)
    radar_buf = create_radar_chart()
    worksheet.insert_image('A2', 'radar.png', {'image_data': radar_buf, 'x_scale': 1.1, 'y_scale': 1.1})
    
    # 上右：基本資料 (D2-F7)
    info = st.session_state.user_info
    worksheet.write('D2', '基本資料', workbook.book.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'font_name': font_name}))
    
    fields = [
        ('D3', '協談者：', 'E3:F3', info['name']),
        ('D4', '協談日期：', 'E4:F4', date.today().strftime("%Y-%m-%d")),
        ('D5', '職  業：', 'E5:F5', info['job']),
        ('D6', '性  別：', 'E6:F6', info['gender']),
        ('D7', '年  齡：', 'E7:F7', info['age'])
    ]
    for lbl_cell, lbl_txt, val_cell, val_txt in fields:
        worksheet.write(lbl_cell, lbl_txt, fmt_label)
        worksheet.merge_range(val_cell, val_txt, fmt_value)

    # 下半部：表格 (Row 15)
    row_idx = 14
    worksheet.write(row_idx, 0, '順位', fmt_th)
    worksheet.write(row_idx, 1, '表意識', fmt_th)
    worksheet.merge_range(row_idx, 2, row_idx, 4, '聯 想 詞', fmt_th) 
    worksheet.write(row_idx, 5, '潛意識', fmt_th)

    conscious = st.session_state.initial_ranked_results
    subconscious = st.session_state.final_ranked_results 
    
    for i in range(8):
        r = row_idx + 1 + i
        rank = i + 1
        c_item = conscious[i] if i < len(conscious) else ""
        kw_list = st.session_state.keywords_map.get(c_item, ["", "", ""])
        
        # 潛意識：顯示對應的面向
        s_item = ""
        if i < len(subconscious):
            s_kw = subconscious[i]
            s_item = st.session_state.keyword_to_category.get(s_kw, "")

        worksheet.write(r, 0, rank, fmt_center)
        worksheet.write(r, 1, c_item, fmt_center)
        worksheet.write(r, 2, kw_list[0], fmt_center)
        worksheet.write(r, 3, kw_list[1], fmt_center)
        worksheet.write(r, 4, kw_list[2], fmt_center)
        worksheet.write(r, 5, s_item, fmt_center)

    workbook.close()
    output.seek(0)
    return output


# --- 5. 主畫面渲染流程 (Main Render Loop) ---
# 這是修正 SyntaxError 的關鍵：保證只有這一個 if-elif-elif 鏈

if st.session_state.stage == 0:
    # --- Stage 0: 資料與權重 ---
    st.title("📋 資料建立與權重設定")
    with st.form("info_form"):
        col1, col2 = st.columns(2)
        st.session_state.user_info['name'] = col1.text_input("姓名", st.session_state.user_info['name'])
        st.session_state.user_info['gender'] = col2.selectbox("性別", ["男", "女", "其他"])
        st.session_state.user_info['birthday'] = col1.text_input("生日", st.session_state.user_info['birthday'])
        st.session_state.user_info['age'] = col2.text_input("年齡", st.session_state.user_info['age'])
        st.session_state.user_info['job'] = st.text_input("職業", st.session_state.user_info['job'])
        
        st.subheader("八大面向權重 (1-10)")
        cols = st.columns(4)
        for i, item in enumerate(ALL_ITEMS):
            st.session_state.importance_scores[item] = cols[i%4].slider(item, 1, 10, 5, key=f'sc_{item}')
        
        if st.form_submit_button("開始測驗"):
            st.session_state.stage = 1
            st.rerun()

elif st.session_state.stage == 1:
    # --- Stage 1: 表意識排序 ---
    st.title("🧬 第一階段：表意識排序")
    st.caption("請依直覺選擇，程式會找出您目前最重視的面向。")
    status, p1, p2 = get_sorting_status('initial_')
    
    if status == "ASK":
        st.subheader(f"哪一個比較重要？")
        c1, c2 = st.columns(2)
        if c1.button(f"🅰️ {p1}", key=f"s1_{p1}", use_container_width=True): record_sorting_win('initial_', p1, p2)
        if c2.button(f"🅱️ {p2}", key=f"s1_{p2}", use_container_width=True): record_sorting_win('initial_', p2, p1)

elif st.session_state.stage == 2:
    # --- Stage 2: 聯想 ---
    current_idx = st.session_state.current_keyword_index
    sorted_cats = st.session_state.initial_ranked_results
    
    if current_idx >= len(sorted_cats):
        st.session_state.stage = 3
        st.rerun()

    current_cat = sorted_cats[current_idx]
    
    st.title(f"💡 第二階段：聯想 ({current_idx+1}/8)")
    st.subheader(f"看到「{current_cat}」，你會想到什麼？")
    
    if current_idx > 0:
        st.button("⬅️ 回上一項", on_click=stage2_go_back)

    prev_kws = st.session_state.keywords_map.get(current_cat, ["", "", ""])
    
    with st.form(key=f"form_{current_cat}"): 
        # autocomplete="off" 已在 CSS 中全域設定
        k1 = st.text_input("聯想詞 1", value=prev_kws[0], key=f"k1_{current_cat}")
        k2 = st.text_input("聯想詞 2", value=prev_kws[1], key=f"k2_{current_cat}")
        k3 = st.text_input("聯想詞 3", value=prev_kws[2], key=f"k3_{current_cat}")
        
        if st.form_submit_button("下一步"):
            process_stage2_input(current_cat, k1, k2, k3)

elif st.session_state.stage == 3:
    # --- Stage 3: 提煉 ---
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    status_type, p1, p2 = get_stage3_comparison()
    
    st.title(f"💖 第三階段：深層感受 ({st.session_state.stage3_cat_idx+1}/8)")
    st.caption(f"針對「{current_cat}」的聯想詞，請選出感受較深刻的詞。")
    
    if status_type == "ASK":
        st.subheader(f"哪一個感受比較深刻？")
        c1, c2 = st.columns(2)
        if c1.button(f"{p1}", key=f"s3_l_{p1}", use_container_width=True): record_stage3_win(p1, p2)
        if c2.button(f"{p2}", key=f"s3_r_{p2}", use_container_width=True): record_stage3_win(p2, p1)

elif st.session_state.stage == 4:
    # --- Stage 4: 潛意識排序 ---
    st.title("✨ 第四階段：潛意識排序")
    st.caption("請根據關鍵字背後的深層意義選擇。")
    status, p1, p2 = get_sorting_status('final_')
    
    if status == "ASK":
        st.subheader(f"哪一個更重要？")
        c1, c2 = st.columns(2)
        if c1.button(f"🅰️ {p1}", key=f"s4_{p1}", use_container_width=True): record_sorting_win('final_', p1, p2)
        if c2.button(f"🅱️ {p2}", key=f"s4_{p2}", use_container_width=True): record_sorting_win('final_', p2, p1)

elif st.session_state.stage == 5:
    # --- Stage 5: 結果 ---
    st.balloons()
    st.title("🎉 協談完成！")
    
    # 預覽
    radar_buf = create_radar_chart()
    st.image(radar_buf, caption='權重圖')
    
    st.divider()
    st.subheader("潛意識最終排序")
    
    final_data = []
    for i, kw in enumerate(st.session_state.final_ranked_results):
        origin = st.session_state.keyword_to_category.get(kw, "未知")
        final_data.append([i + 1, origin, kw])
    
    df_final = pd.DataFrame(final_data, columns=["順位", "八輪面向", "核心關鍵字"])
    st.table(df_final.set_index('順位'))
        
    st.divider()
    excel_file = generate_excel_report()
    st.download_button(
        label="📥 下載完整協談報表 (Excel)",
        data=excel_file,
        file_name=f"wheel_of_life_{st.session_state.user_info['name']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🔄 重新開始"):
        st.session_state.clear()
        st.rerun()