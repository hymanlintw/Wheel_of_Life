import streamlit as st
import time

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="人生八輪深度排序", page_icon="🧬")

# CSS 優化按鈕視覺
st.markdown("""
    <style>
    div.stButton > button {
        height: 120px;
        width: 100%;
        font-size: 26px;
        border-radius: 12px;
        border: 2px solid #1E88E5;
        background-color: white;
        color: #1E88E5;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #E3F2FD;
        transform: scale(1.02);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .rank-card {
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 8px;
        margin-bottom: 5px;
        border-left: 5px solid #4CAF50;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化變數 (State Management) ---
if 'initialized' not in st.session_state:
    # 原始清單
    st.session_state.candidates = ["健康", "工作", "家庭", "休閒", "情緒", "成長", "人際", "財富"]
    # 最終排名結果
    st.session_state.ranked_results = []
    # 歷史堆疊 (Stack)：用來存「被挑戰者打敗的前任擂台主」
    st.session_state.history_stack = []
    # 勝負紀錄 (Cache)：避免重複問問題 {(贏家, 輸家): True}
    st.session_state.match_history = {}
    
    # 遊戲狀態指標
    st.session_state.current_champion = st.session_state.candidates[0] # 目前擂台主
    st.session_state.challenger_idx = 1 # 挑戰者在 candidates 中的索引位置
    st.session_state.initialized = True

# --- 3. 核心邏輯函數 ---

def record_win(winner, loser):
    """記錄勝負並調整狀態"""
    # 寫入快取：記住誰贏誰，避免未來重複問
    st.session_state.match_history[(winner, loser)] = True
    
    # 邏輯判斷
    if winner == st.session_state.current_champion:
        # 擂台主衛冕成功 -> 挑戰者換下一位
        st.session_state.challenger_idx += 1
    else:
        # 擂台主輸了 -> 
        # 1. 舊擂台主入庫 (Stack) 等待復活
        st.session_state.history_stack.append(st.session_state.current_champion)
        # 2. 挑戰者成為新擂台主
        st.session_state.current_champion = winner
        # 3. 繼續挑戰列表中的下一位
        st.session_state.challenger_idx += 1

def get_next_battle():
    """
    計算下一場戰鬥。
    這個函數會自動跑迴圈 (Auto-Loop)，直到遇到：
    1. 需要使用者回答的問題 (Return: 'ASK', p1, p2)
    2. 全部排完 (Return: 'DONE')
    """
    
    while len(st.session_state.candidates) > 0:
        
        # 狀況 A：目前的擂台主已經比完列表後面所有的人 -> 確定是當前第一名
        if st.session_state.challenger_idx >= len(st.session_state.candidates):
            # 1. 將冠軍加入最終名單
            winner = st.session_state.current_champion
            st.session_state.ranked_results.append(winner)
            
            # 2. 從候選清單中移除
            st.session_state.candidates.remove(winner)
            
            # 3. 決定下一輪的擂台主是誰 (回溯邏輯)
            if len(st.session_state.candidates) == 0:
                return "DONE", None, None
            
            if st.session_state.history_stack:
                # 優先從堆疊 (Stack) 中復活上一個認為重要的 (如邏輯中的 E, 然後 A)
                # 但要注意，復活的人必須還在 candidates 裡 (防止已排名的被重複抓)
                while st.session_state.history_stack:
                    resurrected = st.session_state.history_stack.pop()
                    if resurrected in st.session_state.candidates:
                        st.session_state.current_champion = resurrected
                        break
                else:
                    # 如果 stack 裡的人都已經畢業了，就抓清單第一個 (如邏輯中的 B)
                    st.session_state.current_champion = st.session_state.candidates[0]
            else:
                # 堆疊空的，抓清單第一個
                st.session_state.current_champion = st.session_state.candidates[0]
            
            # 4. 重置挑戰者索引 (從擂台主的下一位開始比)
            # 因為清單變短了，要重新抓 index
            current_champ_idx = st.session_state.candidates.index(st.session_state.current_champion)
            st.session_state.challenger_idx = current_champ_idx + 1
            
            # 繼續迴圈，處理下一輪
            continue

        # 狀況 B：還有挑戰者，準備進行比較
        challenger = st.session_state.candidates[st.session_state.challenger_idx]
        champion = st.session_state.current_champion
        
        # 檢查快取：這兩人是否比過？(例如 A 曾在上一輪贏過 B)
        if (champion, challenger) in st.session_state.match_history:
            # Champion 曾贏過 -> 自動判定勝，繼續下一位
            st.session_state.challenger_idx += 1
            continue
        elif (challenger, champion) in st.session_state.match_history:
            # Challenger 曾贏過 -> 自動判定勝 (換人)，繼續下一位
            st.session_state.history_stack.append(champion)
            st.session_state.current_champion = challenger
            st.session_state.challenger_idx += 1
            continue
        
        # 狀況 C：沒比過，必須問使用者
        return "ASK", champion, challenger

    return "DONE", None, None

# --- 4. 介面渲染 (UI Rendering) ---

st.title("🧬 人生價值觀深度排序")
st.progress(len(st.session_state.ranked_results) / 8, text="排序進度")

# 執行邏輯引擎，取得當前狀態
status, p1, p2 = get_next_battle()

if status == "ASK":
    st.write("")
    st.markdown(f"### ⚔️ 靈魂拷問：哪一個對你更重要？")
    st.caption("請依直覺選擇，程式會自動記憶並推算後續結果。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"🅰️ {p1}", key="btn_p1"):
            record_win(p1, p2)
            st.rerun() # 重新執行以載入下一題

    with col2:
        if st.button(f"🅱️ {p2}", key="btn_p2"):
            record_win(p2, p1)
            st.rerun()

elif status == "DONE":
    st.balloons()
    st.success("🎉 分析完成！這是你潛意識中的價值排序：")
    
    st.markdown("---")
    for i, item in enumerate(st.session_state.ranked_results):
        rank = i + 1
        # 前三名給予特殊樣式
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"No.{rank}"
        st.markdown(f"""
        <div class="rank-card">
            <span style="font-size:1.2em; font-weight:bold;">{medal} &nbsp; {item}</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    if st.button("🔄 重新測試"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 顯示除錯資訊 (可選，讓你知道程式在想什麼) ---
# with st.expander("🔍 查看程式邏輯狀態 (Debug)"):
#     st.write(f"已排名: {st.session_state.ranked_results}")
#     st.write(f"剩餘清單: {st.session_state.candidates}")
#     st.write(f"歷史堆疊(Stack): {st.session_state.history_stack}")
#     st.write(f"目前擂台主: {st.session_state.current_champion}")
#     st.write(f"下一位對手索引: {st.session_state.challenger_idx}")