import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import flet as ft
import google.generativeai as genai
from video_transcription_app import VideoTranscriptionApp

def main(page: ft.Page):
    def on_close(e):
        page.window_destroy()
        os.exit(0)

    page.on_close = on_close
    page.title = "文字起こしくん"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1000
    page.window_height = 1000
    page.window_resizable = False
    page.window_maximizable = False

    settings = {
        "api_key": None,
        "device": "cpu"
    }

    app = VideoTranscriptionApp(page, model=None, device="cpu")
    app.setup_ui()

    def handle_submit(e):
        api_key = api_key_field.value.strip()
        device = device_group.value

        settings["api_key"] = api_key if api_key else None
        settings["device"] = device

        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            app.model = model

        app.device = device

        dialog.open = False
        page.update()
        app.show_device_dialog()

    api_key_field = ft.TextField(
        hint_text="APIキーを入力してください (任意)",
        password=True,
        can_reveal_password=True,
        width=400,
    )

    device_group = ft.RadioGroup(
        content=ft.Column([
            ft.Radio(value="cuda", label="GPU (CUDA)"),
            ft.Radio(value="cpu", label="CPU"),
        ]),
        value="cpu",
    )

    dialog_content = ft.Container(
        width=400,
        content=ft.Column([
            ft.Text("APIキーの入力（任意）", size=16),
            api_key_field,
            ft.Divider(),
            ft.Text("処理デバイスの選択", size=16),
            device_group,
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("開始", on_click=handle_submit),
            ], alignment=ft.MainAxisAlignment.END)
        ], tight=True)
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("設定", size=20, weight=ft.FontWeight.BOLD),
        content=dialog_content,
        actions=[],
    )

    page.dialog = dialog
    dialog.open = True
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
