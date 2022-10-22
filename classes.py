import base64
import re
import requests


class EmojiConverter:
    def __init__(self):
        self.data = requests.get('https://unicode.org/emoji/charts/full-emoji-list.html').text
    
    def char_to_png(self, emoji, page_id,  base_save_path, version=0):
        html_search_string = r"<img alt='{0}' class='imga' src='data:image/png;base64,([^']+)'>"
        match_list = re.findall(html_search_string.format(emoji), self.data)
        
        save_path = base_save_path + page_id.replace("-","") + ".png"
        with open(save_path, "wb") as file:
            file.write(base64.decodebytes(match_list[version].encode("utf-8")))
        return save_path
