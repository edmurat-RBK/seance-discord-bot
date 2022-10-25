import base64
import json
import os
import random
import re
import requests


class EmojiConverter:
    def __init__(self):
        if os.path.exists("data/unicode.html"):
            with open("data/unicode.html","r", encoding="utf-8") as file:
                self.data = file.read()
        else:
            self.data = requests.get('https://unicode.org/emoji/charts/full-emoji-list.html').text
            with open("data/unicode.html","w", encoding="utf-8") as file:
                file.write(self.data)
    
    def char_to_png(self, emoji, page_id, version=0):
        html_search_string = r"<img alt='{0}' class='imga' src='data:image/png;base64,([^']+)'>"
        match_list = re.findall(html_search_string.format(emoji), self.data)
        
        save_path = "content/" + page_id.replace("-","") + ".png"
        with open(save_path, "wb") as file:
            file.write(base64.decodebytes(match_list[version].encode("utf-8")))
        return save_path


class GameDesignLenses:
    def __init__(self):
        with open("data/lenses.json","r") as file:
            file_content = file.read()
            self.lenses = json.loads(file_content)
            
    def pick_one(self):
        return random.choice(self.lenses)
        
            
            

if __name__ == "__main__":
    gdl = GameDesignLenses()
    print(gdl.lenses)