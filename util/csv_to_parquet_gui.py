# 릴리즈 파일을 만들기 위해 필요한 명령어
# pyinstaller --noconsole --onefile csv_to_parquet_gui.py

import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os

def select_file():
    file_path = filedialog.askopenfilename(
        title="CSV 파일 선택",
        filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
    )
    if file_path:
        entry_path.delete(0, tk.END)
        entry_path.insert(0, file_path)

def convert_file():
    csv_path = entry_path.get()
    if not csv_path:
        messagebox.showwarning("경고", "먼저 CSV 파일을 선택해주세요.")
        return
    
    try:
        lbl_status.config(text="변환 중...", fg="blue")
        root.update()
        
        # 1. 안전한 확장자 변경
        base_name, _ = os.path.splitext(csv_path)
        parquet_path = base_name + '.parquet'
        
        # 2. 한글 인코딩 예외 처리 추가
        try:
            df = pd.read_csv(csv_path) # 기본 utf-8 시도
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding='cp949') # 실패 시 cp949 시도
            
        df.to_parquet(parquet_path, engine='pyarrow')
        
        lbl_status.config(text="완료!", fg="green")
        messagebox.showinfo("성공", f"변환 완료!\n저장 위치: {parquet_path}")
        
    except Exception as e:
        lbl_status.config(text="오류 발생", fg="red")
        messagebox.showerror("에러", f"변환 중 오류가 발생했습니다:\n{str(e)}")

# GUI 설정
root = tk.Tk()
root.title("CSV to Parquet 변환기")
root.geometry("450x160")

# UI 요소
frame = tk.Frame(root, padx=10, pady=10)
frame.pack(fill=tk.BOTH, expand=True)

lbl_inst = tk.Label(frame, text="변환할 CSV 파일을 선택하세요:")
lbl_inst.pack(anchor=tk.W)

file_frame = tk.Frame(frame)
file_frame.pack(fill=tk.X, pady=5)

entry_path = tk.Entry(file_frame, width=40)
entry_path.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

btn_browse = tk.Button(file_frame, text="찾아보기", command=select_file)
btn_browse.pack(side=tk.RIGHT)

btn_convert = tk.Button(frame, text="Parquet으로 변환", command=convert_file, bg="#4CAF50", fg="white")
btn_convert.pack(pady=10)

lbl_status = tk.Label(frame, text="")
lbl_status.pack()

root.mainloop()