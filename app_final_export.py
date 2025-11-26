import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 全局配置 ---
# 八大面向固定名稱
ALL_ITEMS = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]

# --- 2. 狀態管理與初始化 ---
def initialize_state():
    if 'initialized' not in st.session_state:
        st.session_state.stage = 0  # 流程控制
        
        # === 基本資料 ===
        st.session_state.user_info = {
            "name": "", "job": "", "gender": "", "birthday": "", "age": ""
        }

        # === Stage 1: 表意識排序 (堆疊回溯法) ===
        st.session_state.initial_candidates = list(ALL_ITEMS)
        st.session_state.initial_ranked_results = []
        st.session_state.initial_history_stack = [] # 暫存輸家
        st.session_state.initial_match_history = {} # 避免重複問
        st.session_state.initial_current_champion = st.session_state.initial_candidates[0]
        st.session_state.initial_challenger_idx = 1
        
        # === Stage 2: 關鍵字聯想 ===
        st.session_state.keywords_map = {} # {面向: [k1, k2, k3]}
        st.session_state.all_used_keywords = set() # 用於檢查全域重複
        st.session_state.current_keyword_index = 0
        
        # === Stage 3: 潛意識代表提煉 (A1 vs A2 -> Win vs A3) ===
        st.session_state.deepest_keywords = {} # {面向: 最終代表詞}
        st.session_state.stage3_cat_idx = 0
        st.session_state.stage3_step = 1 # 1: k1 vs k2, 2: Win vs k3
        st.session_state.stage3_temp_winner = None

        # === Stage 4: 潛意識最終排序 (堆疊回溯法 - 邏輯同 Stage 1) ===
        st.session_state.final_candidates = [] # 將填入 8 個代表詞
        st.session_state.final_ranked_results = []
        st.session_state.final_history_stack = []
        st.session_state.final_match_history = {}
        st.session_state.final_current_champion = None
        st.session_state.final_challenger_idx = 1
        
        # 反查字典：用於最後將「代表詞」轉回「面向名稱」
        st.session_state.keyword_to_category = {} 

        st.session_state.initialized = True

initialize_state()

# --- 3. 通用排序邏輯引擎 (適用於 Stage 1 & Stage 4) ---
# 這是您指定的「從A開始比，輸的進堆疊，贏的繼續比，比完回頭找」的演算法

def get_sorting_status(prefix):
    """
    prefix: 'initial_' (表意識) 或 'final_' (潛意識)
    回傳: ("ASK", p1, p2) 或 ("DONE", None, None)
    """
    candidates = st.session_state[f'{prefix}candidates']
    ranked_list = st.session_state[f'{prefix}ranked_results']
    stack = st.session_state[f'{prefix}history_stack']
    history = st.session_state[f'{prefix}match_history']
    
    # 若還有候選人沒排完
    while len(candidates) > 0:
        champion = st.session_state[f'{prefix}current_champion']
        challenger_idx = st.session_state[f'{prefix}challenger_idx']
        
        # 狀況 A: 當前擂台主已經比完列表後面所有人 -> 確定是第一名 (或當前最高順位)
        if challenger_idx >= len(candidates):
            # 1. 紀錄排名
            ranked_list.append(champion)
            # 2. 從候選名單移除
            candidates.remove(champion)
            
            # 若全部排完，結束
            if len(candidates) == 0:
                return "DONE", None, None
            
            # 3. 回溯邏輯 (Backtracking)
            # 依照您的指示：從 G 往回找上一個認為重要的 E...
            if stack:
                # 從堆疊最上面拿出一個「還沒畢業」的候選人
                found_resurrected = False
                while stack:
                    resurrected = stack.pop()
                    if resurrected in candidates:
                        st.session_state[f'{prefix}current_champion'] = resurrected
                        found_resurrected = True
                        break
                
                # 如果堆疊裡的人都已經排完名了(極少見但防呆)，就抓清單第一個
                if not found_resurrected:
                    st.session_state[f'{prefix}current_champion'] = candidates[0]
            else:
                # 堆疊空的，抓清單第一個
                st.session_state[f'{prefix}current_champion'] = candidates[0]
            
            # 4. 重設挑戰者索引 (從擂台主的下一位開始)
            current_champ_idx = candidates.index(st.session_state[f'{prefix}current_champion'])
            st.session_state[f'{prefix}challenger_idx'] = current_champ_idx + 1
            continue # 繼續迴圈處理下一輪

        # 狀況 B: 還有挑戰者，準備進行比較
        challenger = candidates[challenger_idx]
        
        # 檢查快取：這兩人是否比過？
        if (champion, challenger) in history: # Champion 贏過
            st.session_state[f'{prefix}challenger_idx'] += 1
            continue
        elif (challenger, champion) in history: # Challenger 贏過
            # 這裡的邏輯不同於底下 user 點擊，因為是歷史紀錄回放，我們要模擬當時的交換
            stack.append(champion)
            st.session_state[f'{prefix}current_champion'] = challenger
            st.session_state[f'{prefix}challenger_idx'] += 1
            continue
        
        # 狀況 C: 沒比過，必須問使用者
        return "ASK", champion, challenger

    return "DONE", None, None

def record_sorting_win(prefix, winner, loser):
    """處理使用者點擊後的邏輯"""
    # 記錄勝負
    st.session_state[f'{prefix}match_history'][(winner, loser)] = True
    
    current_champ = st.session_state[f'{prefix}current_champion']
    
    if winner == current_champ:
        # 擂台主贏了 -> 挑戰者換下一位
        st.session_state[f'{prefix}challenger_idx'] += 1
    else:
        # 擂台主輸了 -> 舊擂台主入堆疊 (等待回溯)
        st.session_state[f'{prefix}history_stack'].append(current_champ)
        # 贏家成為新擂台主
        st.session_state[f'{prefix}current_champion'] = winner
        # 挑戰者換下一位
        st.session_state[f'{prefix}challenger_idx'] += 1
    
    # 檢查是否完成
    status, _, _ = get_sorting_status(prefix)
    if status == "DONE":
        if prefix == 'initial_':
            st.session_state.stage = 2 # 進入聯想
        elif prefix == 'final_':
            st.session_state.stage = 5 # 進入結果
    st.rerun()

# --- 4. 關鍵字處理邏輯 (Stage 2 & 3) ---

def process_stage2_input(category, k1, k2, k3):
    # 1. 檢查空值
    if not k1 or not k2 or not k3:
        st.error(f"⚠️ 請填滿 3 個聯想詞！針對「{category}」您還有欄位未填寫。")
        return

    inputs = [k.strip() for k in [k1, k2, k3]]
    
    # 2. 檢查該組內的重複
    if len(set(inputs)) != 3:
        st.error(f"⚠️ 聯想詞重複！請確保 3 個詞都不一樣。")
        return
        
    # 3. 檢查與八大面向名稱重複
    for word in inputs:
        if word in ALL_ITEMS:
            st.error(f"⚠️ 關鍵字不能與八大面向名稱（如：{word}）相同，請更換。")
            return
    
    # 4. 檢查全域重複 (跟之前填過的其他面向比較)
    for word in inputs:
        if word in st.session_state.all_used_keywords:
            st.error(f"⚠️ 關鍵字「{word}」在之前的面向已經使用過了，請輸入新的詞彙。")
            return

    # 通過檢查 -> 儲存
    st.session_state.keywords_map[category] = inputs
    st.session_state.all_used_keywords.update(inputs)
    
    # 建立反查索引 (為了 Stage 4 結束後能查回面向)
    for word in inputs:
        st.session_state.keyword_to_category[word] = category
    
    st.session_state.current_keyword_index += 1
    
    if st.session_state.current_keyword_index >= 8:
        st.session_state.stage = 3 # 進入提煉
    st.rerun()

def process_stage3_win(winner, loser):
    # 記錄當前勝者
    st.session_state.stage3_temp_winner = winner
    
    # 推進步驟
    if st.session_state.stage3_step == 1:
        # 剛比完 A1 vs A2，現在 winner 要去跟 A3 比
        st.session_state.stage3_step = 2
    else:
        # 比完第 2 步 (Win vs A3)，這就是最終代表了
        cat_list = st.session_state.initial_ranked_results # 依表意識順序
        current_cat = cat_list[st.session_state.stage3_cat_idx]
        
        st.session_state.deepest_keywords[current_cat] = winner
        
        # 準備下一個面向
        st.session_state.stage3_cat_idx += 1
        st.session_state.stage3_step = 1
        st.session_state.stage3_temp_winner = None
        
        # 檢查是否全部提煉完成
        if st.session_state.stage3_cat_idx >= 8:
            st.session_state.stage = 4
            # 初始化 Stage 4 參數
            # 注意：這裡的 candidates 是 8 個關鍵字
            # 順序依照 Stage 1 的排名順序放入 (如您例子：A1, B2, C1...)
            sorted_cats = st.session_state.initial_ranked_results
            final_kws = [st.session_state.deepest_keywords[c] for c in sorted_cats]
            
            st.session_state.final_candidates = final_kws
            st.session_state.final_current_champion = final_kws[0]
            st.session_state.final_challenger_idx = 1
            
    st.rerun()

# --- 5. Excel 報表生成 ---
def generate_excel_report():
    output = io.BytesIO()
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 建立一個空的 sheet
    df_dummy = pd.DataFrame()
    df_dummy.to_excel(workbook, sheet_name='協談結果', index=False)
    worksheet = workbook.sheets['協談結果']
    
    # 格式設定
    fmt_header = workbook.book.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
    fmt_label = workbook.book.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1})
    fmt_value = workbook.book.add_format({'align': 'left', 'border': 1})
    fmt_th = workbook.book.add_format({'bold': True, 'align': 'center', 'bg_color': '#4CAF50', 'font_color': 'white', 'border': 1})
    fmt_center = workbook.book.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    
    # 寫入基本資料
    info = st.session_state.user_info
    worksheet.merge_range('A1:E1', '人生八輪協談紀錄表', fmt_header)
    
    fields = [
        ('B2', '協談者：', 'C2', info['name']),
        ('D2', '協談日期：', 'E2', date.today().strftime("%Y-%m-%d")),
        ('B3', '職  業：', 'C3', info['job']),
        ('D3', '性  別：', 'E3', info['gender']),
        ('B4', '生  日：', 'C4', info['birthday']),
        ('D4', '年  齡：', 'E4', info['age'])
    ]
    for cell_l, label, cell_v, value in fields:
        worksheet.write(cell_l, label, fmt_label)
        worksheet.write(cell_v, value, fmt_value)

    # 寫入列表標頭
    worksheet.merge_range('B6:C6', '表意識 (人生八輪)', fmt_th)
    worksheet.merge_range('D6:E6', '潛意識 (核心價值)', fmt_th)
    
    # 準備資料
    # 表意識：initial_ranked_results (面向名稱)
    conscious_list = st.session_state.initial_ranked_results
    # 潛意識：final_ranked_results (關鍵字) -> 轉回 面向名稱
    subconscious_keywords = st.session_state.final_ranked_results
    
    for i in range(8):
        row = 6 + 1 + i
        # 排名 A欄
        worksheet.write(row, 0, i + 1, fmt_center)
        
        # 表意識
        c_item = conscious_list[i] if i < len(conscious_list) else ""
        worksheet.merge_range(f'B{row+1}:C{row+1}', c_item, fmt_center)
        
        # 潛意識
        # 邏輯：顯示 "關鍵字 (對應面向)"
        if i < len(subconscious_keywords):
            s_kw = subconscious_keywords[i]
            s_origin = st.session_state.keyword_to_category.get(s_kw, "未知")
            # 格式範例： "存款10億 (財富)"
            display_text = f"{s_kw} ({s_origin})"
        else:
            display_text = ""
            
        worksheet.merge_range(f'D{row+1}:E{row+1}', display_text, fmt_center)

    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:E', 18)
    
    workbook.close()
    output.seek(0)
    return output

# --- 6. 介面渲染 (UI) ---

# Stage 0: 基本資料
if st.session_state.stage == 0:
    st.title("📋 基本資料")
    with st.form("info_form"):
        col1, col2 = st.columns(2)
        st.session_state.user_info['name'] = col1.text_input("姓名")
        st.session_state.user_info['gender'] = col2.selectbox("性別", ["男", "女", "其他"])
        st.session_state.user_info['birthday'] = col1.text_input("生日 (YYYY/MM/DD)")
        st.session_state.user_info['age'] = col2.text_input("年齡")
        st.session_state.user_info['job'] = st.text_input("職業")
        
        if st.form_submit_button("開始測驗"):
            st.session_state.stage = 1
            st.rerun()

# Stage 1: 表意識排序
elif st.session_state.stage == 1:
    st.title("🧬 第一階段：表意識排序")
    st.caption("請依直覺選擇，程式會找出您目前最重視的面向。")
    
    status, p1, p2 = get_sorting_status('initial_')
    
    if status == "ASK":
        st.subheader(f"哪一個比較重要？")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"🅰️ {p1}", key=f"s1_{p1}", use_container_width=True):
                record_sorting_win('initial_', p1, p2)
        with col2:
            if st.button(f"🅱️ {p2}", key=f"s1_{p2}", use_container_width=True):
                record_sorting_win('initial_', p2, p1)

# Stage 2: 關鍵字聯想 (重點修改：動態 Key 與 驗證)
elif st.session_state.stage == 2:
    # 依據表意識排序的順序來問
    current_idx = st.session_state.current_keyword_index
    sorted_cats = st.session_state.initial_ranked_results
    current_cat = sorted_cats[current_idx]
    
    st.title(f"💡 第二階段：聯想 ({current_idx+1}/8)")
    st.subheader(f"看到「{current_cat}」，你會想到什麼？")
    st.info("請輸入 3 個不重複的關鍵字（人、事、物、感受皆可）。")
    
    # 使用 form
    with st.form(key=f"form_{current_cat}"): # 動態 key，確保切換面向時清空
        # 動態 key，確保欄位清空
        k1 = st.text_input("聯想詞 1", key=f"k1_{current_cat}")
        k2 = st.text_input("聯想詞 2", key=f"k2_{current_cat}")
        k3 = st.text_input("聯想詞 3", key=f"k3_{current_cat}")
        
        submit = st.form_submit_button("下一步")
        
        if submit:
            process_stage2_input(current_cat, k1, k2, k3)

# Stage 3: 潛意識代表提煉 (A1 vs A2, Win vs A3)
elif st.session_state.stage == 3:
    cat_list = st.session_state.initial_ranked_results
    current_cat = cat_list[st.session_state.stage3_cat_idx]
    keywords = st.session_state.keywords_map[current_cat] # [k1, k2, k3]
    
    st.title(f"💖 第三階段：深層感受提煉")
    st.caption(f"針對「{current_cat}」，請選出感受較深刻的詞。")
    
    # 決定要比對哪兩個詞
    if st.session_state.stage3_step == 1:
        p1, p2 = keywords[0], keywords[1]
    else:
        p1 = st.session_state.stage3_temp_winner
        p2 = keywords[2]
        
    st.subheader(f"哪一個感受比較深刻？")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{p1}", key=f"s3_l_{p1}", use_container_width=True):
            process_stage3_win(p1, p2)
    with col2:
        if st.button(f"{p2}", key=f"s3_r_{p2}", use_container_width=True):
            process_stage3_win(p2, p1)

# Stage 4: 潛意識最終排序 (堆疊回溯法)
elif st.session_state.stage == 4:
    st.title("✨ 第四階段：潛意識最終排序")
    st.caption("請根據這些關鍵字背後的深層意義，選出對您生命更重要的一方。")
    
    status, p1, p2 = get_sorting_status('final_')
    
    if status == "ASK":
        st.subheader(f"哪一個比較重要？")
        col1, col2 = st.columns(2)
        # 顯示時可以稍微提示該關鍵字來自哪個面向 (選填，目前只顯示關鍵字)
        with col1:
            if st.button(f"🅰️ {p1}", key=f"s4_{p1}", use_container_width=True):
                record_sorting_win('final_', p1, p2)
        with col2:
            if st.button(f"🅱️ {p2}", key=f"s4_{p2}", use_container_width=True):
                record_sorting_win('final_', p2, p1)

# Stage 5: 結果與下載
elif st.session_state.stage == 5:
    st.balloons()
    st.title("🎉 協談完成！")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("表意識 (八輪排序)")
        st.table(pd.DataFrame(st.session_state.initial_ranked_results, columns=["面向"]))
    with col2:
        st.info("潛意識 (核心價值)")
        # 顯示 關鍵字 + 原始面向
        display_data = []
        for kw in st.session_state.final_ranked_results:
            origin = st.session_state.keyword_to_category.get(kw, "")
            display_data.append(f"{kw} ({origin})")
        st.table(pd.DataFrame(display_data, columns=["關鍵字 (面向)"]))
        
    st.divider()
    excel_file = generate_excel_report()
    st.download_button(
        label="📥 下載完整協談報表 (Excel)",
        data=excel_file,
        file_name=f"人生八輪_{st.session_state.user_info['name']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🔄 重新開始"):
        st.session_state.clear()
        st.rerun()