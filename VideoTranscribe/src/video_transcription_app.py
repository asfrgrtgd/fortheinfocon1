import flet as ft
import flet_video as ftv
from faster_whisper import WhisperModel
from moviepy.editor import VideoFileClip
import os
import threading
import asyncio
from datetime import timedelta
import tempfile

class VideoTranscriptionApp:
    def __init__(self, page: ft.Page, model, device):
        self.page = page
        self.model = model
        self.whisper_model = None
        self.current_file = None
        self.device = device
        self.sections = {
            "transcription": "",
            "summary": "",
            "topics": "",
            "subtitles": []
        }
        self.current_subtitle_index = 0
        self.current_time_text = ft.Text(value="現在の再生時間: 00:00.000", size=16)
        self.video_player = ftv.Video(width=1280, height=720)

    def show_device_dialog(self):
        def close_dialog(_):
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("処理デバイスの設定完了", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Text("設定が完了しました。動画ファイルを選択してください。", size=16),
            actions=[
                ft.TextButton("閉じる", on_click=close_dialog)
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def setup_ui(self):
        self.page.padding = 20
        self.page.fonts = {"Yu Gothic UI": "Yu Gothic UI"}

        self.file_picker = ft.FilePicker(on_result=self.handle_file_picked)
        self.page.overlay.append(self.file_picker)

        self.select_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.UPLOAD_FILE),
                    ft.Text("動画ファイルを選択", size=16),
                ],
                spacing=20,
            ),
            style=ft.ButtonStyle(padding=20),
            on_click=lambda _: self.file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["mp4", "avi", "mov", "mkv"]
            )
        )

        self.progress_bar = ft.ProgressBar(visible=False)
        self.progress_text = ft.Text("", size=14)

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="文字起こし",
                    icon=ft.icons.TEXT_FIELDS,
                    content=ft.Container(
                        content=self.create_text_section("transcription"),
                        padding=10
                    ),
                ),
                ft.Tab(
                    text="概要",
                    icon=ft.icons.SHORT_TEXT,
                    content=ft.Container(
                        content=self.create_text_section("summary"),
                        padding=10
                    ),
                ),
                ft.Tab(
                    text="話題別要約",
                    icon=ft.icons.FORMAT_LIST_BULLETED,
                    content=ft.Container(
                        content=self.create_text_section("topics"),
                        padding=10
                    ),
                ),
                ft.Tab(
                    text="字幕付き動画",
                    icon=ft.icons.MOVIE,
                    content=ft.Container(
                        content=self.create_video_section(),
                        padding=10
                    ),
                ),
            ],
        )

        self.page.add(
            ft.Column(
                controls=[
                    ft.Container(
                        content=self.select_button,
                        alignment=ft.alignment.center,
                    ),
                    ft.Row([self.progress_text], alignment=ft.MainAxisAlignment.CENTER),
                    self.progress_bar,
                    ft.Divider(),
                    self.tabs,
                ],
                spacing=10,
            )
        )

    def create_text_section(self, section_name: str):
        t = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=26,
            max_lines=26,
            value="",
            text_size=15,
        )
        b = ft.IconButton(
            icon=ft.icons.COPY,
            tooltip="テキストをコピー",
            on_click=lambda e: self.copy_text(t.value),
        )
        return ft.Column([
            ft.Row([b], alignment=ft.MainAxisAlignment.END),
            t,
        ])

    def create_video_section(self, playlist=None):
        if playlist is None:
            playlist = self.video_player.playlist
        self.video_player = ftv.Video(
            expand=True,
            playlist=playlist,
            fill_color=None,
            aspect_ratio=16 / 9,
            width=1280,
            height=720,
            volume=50,
            autoplay=False,
            filter_quality=ft.FilterQuality.HIGH,
            on_loaded=self.on_video_loaded
        )
        self.subtitle_text = ft.Text(
            value="",
            size=20,
            text_align=ft.TextAlign.CENTER,
            weight=ft.FontWeight.BOLD
        )
        return ft.Column([
            self.video_player,
            ft.Container(
                content=self.subtitle_text,
                padding=20,
                bgcolor=ft.colors.BLACK54,
                border_radius=10,
                alignment=ft.alignment.center,
            ),
        ])

    def update_section_text(self, section: str, text: str):
        self.sections[section] = text
        i = {"transcription": 0, "summary": 1, "topics": 2}[section]
        text_field = self.tabs.tabs[i].content.content.controls[1]
        text_field.value = text
        self.page.update()

    def copy_text(self, text: str):
        self.page.set_clipboard(text)
        self.show_snackbar("テキストをコピーしました")

    def show_snackbar(self, message: str):
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(message),
                action="閉じる",
            )
        )

    def handle_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.current_file = file_path
                self.progress_bar.visible = True
                self.update_progress("動画を処理中...")
                self.page.update()
                threading.Thread(target=self.process_video, args=(file_path,), daemon=True).start()
            else:
                self.show_snackbar("エラー: 対応していないファイル形式です")

    def format_timestamp(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))

    def extract_audio(self, video_path: str) -> str:
        self.update_progress("音声を抽出中...")
        v = VideoFileClip(video_path)
        temp_audio = tempfile.mktemp(suffix=".wav")
        v.audio.write_audiofile(temp_audio, verbose=False, logger=None)
        v.close()
        return temp_audio

    def update_progress(self, text: str):
        self.progress_text.value = text
        self.page.update()

    def process_video(self, video_path: str):
        audio_path = None
        try:
            audio_path = self.extract_audio(video_path)

            if self.whisper_model is None:
                self.update_progress("Whisperモデルを読み込み中...")
                self.whisper_model = WhisperModel("large-v3-turbo", device=self.device, compute_type="auto")

            self.update_progress("文字起こし中...")
            segments, _ = self.whisper_model.transcribe(audio_path,language="ja")
            st = ""
            st_ts = ""
            subs = []
            for s in segments:
                sm = s.start * 1000
                em = s.end * 1000
                ts_str = self.format_timestamp(s.start)
                st_ts += f"[{ts_str}] {s.text}\n"
                st += s.text + " "
                subs.append({"start": sm, "end": em, "text": s.text})
            self.update_section_text("transcription", st_ts)

            if self.model:
                self.update_progress("概要を生成中...")
                r1 = self.model.generate_content(f"以下の文章の要約を作成してください。\n\n{st}")
                self.update_section_text("summary", r1.text)

                self.update_progress("話題別要約を生成中...")
                r2 = self.model.generate_content(
                    f"以下の文章を主要な話題ごとに分けて要約してください。\n"
                    f"各話題について:\n- 話題のタイトル\n- タイムスタンプ(タイムスタンプという文字列は入れないでくださいフォーマットはh:m:s)（例 01:10:00 - 01:12:30）\n"
                    f"- 50-200文字程度の要約\n\n"
                    f"{st_ts}"
                )
                self.update_section_text("topics", r2.text)
            else:
                self.update_section_text("summary", "APIキーが提供されていないため、概要の生成をスキップしました。")
                self.update_section_text("topics", "APIキーが提供されていないため、話題別要約の生成をスキップしました。")

            self.sections["subtitles"] = subs
            pl = [ftv.VideoMedia(os.path.normpath(video_path))]
            self.tabs.tabs[3].content.content.controls = self.create_video_section(playlist=pl).controls
            self.page.update()

            self.update_progress("処理完了")
            self.progress_bar.visible = False
            self.page.update()

        except Exception as e:
            self.update_progress(f"エラーが発生しました: {str(e)}")

        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            self.progress_bar.visible = False
            self.page.update()

    async def update_subtitle(self):
        try:
            current_pos = await self.video_player.get_current_position_async()
            if current_pos is None or "subtitles" not in self.sections:
                return
            c = float(current_pos)
            cur_sub = None
            for sub in self.sections["subtitles"]:
                if sub["start"] <= c <= sub["end"]:
                    cur_sub = sub
                    break
            if cur_sub:
                self.subtitle_text.value = cur_sub["text"]
                self.subtitle_text.visible = True
            else:
                self.subtitle_text.value = ""

            self.subtitle_text.size = 20
            self.subtitle_text.text_align = ft.TextAlign.CENTER
            self.subtitle_text.bgcolor = ft.colors.BLACK54
            self.subtitle_text.color = ft.colors.WHITE
            self.page.update()
        except:
            pass

    def on_video_loaded(self, e):
        self.video_player.volume = 50
        self.page.run_task(self.update_time)
        self.page.update()

    async def update_time(self):
        while True:
            try:
                if not self.video_player:
                    await asyncio.sleep(0.1)
                    continue
                current_pos = await self.video_player.get_current_position_async()
                if current_pos is not None:
                    m = int(current_pos // 60000)
                    s = int((current_pos % 60000) // 1000)
                    ms = int(current_pos % 1000)
                    ftm = f"{m:02d}:{s:02d}.{ms:03d}"
                    self.current_time_text.value = f"現在の再生時間: {ftm}"
                    await self.update_subtitle()
                    self.page.update()
            except:
                await asyncio.sleep(0.1)
                continue
            await asyncio.sleep(0.01)