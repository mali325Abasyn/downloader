from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
from plyer import filechooser
import threading
import os
import shutil
from yt_dlp import YoutubeDL

class VideoDownloaderApp(App):
    def build(self):
        self.download_info = {}
        self.temp_path = os.path.join(self.user_data_dir, "downloads")
        os.makedirs(self.temp_path, exist_ok=True)
        
        # UI Layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # URL Input
        self.url_input = TextInput(hint_text='Enter video URL', size_hint_y=None, height=50)
        layout.add_widget(self.url_input)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        self.fetch_btn = Button(text='Fetch Formats', on_press=self.fetch_formats)
        self.download_btn = Button(text='Download', on_press=self.download_video)
        self.save_btn = Button(text='Save File', disabled=True)
        btn_layout.add_widget(self.fetch_btn)
        btn_layout.add_widget(self.download_btn)
        btn_layout.add_widget(self.save_btn)
        layout.add_widget(btn_layout)
        
        # Format Selector
        self.format_spinner = Spinner(text='Select format', values=[], size_hint_y=None, height=44)
        layout.add_widget(self.format_spinner)
        
        # Log Output
        scroll = ScrollView()
        self.log_label = Label(text='Logs will appear here...', size_hint_y=None, halign='left', valign='top')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll.add_widget(self.log_label)
        layout.add_widget(scroll)
        
        return layout

    def log(self, message):
        def update_log(_dt):
            self.log_label.text += message + "\n"
        Clock.schedule_once(update_log)

    def fetch_formats(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.log("Please enter a URL first!")
            return

        threading.Thread(target=self._fetch_formats_thread, args=(url,)).start()

    def _fetch_formats_thread(self, url):
        try:
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = []
                
                for f in info['formats']:
                    if f.get('vcodec') != 'none' and f.get('height'):
                        label = f"{f.get('format_note', 'unknown')} - {f.get('ext')} - {f.get('height')}p"
                        formats.append((label, f['format_id']))
                    elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        label = f"Audio Only - {f.get('ext')} - {f.get('abr', 'unknown')}kbps"
                        formats.append((label, f['format_id']))

                formats = list(dict.fromkeys(formats))
                formats = sorted(formats, key=lambda x: self.extract_height(x[0]), reverse=True)
                
                self.download_info['formats'] = formats
                self.download_info['url'] = url
                self.download_info['title'] = self.sanitize_filename(info.get('title', 'video'))
                
                spinner_values = [f[0] for f in formats]
                Clock.schedule_once(lambda dt: self.update_spinner(spinner_values))
                self.log(f"Found {len(formats)} formats")
        except Exception as e:
            self.log(f"Error: {str(e)}")

    def update_spinner(self, values):
        self.format_spinner.values = values
        if values:
            self.format_spinner.text = values[0]

    def download_video(self, instance):
        if not self.format_spinner.text:
            self.log("Select a format first!")
            return

        selected_idx = self.format_spinner.values.index(self.format_spinner.text)
        selected_format = self.download_info['formats'][selected_idx][1]
        
        threading.Thread(target=self._download_thread, args=(selected_format,)).start()

    def _download_thread(self, selected_format):
        try:
            ydl_opts = {
                'format': selected_format,
                'outtmpl': os.path.join(self.temp_path, f"{self.download_info['title']}.%(ext)s"),
                'progress_hooks': [self.progress_hook],
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.download_info['url']])
            
            Clock.schedule_once(lambda dt: self.enable_save_button())
            self.log("Download complete!")
        except Exception as e:
            self.log(f"Download failed: {str(e)}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            self.log(f"Progress: {percent}")

    def enable_save_button(self):
        self.save_btn.disabled = False
        self.save_btn.bind(on_press=self.save_file)

    def save_file(self, instance):
        try:
            filechooser.save_file(title="Save video", 
                                 on_selection=self.handle_save_selection)
        except Exception as e:
            self.log(f"Save error: {str(e)}")

    def handle_save_selection(self, selection):
        if selection:
            dest = selection[0]
            src = os.path.join(self.temp_path, os.listdir(self.temp_path)[0])
            shutil.copy(src, dest)
            self.log(f"File saved to: {dest}")

    def sanitize_filename(self, name):
        return "".join(c if c.isalnum() or c in " -_." else "_" for c in name)

    def extract_height(self, label):
        try:
            return int(label.split('-')[-1].replace('p', '').strip())
        except:
            return 0

if __name__ == '__main__':
    VideoDownloaderApp().run()