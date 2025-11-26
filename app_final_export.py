import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 全局變數與配置 ---
ALL_ITEMS = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]
MAX_KEYWORD_COMPARISONS = 3 

# --- 2. 狀態管理與初始化 ---
def initialize_state():
    if 'initialized' not in st.session_state:
        st.session_state.stage = 0  # 0:基本資料, 1:表意識排序...
        
        # === 基本資料 ===
        st.session_state.user_info = {
            "name": "", "job": "", "gender": "", "birthday": "", "age": ""
        }

        # === 排序邏輯通用變數 ===
        # Initial = 表意識 (Stage 1)
        st.session_state.initial_candidates = list(ALL_ITEMS)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = []
        st.session_state.initial_match_history = {}
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        
        # === 關鍵字聯想 (Stage 2) ===
        st.session_state.keywords = {}
        st.session_state.all_used_keywords = set()
        st.session_state.current_keyword_index = 0
        st.session_state.is_keyword_error = False
        
        # === 潛意識提煉 (Stage 3) ===
        st.session_state.deepest_keywords = {} 
        st.session_state.current_category_idx = 0
        st.session_state.comparison_temp_winner = None
        st.session_state.comparison_step_idx = 0 
        st.session_state.keywords_to_compare = None 

        # === 最終排序 (Stage 4) ===
        st.session_state.final_candidates = None 
        st.session_state.final_ranked_results = []
        st.session_state.final_history_stack = []
        st.session_state.final_match_history = {}
        st.session_state.final_current_champion = None
        st.session_state.final_challenger_idx = None

        st.session_state.initialized = True

initialize_state()

# --- 3. 核心邏輯函數 (排序與比較) ---
# ... (此處沿用上一版的核心邏輯，為節省篇幅省略重複代碼，直接使用功能) ...

def get_sorting_status(prefix):
    candidates = st.session_state[f'{prefix}candidates']
    while len(candidates) > 0:
        challenger_idx = st.session_state[f'{prefix}challenger_idx']
        if challenger_idx >= len(candidates):
            winner = st.session_state[f'{prefix}current_champion']
            st.session_state[f'{prefix}ranked_results'].append(winner)
            candidates.remove(winner)
            if len(candidates) == 0: return "DONE", None, None
            
            if st.session_state[f'{prefix}history_stack']:
                while st.session_state[f'{prefix}history_stack']:
                    resurrected = st.session_state[f'{prefix}history_stack'].pop()
                    if resurrected in candidates:
                        st.session_state[f'{prefix}current_champion'] = resurrected
                        break
                else: st.session_state[f'{prefix}current_champion'] = candidates[0]
            else: st.session_state[f'{prefix}current_champion'] = candidates[0]
            
            current_champ_idx = candidates.index(st.session_state[f'{prefix}current_champion'])
            st.session_state[f'{prefix}challenger_idx'] = current_champ_idx + 1
            continue

        challenger = candidates[challenger_idx]
        champion = st.session_state[f'{prefix}current_champion']
        if (champion, challenger) in st.session_state[f'{prefix}match_history'] or \
           (challenger, champion) in st.session_state[f'{prefix}match_history']:
            st.session_state[f'{prefix}challenger_idx'] += 1
            continue
        return "ASK", champion, challenger
    return "DONE", None, None

def record_sorting_win(prefix, winner, loser):
    st.session_state[f'{prefix}match_history'][(winner, loser)] = True
    if winner == st.session_state[f'{prefix}current_champion']:
        st.session_state[f'{prefix}challenger_idx'] += 1
    else:
        st.session_state[f'{prefix}history_stack'].append(st.session_state[f'{prefix}current_champion'])
        st.session_state[f'{prefix}current_champion'] = winner
        st.session_state[f'{prefix}challenger_idx'] += 1
    
    status, _, _ = get_sorting_status(prefix)
    if status == "DONE":
        if prefix == 'initial_': st.session_state.stage = 2
        elif prefix == 'final_': st.session_state.stage = 5
    st.rerun()

def process_keywords(category, k1, k2, k3):
    inputs = [k.strip() for k in [k1, k2, k3] if k.strip()]
    if len(set(inputs)) != 3: return "錯誤：請確保 3 個關鍵字都不相同！"
    for word in inputs:
        if word in ALL_ITEMS: return f"錯誤：'{word}' 不能是八大面向的名稱。"
        if word in st.session_state.all_used_keywords: return f"錯誤：'{word}' 已經使用過了。"
    
    st.session_state.keywords[category] = inputs
    st.session_state.all_used_keywords.update(inputs)
    st.session_state.current_keyword_index += 1
    
    if st.session_state.current_keyword_index >= 8: st.session_state.stage = 3
    st.rerun()

def get_keyword_comparison_status():
    current_category = st.session_state.initial_ranked_results[st.session_state.current_category_idx]
    if st.session_state.comparison_step_idx == 0:
        st.session_state.keywords_to_compare = st.session_state.keywords[current_category]
        st.session_state.comparison_step_idx = 1
        st.session_state.comparison_temp_winner = None
        return "ASK", st.session_state.keywords_to_compare[0], st.session_state.keywords_to_compare[1]
    elif st.session_state.comparison_step_idx == 1:
        return "ASK", st.session_state.comparison_temp_winner, st.session_state.keywords_to_compare[2]
    elif st.session_state.comparison_step_idx == 2:
        k_list = st.session_state.keywords_to_compare
        winner_2 = st.session_state.comparison_temp_winner
        loser_1 = k_list[0] if k_list[0] != winner_2 else k_list[1]
        return "ASK", winner_2, loser_1
    return "DONE", None, None

def record_keyword_win(winner, loser):
    if st.session_state.comparison_step_idx <= 2:
        st.session_state.comparison_temp_winner = winner
        st.session_state.comparison_step_idx += 1
    
    current_category = st.session_state.initial_ranked_results[st.session_state.current_category_idx]
    if st.session_state.comparison_step_idx > 3: # Max steps
        st.session_state.deepest_keywords[current_category] = st.session_state.comparison_temp_winner
        st.session_state.current_category_idx += 1
        st.session_state.comparison_step_idx = 0
        if st.session_state.current_category_idx >= 8:
            st.session_state.stage = 4
            st.session_state.final_candidates = list(st.session_state.deepest_keywords.values())
            st.session_state.final_current_champion = st.session_state.final_candidates[0]
            st.session_state.final_challenger_idx = 1
    st.rerun()

# --- 4. Excel 生成函數 (仿造範本格式) ---

def generate_excel_report():
    output = io.BytesIO()
    # 使用 xlsxwriter 引擎
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 建立 DataFrame (雖然我們主要用 writer 直接寫入，但需要一個 dummy df 來 init)
    df_dummy = pd.DataFrame()
    df_dummy.to_excel(workbook, sheet_name='協談結果', index=False)
    
    worksheet = workbook.sheets['協談結果']
    
    # --- 定義格式 ---
    fmt_header = workbook.book.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
    fmt_label = workbook.book.add_format({'bold': True, 'align': 'right', 'bg_color': '#f0f0f0', 'border': 1})
    fmt_value = workbook.book.add_format({'align': 'left', 'border': 1})
    fmt_table_head = workbook.book.add_format({'bold': True, 'align': 'center', 'bg_color': '#4CAF50', 'font_color': 'white', 'border': 1})
    fmt_cell_center = workbook.book.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    
    # --- 寫入基本資料 (仿造範本上方) ---
    info = st.session_state.user_info
    today_str = date.today().strftime("%Y-%m-%d")
    
    # 設定欄寬
    worksheet.set_column('A:A', 5)   # 排序
    worksheet.set_column('B:B', 20)  # Label
    worksheet.set_column('C:C', 20)  # Value
    worksheet.set_column('D:D', 20)  # Label
    worksheet.set_column('E:E', 20)  # Value
    
    worksheet.merge_range('A1:E1', '人生八輪協談紀錄表', fmt_header)
    
    # Row 2
    worksheet.write('B2', '協談者：', fmt_label)
    worksheet.write('C2', info['name'], fmt_value)
    worksheet.write('D2', '協談日期：', fmt_label)
    worksheet.write('E2', today_str, fmt_value)
    
    # Row 3
    worksheet.write('B3', '職  業：', fmt_label)
    worksheet.write('C3', info['job'], fmt_value)
    worksheet.write('D3', '性  別：', fmt_label)
    worksheet.write('E3', info['gender'], fmt_value)
    
    # Row 4
    worksheet.write('B4', '生  日：', fmt_label)
    worksheet.write('C4', info['birthday'], fmt_value)
    worksheet.write('D4', '年  齡：', fmt_label)
    worksheet.write('E4', info['age'], fmt_value)
    
    # --- 寫入對照表 (仿造範本下方) ---
    # Headers
    start_row = 6
    worksheet.merge_range(f'B{start_row}:C{start_row}', '表意識 (人生八輪)', fmt_table_head)
    worksheet.merge_range(f'D{start_row}:E{start_row}', '潛意識 (核心價值)', fmt_table_head)
    
    # 準備資料
    conscious_list = st.session_state.initial_ranked_results # 表意識排序結果
    subconscious_list = st.session_state.final_ranked_results # 潛意識排序結果
    
    # 為了讓潛意識那一欄顯示「它是哪個面向的代表」，我們需要反查
    # 建立一個反查字典: {關鍵字: 面向名稱}
    keyword_to_category = {v: k for k, v in st.session_state.deepest_keywords.items()}

    for i in range(8):
        row = start_row + 1 + i
        rank = i + 1
        
        # 寫入排名
        worksheet.write(row, 0, rank, fmt_cell_center)
        
        # 寫入表意識 (合併 B, C)
        c_item = conscious_list[i] if i < len(conscious_list) else ""
        worksheet.merge_range(f'B{row+1}:C{row+1}', c_item, fmt_cell_center)
        
        # 寫入潛意識 (合併 D, E)
        s_item = subconscious_list[i] if i < len(subconscious_list) else ""
        # 顯示格式：關鍵字 (原面向)
        origin = keyword_to_category.get(s_item, "")
        display_text = f"{s_item}" # 若想加上原面向可改為 f"{s_item} ({origin})"
        
        worksheet.merge_range(f'D{row+1}:E{row+1}', display_text, fmt_cell_center)

    workbook.close()
    output.seek(0)
    return output

# --- 5. 介面渲染 (各階段) ---

# Stage 0: 基本資料
if st.session_state.stage == 0:
    st.title("📋 協談者資料建立")
    st.info("請輸入基本資料，這將顯示在最終的報表中。")
    with st.form("info_form"):
        col1, col2 = st.columns(2)
        st.session_state.user_info['name'] = col1.text_input("姓名", st.session_state.user_info['name'])
        st.session_state.user_info['gender'] = col2.selectbox("性別", ["男", "女", "其他"], index=0)
        st.session_state.user_info['birthday'] = col1.text_input("生日 (YYYY/MM/DD)", st.session_state.user_info['birthday'])
        st.session_state.user_info['age'] = col2.text_input("年齡", st.session_state.user_info['age'])
        st.session_state.user_info['job'] = st.text_input("職業", st.session_state.user_info['job'])
        
        if st.form_submit_button("開始協談"):
            st.session_state.stage = 1
            st.rerun()

# Stage 1: 表意識排序
elif st.session_state.stage == 1:
    st.title("🧬 第一階段：表意識排序")
    status, p1, p2 = get_sorting_status('initial_')
    if status == "ASK":
        st.write(f"哪一個比較重要？")
        c1, c2 = st.columns(2)
        if c1.button(f"🅰️ {p1}", use_container_width=True): record_sorting_win('initial_', p1, p2)
        if c2.button(f"🅱️ {p2}", use_container_width=True): record_sorting_win('initial_', p2, p1)

# Stage 2: 關鍵字聯想
elif st.session_state.stage == 2:
    idx = st.session_state.current_keyword_index
    cat = st.session_state.initial_ranked_results[idx]
    st.title(f"💡 第二階段：聯想 ({cat})")
    with st.form("kw_form"):
        k1 = st.text_input("聯想 1")
        k2 = st.text_input("聯想 2")
        k3 = st.text_input("聯想 3")
        if st.form_submit_button("下一項"): process_keywords(cat, k1, k2, k3)

# Stage 3: 潛意識代表
elif st.session_state.stage == 3:
    st.title("💖 第三階段：深層感受")
    status, p1, p2 = get_keyword_comparison_status()
    if status == "ASK":
        st.write(f"哪一個感受更深刻？")
        c1, c2 = st.columns(2)
        if c1.button(f"{p1}", use_container_width=True): record_keyword_win(p1, p2)
        if c2.button(f"{p2}", use_container_width=True): record_keyword_win(p2, p1)

# Stage 4: 潛意識排序
elif st.session_state.stage == 4:
    st.title("✨ 第四階段：潛意識排序")
    status, p1, p2 = get_sorting_status('final_')
    if status == "ASK":
        st.write(f"哪一個對你的生命更重要？")
        c1, c2 = st.columns(2)
        if c1.button(f"{p1}", use_container_width=True): record_sorting_win('final_', p1, p2)
        if c2.button(f"{p2}", use_container_width=True): record_sorting_win('final_', p2, p1)

# Stage 5: 最終報表
elif st.session_state.stage == 5:
    st.balloons()
    st.title("🎉 協談完成！")
    
    # 顯示預覽
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("表意識 (排序)")
        st.dataframe(pd.DataFrame(st.session_state.initial_ranked_results, columns=["面向"]), use_container_width=True)
    with col2:
        st.subheader("潛意識 (核心價值)")
        st.dataframe(pd.DataFrame(st.session_state.final_ranked_results, columns=["關鍵字"]), use_container_width=True)

    st.divider()
    
    # 生成 Excel
    excel_file = generate_excel_report()
    
    st.download_button(
        label="📥 下載完整協談報表 (Excel)",
        data=excel_file,
        file_name=f"人生八輪協談_{st.session_state.user_info['name']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🔄 開始新的協談"):
        st.session_state.clear()
        st.rerun()